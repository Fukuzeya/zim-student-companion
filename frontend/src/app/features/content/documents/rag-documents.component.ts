import { Component, inject, signal, OnInit, OnDestroy, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RagDocumentService, RAGDocument, RAGStats, UploadProgress } from '../../../core/services/rag-document.service';
import { ToastService } from '../../../core/services/toast.service';

interface UploadFormData {
  documentType: string;
  subject: string;
  grade: string;
  educationLevel: string;
  year?: number;
  paperNumber?: string;
  term?: string;
}

@Component({
  selector: 'app-rag-documents',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="rag-documents-container">
      <!-- Header -->
      <div class="page-header">
        <div class="header-info">
          <h1>
            <span class="material-symbols-outlined">school</span>
            RAG Document Management
          </h1>
          <p class="subtitle">Upload and manage documents for the RAG knowledge base</p>
        </div>
        <div class="header-actions">
          <button class="btn-secondary" (click)="refreshDocuments()">
            <span class="material-symbols-outlined" [class.spinning]="isRefreshing()">refresh</span>
            Refresh
          </button>
          <button class="btn-primary" (click)="showUploadArea = !showUploadArea">
            <span class="material-symbols-outlined">upload_file</span>
            Upload Documents
          </button>
        </div>
      </div>

      <!-- RAG Stats Cards -->
      @if (stats()) {
        <div class="stats-grid">
          <div class="stat-card primary">
            <div class="stat-icon">
              <span class="material-symbols-outlined">inventory_2</span>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ getTotalDocuments() }}</div>
              <div class="stat-label">Total Documents</div>
              <div class="stat-sublabel">
                {{ stats()!.uploads.by_status['completed']?.count || 0 }} processed
              </div>
            </div>
          </div>

          <div class="stat-card success">
            <div class="stat-icon">
              <span class="material-symbols-outlined">analytics</span>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats()!.uploads.total_chunks_indexed.toLocaleString() }}</div>
              <div class="stat-label">Total Chunks</div>
              <div class="stat-sublabel">Indexed in vector store</div>
            </div>
          </div>

          <div class="stat-card info">
            <div class="stat-icon">
              <span class="material-symbols-outlined">storage</span>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats()!.uploads.total_storage_mb.toFixed(1) }} MB</div>
              <div class="stat-label">Storage Used</div>
              <div class="stat-sublabel">{{ getTotalFiles() }} files</div>
            </div>
          </div>

          <div class="stat-card" [class.warning]="stats()!.health !== 'healthy'">
            <div class="stat-icon">
              <span class="material-symbols-outlined">
                {{ stats()!.health === 'healthy' ? 'check_circle' : 'warning' }}
              </span>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats()!.health }}</div>
              <div class="stat-label">System Health</div>
              <div class="stat-sublabel">
                {{ stats()!.uploads.by_status['processing']?.count || 0 }} processing
              </div>
            </div>
          </div>
        </div>
      }

      <!-- Upload Area -->
      @if (showUploadArea) {
        <div class="upload-section" [@slideDown]>
          <div class="upload-card">
            <div class="upload-header">
              <h3>
                <span class="material-symbols-outlined">cloud_upload</span>
                Upload New Documents
              </h3>
              <button class="close-btn" (click)="showUploadArea = false">
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>

            <!-- Drag and Drop Zone -->
            <div
              class="dropzone"
              [class.dragover]="isDragging()"
              (drop)="onDrop($event)"
              (dragover)="onDragOver($event)"
              (dragleave)="onDragLeave($event)"
              (click)="fileInput.click()"
            >
              <span class="material-symbols-outlined drop-icon">cloud_upload</span>
              <h4>Drag & drop files here</h4>
              <p>or click to browse</p>
              <div class="file-types">
                Supported: PDF, DOCX, DOC, TXT (Max 50MB)
              </div>
              <input
                #fileInput
                type="file"
                multiple
                accept=".pdf,.docx,.doc,.txt"
                (change)="onFilesSelected($event)"
                style="display: none"
              />
            </div>

            <!-- Upload Form -->
            <div class="upload-form">
              <div class="form-row">
                <div class="form-group">
                  <label>Document Type *</label>
                  <select [(ngModel)]="uploadForm.documentType" required>
                    <option value="">Select type...</option>
                    <option value="past_paper">Past Paper</option>
                    <option value="marking_scheme">Marking Scheme</option>
                    <option value="syllabus">Syllabus</option>
                    <option value="textbook">Textbook</option>
                    <option value="teacher_notes">Teacher Notes</option>
                  </select>
                </div>

                <div class="form-group">
                  <label>Subject</label>
                  <input type="text" [(ngModel)]="uploadForm.subject" placeholder="e.g., Mathematics" />
                </div>

                <div class="form-group">
                  <label>Grade</label>
                  <input type="text" [(ngModel)]="uploadForm.grade" placeholder="e.g., Form 3" />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>Education Level</label>
                  <select [(ngModel)]="uploadForm.educationLevel">
                    <option value="secondary">Secondary</option>
                    <option value="primary">Primary</option>
                    <option value="a_level">A-Level</option>
                  </select>
                </div>

                <div class="form-group">
                  <label>Year (for past papers)</label>
                  <input type="number" [(ngModel)]="uploadForm.year" placeholder="2023" min="2000" max="2030" />
                </div>

                <div class="form-group">
                  <label>Paper Number</label>
                  <input type="text" [(ngModel)]="uploadForm.paperNumber" placeholder="Paper 1" />
                </div>

                <div class="form-group">
                  <label>Term</label>
                  <input type="text" [(ngModel)]="uploadForm.term" placeholder="Term 1" />
                </div>
              </div>
            </div>

            <!-- Selected Files Preview -->
            @if (selectedFiles().length > 0) {
              <div class="selected-files">
                <h4>Selected Files ({{ selectedFiles().length }})</h4>
                <div class="files-list">
                  @for (file of selectedFiles(); track file.name) {
                    <div class="file-item">
                      <span class="material-symbols-outlined file-icon">description</span>
                      <div class="file-details">
                        <span class="file-name">{{ file.name }}</span>
                        <span class="file-size">{{ formatFileSize(file.size) }}</span>
                      </div>
                      <button class="remove-btn" (click)="removeFile(file)">
                        <span class="material-symbols-outlined">close</span>
                      </button>
                    </div>
                  }
                </div>
                <div class="upload-actions">
                  <button class="btn-secondary" (click)="clearFiles()">Clear All</button>
                  <button
                    class="btn-primary"
                    [disabled]="!uploadForm.documentType || isUploading()"
                    (click)="startUpload()"
                  >
                    <span class="material-symbols-outlined">upload</span>
                    Upload {{ selectedFiles().length }} {{ selectedFiles().length === 1 ? 'File' : 'Files' }}
                  </button>
                </div>
              </div>
            }

            <!-- Upload Progress -->
            @if (activeUploads().length > 0) {
              <div class="upload-progress-section">
                <div class="progress-header">
                  <h4>Upload Progress</h4>
                  <button class="clear-btn" (click)="clearCompleted()">Clear Completed</button>
                </div>
                @for (upload of activeUploads(); track upload.filename) {
                  <div class="progress-item" [class]="upload.status">
                    <div class="progress-info">
                      <div class="progress-title">
                        <span class="material-symbols-outlined status-icon">
                          {{ getStatusIcon(upload.status) }}
                        </span>
                        <span class="filename">{{ upload.filename }}</span>
                      </div>
                      <span class="progress-message">{{ upload.message || upload.status }}</span>
                    </div>
                    <div class="progress-bar-container">
                      <div
                        class="progress-bar"
                        [style.width.%]="upload.progress"
                        [class]="upload.status"
                      ></div>
                    </div>
                    <span class="progress-percent">{{ upload.progress.toFixed(0) }}%</span>
                  </div>
                }
              </div>
            }
          </div>
        </div>
      }

      <!-- Filters -->
      <div class="filters-section">
        <div class="search-box">
          <span class="material-symbols-outlined">search</span>
          <input
            type="text"
            placeholder="Search documents..."
            [(ngModel)]="searchQuery"
            (input)="applyFilters()"
          />
        </div>

        <div class="filter-group">
          <select [(ngModel)]="filterStatus" (change)="applyFilters()">
            <option value="">All Status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>

          <select [(ngModel)]="filterType" (change)="applyFilters()">
            <option value="">All Types</option>
            <option value="past_paper">Past Papers</option>
            <option value="marking_scheme">Marking Schemes</option>
            <option value="syllabus">Syllabi</option>
            <option value="textbook">Textbooks</option>
            <option value="teacher_notes">Teacher Notes</option>
          </select>

          <select [(ngModel)]="filterSubject" (change)="applyFilters()">
            <option value="">All Subjects</option>
            <option value="Mathematics">Mathematics</option>
            <option value="English">English</option>
            <option value="Physics">Physics</option>
            <option value="Chemistry">Chemistry</option>
            <option value="Biology">Biology</option>
          </select>
        </div>
      </div>

      <!-- Documents List -->
      @if (isLoading()) {
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Loading documents...</p>
        </div>
      } @else if (filteredDocuments().length === 0) {
        <div class="empty-state">
          <span class="material-symbols-outlined">folder_open</span>
          <h3>No documents found</h3>
          <p>Upload your first document to build the RAG knowledge base</p>
          <button class="btn-primary" (click)="showUploadArea = true">
            <span class="material-symbols-outlined">upload</span>
            Upload Document
          </button>
        </div>
      } @else {
        <div class="documents-table-card">
          <table class="documents-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Type</th>
                <th>Subject</th>
                <th>Status</th>
                <th>Chunks</th>
                <th>Size</th>
                <th>Uploaded</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (doc of filteredDocuments(); track doc.document_id) {
                <tr>
                  <td>
                    <div class="doc-cell">
                      <span class="material-symbols-outlined doc-type-icon" [class]="doc.document_type">
                        {{ getDocTypeIcon(doc.document_type) }}
                      </span>
                      <div class="doc-info">
                        <span class="doc-filename">{{ doc.filename }}</span>
                        @if (doc.grade || doc.year) {
                          <span class="doc-meta">
                            {{ doc.grade }} {{ doc.year ? '(' + doc.year + ')' : '' }}
                          </span>
                        }
                      </div>
                    </div>
                  </td>
                  <td>
                    <span class="type-badge" [class]="doc.document_type">
                      {{ formatDocType(doc.document_type) }}
                    </span>
                  </td>
                  <td>
                    <span class="subject-tag">{{ doc.subject || '-' }}</span>
                  </td>
                  <td>
                    <div class="status-cell">
                      <span class="status-badge" [class]="doc.status">
                        <span class="material-symbols-outlined">{{ getStatusIcon(doc.status) }}</span>
                        {{ doc.status }}
                      </span>
                      @if (doc.status === 'processing') {
                        <div class="mini-progress">
                          <div class="mini-progress-bar" [style.width.%]="doc.processing_progress"></div>
                        </div>
                      }
                    </div>
                  </td>
                  <td>
                    @if (doc.chunks_indexed > 0) {
                      <span class="chunks-count">{{ doc.chunks_indexed }}</span>
                    } @else {
                      <span class="text-muted">-</span>
                    }
                  </td>
                  <td>{{ doc.file_size_mb.toFixed(2) }} MB</td>
                  <td>
                    <span class="date-text">{{ formatDate(doc.uploaded_at) }}</span>
                  </td>
                  <td>
                    <div class="action-buttons">
                      <button
                        class="action-btn"
                        title="View Details"
                        (click)="viewDocumentDetails(doc)"
                      >
                        <span class="material-symbols-outlined">visibility</span>
                      </button>
                      @if (doc.status === 'failed') {
                        <button
                          class="action-btn retry"
                          title="Retry Processing"
                          (click)="retryDocument(doc)"
                        >
                          <span class="material-symbols-outlined">refresh</span>
                        </button>
                      }
                      <button
                        class="action-btn danger"
                        title="Delete"
                        (click)="deleteDocument(doc)"
                      >
                        <span class="material-symbols-outlined">delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>

          <!-- Pagination -->
          @if (pagination.total > pagination.limit) {
            <div class="pagination">
              <button
                class="page-btn"
                [disabled]="pagination.offset === 0"
                (click)="previousPage()"
              >
                <span class="material-symbols-outlined">chevron_left</span>
                Previous
              </button>
              <span class="page-info">
                Page {{ currentPage() }} of {{ totalPages() }}
                ({{ pagination.total }} total)
              </span>
              <button
                class="page-btn"
                [disabled]="!hasMore()"
                (click)="nextPage()"
              >
                Next
                <span class="material-symbols-outlined">chevron_right</span>
              </button>
            </div>
          }
        </div>
      }
    </div>
  `,
  styleUrls: ['./rag-documents.component.scss']
})
export class RagDocumentsComponent implements OnInit, OnDestroy {
  private ragService = inject(RagDocumentService);
  private toastService = inject(ToastService);

  // State
  documents = signal<RAGDocument[]>([]);
  filteredDocuments = signal<RAGDocument[]>([]);
  stats = signal<RAGStats | null>(null);
  isLoading = signal(false);
  isRefreshing = signal(false);
  isUploading = signal(false);

  // Upload state
  showUploadArea = false;
  selectedFiles = signal<File[]>([]);
  isDragging = signal(false);
  activeUploads = this.ragService.activeUploads;

  // Form
  uploadForm: UploadFormData = {
    documentType: '',
    subject: '',
    grade: '',
    educationLevel: 'secondary'
  };

  // Filters
  searchQuery = '';
  filterStatus = '';
  filterType = '';
  filterSubject = '';

  // Pagination
  pagination = {
    limit: 50,
    offset: 0,
    total: 0
  };

  // Computed
  getTotalDocuments = computed(() => {
    const stats = this.stats();
    if (!stats) return 0;
    return Object.values(stats.uploads.by_status).reduce((sum, s) => sum + s.count, 0);
  });

  getTotalFiles = computed(() => {
    return Object.values(this.stats()?.uploads.by_type || {}).reduce((sum: number, count) => sum + (count as number), 0);
  });

  currentPage = computed(() => Math.floor(this.pagination.offset / this.pagination.limit) + 1);
  totalPages = computed(() => Math.ceil(this.pagination.total / this.pagination.limit));
  hasMore = computed(() => this.pagination.offset + this.pagination.limit < this.pagination.total);

  private refreshInterval: any;

  ngOnInit(): void {
    this.loadDocuments();
    this.loadStats();

    // Auto-refresh every 10 seconds when there are processing documents
    this.refreshInterval = setInterval(() => {
      const hasProcessing = this.documents().some(d => d.status === 'processing' || d.status === 'pending');
      if (hasProcessing) {
        this.refreshDocuments(true);
      }
    }, 10000);
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  loadDocuments(): void {
    this.isLoading.set(true);
    this.ragService.listDocuments({
      limit: this.pagination.limit,
      offset: this.pagination.offset
    }).subscribe({
      next: (response) => {
        this.documents.set(response.documents);
        this.filteredDocuments.set(response.documents);
        this.pagination.total = response.total;
        this.isLoading.set(false);
        this.applyFilters();
      },
      error: (error) => {
        this.toastService.error('Failed to load documents');
        this.isLoading.set(false);
      }
    });
  }

  loadStats(): void {
    this.ragService.getRAGStats().subscribe({
      next: (stats) => {
        this.stats.set(stats);
      },
      error: (error) => {
        console.error('Failed to load RAG stats', error);
      }
    });
  }

  refreshDocuments(silent = false): void {
    if (!silent) this.isRefreshing.set(true);
    this.ragService.listDocuments({
      limit: this.pagination.limit,
      offset: this.pagination.offset
    }).subscribe({
      next: (response) => {
        this.documents.set(response.documents);
        this.pagination.total = response.total;
        this.applyFilters();
        if (!silent) {
          this.isRefreshing.set(false);
          this.toastService.success('Documents refreshed');
        }
        this.loadStats();
      },
      error: () => {
        if (!silent) {
          this.isRefreshing.set(false);
          this.toastService.error('Failed to refresh');
        }
      }
    });
  }

  // Drag and drop handlers
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);

    const files = event.dataTransfer?.files;
    if (files) {
      this.addFiles(Array.from(files));
    }
  }

  onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.addFiles(Array.from(input.files));
      input.value = ''; // Reset input
    }
  }

  private addFiles(files: File[]): void {
    const validFiles = files.filter(f => {
      const ext = f.name.split('.').pop()?.toLowerCase();
      return ['pdf', 'docx', 'doc', 'txt'].includes(ext || '');
    });

    if (validFiles.length !== files.length) {
      this.toastService.warning('Some files were skipped (unsupported format)');
    }

    this.selectedFiles.update(current => [...current, ...validFiles]);
  }

  removeFile(file: File): void {
    this.selectedFiles.update(files => files.filter(f => f !== file));
  }

  clearFiles(): void {
    this.selectedFiles.set([]);
  }

  startUpload(): void {
    if (!this.uploadForm.documentType) {
      this.toastService.error('Please select a document type');
      return;
    }

    const files = this.selectedFiles();
    if (files.length === 0) {
      this.toastService.error('Please select at least one file to upload');
      return;
    }

    this.isUploading.set(true);
    this.toastService.info(`Starting upload of ${files.length} file(s)...`);

    let completedCount = 0;
    let errorCount = 0;

    files.forEach(file => {
      this.ragService.uploadDocument(file, this.uploadForm.documentType, {
        subject: this.uploadForm.subject || undefined,
        grade: this.uploadForm.grade || undefined,
        education_level: this.uploadForm.educationLevel,
        year: this.uploadForm.year,
        paper_number: this.uploadForm.paperNumber || undefined,
        term: this.uploadForm.term || undefined,
        process_immediately: true
      }).subscribe({
        next: (progress) => {
          if (progress.status === 'completed') {
            completedCount++;
            this.toastService.success(`${file.name} processed successfully`);
          } else if (progress.status === 'failed') {
            errorCount++;
            this.toastService.error(`${file.name}: ${progress.message || 'Processing failed'}`);
          }
        },
        error: (error) => {
          errorCount++;
          const errorMessage = error.error?.error || error.error?.detail || error.message || 'Upload failed';
          this.toastService.error(`${file.name}: ${errorMessage}`);
          console.error('Upload error:', error);

          // Check if all files have been processed
          if (completedCount + errorCount === files.length) {
            this.isUploading.set(false);
            this.refreshDocuments(true);
          }
        }
      });
    });

    this.selectedFiles.set([]);

    // Refresh documents periodically while uploading
    const refreshInterval = setInterval(() => {
      this.refreshDocuments(true);
      if (!this.isUploading()) {
        clearInterval(refreshInterval);
      }
    }, 3000);

    // Safety timeout to reset uploading state
    setTimeout(() => {
      this.isUploading.set(false);
      this.refreshDocuments(false);
    }, 60000);
  }

  clearCompleted(): void {
    this.ragService.clearCompletedUploads();
  }

  applyFilters(): void {
    let filtered = this.documents();

    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(d =>
        d.filename.toLowerCase().includes(query) ||
        d.subject?.toLowerCase().includes(query) ||
        d.grade?.toLowerCase().includes(query)
      );
    }

    if (this.filterStatus) {
      filtered = filtered.filter(d => d.status === this.filterStatus);
    }

    if (this.filterType) {
      filtered = filtered.filter(d => d.document_type === this.filterType);
    }

    if (this.filterSubject) {
      filtered = filtered.filter(d => d.subject === this.filterSubject);
    }

    this.filteredDocuments.set(filtered);
  }

  viewDocumentDetails(doc: RAGDocument): void {
    // To be implemented - show modal with processing logs
    this.toastService.info(`Viewing details for ${doc.filename}`);
  }

  retryDocument(doc: RAGDocument): void {
    this.ragService.retryProcessing(doc.document_id).subscribe({
      next: () => {
        this.toastService.success('Processing retry started');
        setTimeout(() => this.refreshDocuments(true), 1000);
      },
      error: (error) => {
        this.toastService.error(`Retry failed: ${error.error?.error || error.message}`);
      }
    });
  }

  deleteDocument(doc: RAGDocument): void {
    if (!confirm(`Delete "${doc.filename}"? This cannot be undone.`)) {
      return;
    }

    this.ragService.deleteDocument(doc.document_id).subscribe({
      next: () => {
        this.toastService.success('Document deleted');
        this.refreshDocuments();
      },
      error: (error) => {
        this.toastService.error(`Delete failed: ${error.error?.error || error.message}`);
      }
    });
  }

  previousPage(): void {
    if (this.pagination.offset > 0) {
      this.pagination.offset -= this.pagination.limit;
      this.loadDocuments();
    }
  }

  nextPage(): void {
    if (this.hasMore()) {
      this.pagination.offset += this.pagination.limit;
      this.loadDocuments();
    }
  }

  // Utility methods
  formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    if (diffMins < 10080) return `${Math.floor(diffMins / 1440)}d ago`;

    return date.toLocaleDateString();
  }

  formatDocType(type: string): string {
    return type.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  }

  getDocTypeIcon(type: string): string {
    const icons: Record<string, string> = {
      past_paper: 'description',
      marking_scheme: 'grading',
      syllabus: 'menu_book',
      textbook: 'import_contacts',
      teacher_notes: 'sticky_note_2'
    };
    return icons[type] || 'description';
  }

  getStatusIcon(status: string): string {
    const icons: Record<string, string> = {
      pending: 'schedule',
      processing: 'autorenew',
      completed: 'check_circle',
      failed: 'error',
      uploading: 'upload'
    };
    return icons[status] || 'help';
  }
}
