// Content management models based on OpenAPI specification

export interface Question {
  id: string;
  content: string;
  subject: string;
  topic: string;
  difficulty: DifficultyLevel;
  type: QuestionType;
  options?: QuestionOption[];
  correct_answer?: string;
  explanation?: string;
  tags: string[];
  education_level: string;
  grade: string;
  is_active: boolean;
  is_flagged: boolean;
  flag_reason?: string;
  usage_count: number;
  accuracy_rate: number;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export enum DifficultyLevel {
  EASY = 'easy',
  MEDIUM = 'medium',
  HARD = 'hard'
}

export enum QuestionType {
  MULTIPLE_CHOICE = 'multiple_choice',
  TRUE_FALSE = 'true_false',
  SHORT_ANSWER = 'short_answer',
  ESSAY = 'essay',
  FILL_BLANK = 'fill_blank'
}

export interface QuestionOption {
  id: string;
  text: string;
  is_correct: boolean;
}

export interface QuestionListResponse {
  items: Question[];
  total: number;
  page: number;
  page_size: number;
}

export interface QuestionFilters {
  subject?: string;
  topic?: string;
  difficulty?: DifficultyLevel;
  type?: QuestionType;
  education_level?: string;
  grade?: string;
  is_flagged?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface CreateQuestionRequest {
  content: string;
  subject: string;
  topic: string;
  difficulty: DifficultyLevel;
  type: QuestionType;
  options?: QuestionOption[];
  correct_answer?: string;
  explanation?: string;
  tags: string[];
  education_level: string;
  grade: string;
}

export interface FlagQuestionRequest {
  reason: string;
}

export interface Topic {
  id: string;
  name: string;
  subject_id: string;
  subject_name: string;
  description?: string;
  order: number;
  parent_id?: string;
  children?: Topic[];
  question_count: number;
  is_active: boolean;
  created_at: string;
}

export interface Subject {
  id: string;
  name: string;
  code: string;
  education_level: string;
  description?: string;
  icon?: string;
  color?: string;
  topic_count: number;
  question_count: number;
  document_count: number;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

// Subject API Request/Response Types
export interface SubjectListParams {
  search?: string;
  education_level?: string;
  is_active?: boolean;
  has_topics?: boolean;
  has_questions?: boolean;
  sort_by?: 'name' | 'code' | 'created_at' | 'topic_count' | 'question_count' | 'education_level';
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface SubjectListResponse {
  subjects: Subject[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface SubjectStats {
  total_subjects: number;
  active_subjects: number;
  inactive_subjects: number;
  by_education_level: Record<string, number>;
  total_topics: number;
  total_questions: number;
  subjects_without_topics: number;
  subjects_without_questions: number;
  avg_topics_per_subject: number;
  avg_questions_per_subject: number;
  recently_created: number;
  most_popular: Array<{ name: string; question_count: number }>;
}

export interface SubjectDetailResponse extends Subject {
  topics: Array<{
    id: string;
    name: string;
    grade: string;
    order_index: number;
    question_count: number;
  }>;
  coverage_percentage: number;
  difficulty_distribution: Record<string, number>;
  recent_activity: Array<Record<string, unknown>>;
}

export interface SubjectCreate {
  name: string;
  code: string;
  education_level: string;
  description?: string;
  icon?: string;
  color?: string;
}

export interface SubjectUpdate {
  name?: string;
  code?: string;
  education_level?: string;
  description?: string;
  icon?: string;
  color?: string;
  is_active?: boolean;
}

export interface SubjectBulkAction {
  subject_ids: string[];
  action: 'activate' | 'deactivate' | 'delete';
}

export interface SubjectBulkActionResponse {
  total_requested: number;
  successful: number;
  failed: number;
  errors: Array<{ subject_id: string; error: string }>;
  message: string;
}

export interface SubjectDependencyWarning {
  subject_id: string;
  subject_name: string;
  topic_count: number;
  question_count: number;
  document_count: number;
  active_students_count: number;
  can_delete: boolean;
  warnings: string[];
}

export interface SubjectExportRequest {
  format: 'csv' | 'json' | 'excel';
  subject_ids?: string[];
  include_topics?: boolean;
  include_questions?: boolean;
}

export interface SubjectExportResponse {
  filename: string;
  file_size: number;
  record_count: number;
  download_url: string;
  expires_at: string;
}

export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  subject?: string;
  topic?: string;
  education_level?: string;
  status: DocumentStatus;
  processing_progress?: number;
  error_message?: string;
  chunks_count?: number;
  uploaded_by: string;
  created_at: string;
  processed_at?: string;
}

export enum DocumentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
}

export interface UploadDocumentRequest {
  file: File;
  subject?: string;
  topic?: string;
  education_level?: string;
}

export interface CurriculumTree {
  subjects: CurriculumSubject[];
}

export interface CurriculumSubject {
  id: string;
  name: string;
  topics: CurriculumTopic[];
  coverage_percentage: number;
}

export interface CurriculumTopic {
  id: string;
  name: string;
  subtopics: CurriculumSubtopic[];
  questions_count: number;
  coverage_percentage: number;
}

export interface CurriculumSubtopic {
  id: string;
  name: string;
  questions_count: number;
  has_content: boolean;
}
