import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import {
  QuestionListResponse,
  QuestionFilters,
  Question,
  CreateQuestionRequest,
  FlagQuestionRequest,
  Topic,
  Subject,
  SubjectListParams,
  SubjectListResponse,
  SubjectStats,
  SubjectDetailResponse,
  SubjectCreate,
  SubjectUpdate,
  SubjectBulkAction,
  SubjectBulkActionResponse,
  SubjectDependencyWarning,
  SubjectExportRequest,
  SubjectExportResponse,
  DocumentListResponse,
  Document,
  CurriculumTree,
} from '../models';

@Injectable({
  providedIn: 'root',
})
export class ContentService {
  private readonly basePath = '/admin';

  constructor(private api: ApiService) {}

  // Questions
  getQuestions(filters?: QuestionFilters): Observable<QuestionListResponse> {
    return this.api.get<QuestionListResponse>(`${this.basePath}/questions`, filters);
  }

  getQuestionById(questionId: string): Observable<Question> {
    return this.api.get<Question>(`${this.basePath}/questions/${questionId}`);
  }

  createQuestion(data: CreateQuestionRequest): Observable<Question> {
    return this.api.post<Question>(`${this.basePath}/questions`, data);
  }

  updateQuestion(questionId: string, data: Partial<Question>): Observable<Question> {
    return this.api.put<Question>(`${this.basePath}/questions/${questionId}`, data);
  }

  deleteQuestion(questionId: string): Observable<{ success: boolean }> {
    return this.api.delete(`${this.basePath}/questions/${questionId}`);
  }

  flagQuestion(questionId: string, data: FlagQuestionRequest): Observable<Question> {
    return this.api.post<Question>(`${this.basePath}/questions/${questionId}/flag`, data);
  }

  bulkQuestionAction(
    action: string,
    questionIds: string[]
  ): Observable<{ success: boolean; affected: number }> {
    return this.api.post(`${this.basePath}/questions/bulk`, { action, question_ids: questionIds });
  }

  // Topics
  getTopics(filters?: { subject_id?: string; search?: string }): Observable<Topic[]> {
    return this.api.get<Topic[]>(`${this.basePath}/topics`, filters);
  }

  createTopic(data: Partial<Topic>): Observable<Topic> {
    return this.api.post<Topic>(`${this.basePath}/topics`, data);
  }

  updateTopic(topicId: string, data: Partial<Topic>): Observable<Topic> {
    return this.api.put<Topic>(`${this.basePath}/topics/${topicId}`, data);
  }

  reorderTopics(subjectId: string, topicIds: string[]): Observable<{ success: boolean }> {
    return this.api.post(`${this.basePath}/topics/reorder`, {
      subject_id: subjectId,
      topic_ids: topicIds,
    });
  }

  // Subjects - Enhanced API
  getSubjects(params?: SubjectListParams): Observable<SubjectListResponse> {
    return this.api.get<SubjectListResponse>(`${this.basePath}/subjects`, params);
  }

  getSubjectById(subjectId: string): Observable<SubjectDetailResponse> {
    return this.api.get<SubjectDetailResponse>(`${this.basePath}/subjects/${subjectId}`);
  }

  getSubjectStats(): Observable<SubjectStats> {
    return this.api.get<SubjectStats>(`${this.basePath}/subjects/stats`);
  }

  createSubject(data: SubjectCreate): Observable<Subject> {
    return this.api.post<Subject>(`${this.basePath}/subjects`, data);
  }

  updateSubject(subjectId: string, data: SubjectUpdate): Observable<Subject> {
    return this.api.put<Subject>(`${this.basePath}/subjects/${subjectId}`, data);
  }

  deleteSubject(subjectId: string): Observable<{ message: string }> {
    return this.api.delete(`${this.basePath}/subjects/${subjectId}`);
  }

  checkSubjectDependencies(subjectId: string): Observable<SubjectDependencyWarning> {
    return this.api.get<SubjectDependencyWarning>(`${this.basePath}/subjects/${subjectId}/dependencies`);
  }

  bulkSubjectAction(data: SubjectBulkAction): Observable<SubjectBulkActionResponse> {
    return this.api.post<SubjectBulkActionResponse>(`${this.basePath}/subjects/bulk`, data);
  }

  exportSubjects(data: SubjectExportRequest): Observable<SubjectExportResponse> {
    return this.api.post<SubjectExportResponse>(`${this.basePath}/subjects/export`, data);
  }

  downloadExport(url: string): Observable<Blob> {
    return this.api.download(url);
  }

  // Documents (RAG)
  getDocuments(filters?: {
    status?: string;
    subject?: string;
    page?: number;
    page_size?: number;
  }): Observable<DocumentListResponse> {
    return this.api.get<DocumentListResponse>(`${this.basePath}/documents`, filters);
  }

  getDocumentById(documentId: string): Observable<Document> {
    return this.api.get<Document>(`${this.basePath}/documents/${documentId}`);
  }

  uploadDocument(
    file: File,
    metadata?: { subject?: string; topic?: string; education_level?: string }
  ): Observable<Document> {
    return this.api.upload<Document>(`${this.basePath}/documents`, file, metadata);
  }

  retryDocumentProcessing(documentId: string): Observable<Document> {
    return this.api.post<Document>(`${this.basePath}/documents/${documentId}/retry`, {});
  }

  deleteDocument(documentId: string): Observable<{ success: boolean }> {
    return this.api.delete(`${this.basePath}/documents/${documentId}`);
  }

  // Curriculum
  getCurriculumTree(filters?: { education_level?: string }): Observable<CurriculumTree> {
    return this.api.get<CurriculumTree>(`${this.basePath}/curriculum`, filters);
  }

  getCurriculumCoverage(subjectId: string): Observable<{
    subject: string;
    total_topics: number;
    covered_topics: number;
    coverage_percentage: number;
  }> {
    return this.api.get(`${this.basePath}/curriculum/coverage/${subjectId}`);
  }
}
