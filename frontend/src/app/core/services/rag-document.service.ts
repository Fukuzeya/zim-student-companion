import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType, HttpRequest } from '@angular/common/http';
import { Observable, BehaviorSubject, interval } from 'rxjs';
import { map, catchError, tap, switchMap, takeWhile } from 'rxjs/operators';

export interface RAGDocument {
  document_id: string;
  filename: string;
  file_size: number;
  file_size_mb: number;
  document_type: 'past_paper' | 'marking_scheme' | 'syllabus' | 'textbook' | 'teacher_notes';
  subject?: string;
  grade?: string;
  education_level: string;
  year?: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  chunks_created: number;
  chunks_indexed: number;
  processing_progress: number;
  error?: string;
  retry_count: number;
  uploaded_at: string;
  processed_at?: string;
  processing_time_ms?: number;
}

export interface RAGDocumentDetail extends RAGDocument {
  processing_metadata?: any;
  vector_store_collection?: string;
  file_hash?: string;
  file_path?: string;
  uploaded_by?: string;
  processing_logs?: Array<{
    stage: string;
    status: string;
    message: string;
    created_at: string;
  }>;
}

export interface DocumentListResponse {
  documents: RAGDocument[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface UploadProgress {
  document_id?: string;
  filename: string;
  progress: number; // 0-100
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  message?: string;
}

export interface RAGStats {
  uploads: {
    by_status: {
      [key: string]: {
        count: number;
        chunks: number;
      };
    };
    by_type: {
      [key: string]: number;
    };
    total_chunks_indexed: number;
    total_storage_bytes: number;
    total_storage_mb: number;
  };
  last_ingestion?: string;
  last_document?: RAGDocument;
  vector_store: any;
  health: string;
}

@Injectable({
  providedIn: 'root'
})
export class RagDocumentService {
  private http = inject(HttpClient);
  private apiUrl = '/api/v1/admin';

  // State management
  private uploadProgressMap = new Map<string, BehaviorSubject<UploadProgress>>();

  // Public signals for reactive UI
  activeUploads = signal<UploadProgress[]>([]);

  /**
   * Upload a document for RAG ingestion
   */
  uploadDocument(
    file: File,
    documentType: string,
    metadata: {
      subject?: string;
      grade?: string;
      education_level?: string;
      year?: number;
      paper_number?: string;
      term?: string;
      process_immediately?: boolean;
    }
  ): Observable<UploadProgress> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    if (metadata.subject) formData.append('subject', metadata.subject);
    if (metadata.grade) formData.append('grade', metadata.grade);
    if (metadata.education_level) formData.append('education_level', metadata.education_level);
    if (metadata.year) formData.append('year', metadata.year.toString());
    if (metadata.paper_number) formData.append('paper_number', metadata.paper_number);
    if (metadata.term) formData.append('term', metadata.term);
    formData.append('process_immediately', metadata.process_immediately !== false ? 'true' : 'false');

    const req = new HttpRequest('POST', `${this.apiUrl}/documents/upload`, formData, {
      reportProgress: true
    });

    const progress$ = new BehaviorSubject<UploadProgress>({
      filename: file.name,
      progress: 0,
      status: 'uploading'
    });

    this.uploadProgressMap.set(file.name, progress$);
    this.updateActiveUploads();

    this.http.request(req).pipe(
      map(event => this.calculateUploadProgress(event, file.name)),
      tap(progress => {
        progress$.next(progress);
        this.updateActiveUploads();
      }),
      catchError(error => {
        // Extract the most meaningful error message
        let errorMessage = 'Upload failed';
        if (error.error?.error) {
          errorMessage = error.error.error;
        } else if (error.error?.detail) {
          errorMessage = error.error.detail;
        } else if (error.error?.message) {
          errorMessage = error.error.message;
        } else if (error.message) {
          errorMessage = error.message;
        } else if (error.statusText) {
          errorMessage = `${error.status}: ${error.statusText}`;
        }

        console.error('Document upload error:', {
          status: error.status,
          error: error.error,
          message: errorMessage
        });

        const errorProgress: UploadProgress = {
          filename: file.name,
          progress: 0,
          status: 'failed',
          message: errorMessage
        };
        progress$.next(errorProgress);
        this.updateActiveUploads();
        throw error;
      })
    ).subscribe({
      next: (progress) => {
        if (progress.status === 'processing' && progress.document_id) {
          // Start polling for processing progress
          this.pollProcessingProgress(progress.document_id, file.name);
        }
      },
      complete: () => {
        // Upload complete, processing started
      }
    });

    return progress$.asObservable();
  }

  /**
   * Calculate upload progress from HTTP events
   */
  private calculateUploadProgress(event: HttpEvent<any>, filename: string): UploadProgress {
    switch (event.type) {
      case HttpEventType.UploadProgress:
        if (event.total) {
          const uploadProgress = Math.round((100 * event.loaded) / event.total);
          return {
            filename,
            progress: uploadProgress,
            status: 'uploading',
            message: `Uploading... ${uploadProgress}%`
          };
        }
        return { filename, progress: 0, status: 'uploading', message: 'Uploading...' };

      case HttpEventType.Response:
        const body = event.body;
        console.log('Upload response:', body);

        if (!body) {
          return {
            filename,
            progress: 0,
            status: 'failed',
            message: 'No response from server'
          };
        }

        if (body.success) {
          return {
            filename,
            document_id: body.document_id,
            progress: 100,
            status: 'processing',
            message: body.message || 'Upload complete. Processing...'
          };
        } else {
          return {
            filename,
            progress: 0,
            status: 'failed',
            message: body.error || body.detail || 'Upload failed'
          };
        }

      case HttpEventType.Sent:
        return { filename, progress: 0, status: 'uploading', message: 'Request sent...' };

      default:
        return { filename, progress: 0, status: 'uploading' };
    }
  }

  /**
   * Poll document processing progress
   */
  private pollProcessingProgress(documentId: string, filename: string): void {
    const progress$ = this.uploadProgressMap.get(filename);
    if (!progress$) return;

    interval(2000).pipe(
      switchMap(() => this.getDocumentStatus(documentId)),
      takeWhile(doc => doc.status === 'processing' || doc.status === 'pending', true)
    ).subscribe({
      next: (doc) => {
        const uploadProgress: UploadProgress = {
          filename,
          document_id: documentId,
          progress: doc.processing_progress || 0,
          status: doc.status === 'completed' ? 'completed' :
                  doc.status === 'failed' ? 'failed' : 'processing',
          message: doc.status === 'completed' ? `Completed! ${doc.chunks_indexed} chunks indexed` :
                  doc.status === 'failed' ? `Failed: ${doc.error}` :
                  doc.processing_metadata?.last_message || 'Processing...'
        };

        progress$.next(uploadProgress);
        this.updateActiveUploads();

        // Clean up after completion or failure
        if (doc.status === 'completed' || doc.status === 'failed') {
          setTimeout(() => {
            this.uploadProgressMap.delete(filename);
            this.updateActiveUploads();
          }, 5000);
        }
      },
      error: (err) => {
        progress$.next({
          filename,
          document_id: documentId,
          progress: 0,
          status: 'failed',
          message: 'Failed to fetch status'
        });
        this.updateActiveUploads();
      }
    });
  }

  /**
   * Update active uploads signal
   */
  private updateActiveUploads(): void {
    const uploads: UploadProgress[] = [];
    this.uploadProgressMap.forEach(progress$ => {
      uploads.push(progress$.value);
    });
    this.activeUploads.set(uploads);
  }

  /**
   * List all documents with filtering
   */
  listDocuments(filters?: {
    status?: string;
    document_type?: string;
    subject?: string;
    limit?: number;
    offset?: number;
  }): Observable<DocumentListResponse> {
    const params: any = {};
    if (filters?.status) params.status = filters.status;
    if (filters?.document_type) params.document_type = filters.document_type;
    if (filters?.subject) params.subject = filters.subject;
    if (filters?.limit) params.limit = filters.limit.toString();
    if (filters?.offset) params.offset = filters.offset.toString();

    return this.http.get<DocumentListResponse>(`${this.apiUrl}/documents`, { params });
  }

  /**
   * Get detailed document status
   */
  getDocumentStatus(documentId: string): Observable<RAGDocumentDetail> {
    return this.http.get<RAGDocumentDetail>(`${this.apiUrl}/documents/${documentId}`);
  }

  /**
   * Retry processing a failed document
   */
  retryProcessing(documentId: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/documents/${documentId}/retry`, {});
  }

  /**
   * Delete a document
   */
  deleteDocument(documentId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/documents/${documentId}`);
  }

  /**
   * Get RAG system statistics
   */
  getRAGStats(): Observable<RAGStats> {
    return this.http.get<RAGStats>(`${this.apiUrl}/rag/stats`);
  }

  /**
   * Clear completed uploads from tracking
   */
  clearCompletedUploads(): void {
    this.uploadProgressMap.forEach((progress$, filename) => {
      const current = progress$.value;
      if (current.status === 'completed' || current.status === 'failed') {
        this.uploadProgressMap.delete(filename);
      }
    });
    this.updateActiveUploads();
  }
}
