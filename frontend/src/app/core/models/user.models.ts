// User management models based on OpenAPI specification
// Bank-grade user management system with comprehensive filtering

import { UserRole, SubscriptionTier, StudentProfile } from './auth.models';

// ================================
// Core User Types
// ================================

export interface User {
  id: string;
  phone_number: string;
  whatsapp_id?: string;
  email: string;
  username?: string;
  full_name?: string;
  name?: string;
  role: UserRole;
  subscription_tier: SubscriptionTier;
  subscription_expires_at: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at?: string;
  last_active: string;
  last_login?: string;
  phone?: string;
  grade?: string;
  subscription?: string;
  subjects?: string[];
  progress?: number;
  questions_asked?: number;
  study_hours?: number;
  competitions_joined?: number;
  badges_earned?: number;
  institution?: string;
  status?: 'active' | 'inactive' | 'suspended' | 'pending';
  avatar_url?: string;
  total_sessions?: number;
  student?: StudentProfile;
  // Extended user detail fields
  student_name?: string;
  school?: string;
}

// User list item for table display (lighter weight)
export interface UserListItem {
  id: string;
  phone_number: string;
  email?: string;
  role: UserRole;
  subscription_tier: SubscriptionTier;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_active?: string;
  student_name?: string;
  school?: string;
  status?: 'active' | 'inactive' | 'suspended' | 'pending';
}

// Comprehensive user detail with all statistics
export interface UserDetail {
  id: string;
  phone_number: string;
  whatsapp_id?: string;
  email?: string;
  role: UserRole;
  subscription_tier: SubscriptionTier;
  subscription_expires_at?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_active?: string;
  // Student details (if applicable)
  student?: {
    id: string;
    first_name: string;
    last_name: string;
    full_name: string;
    grade: string;
    education_level: EducationLevel;
    school_name?: string;
    district?: string;
    province?: string;
    subjects: string[];
    total_xp: number;
    level: number;
    daily_goal_minutes: number;
    preferred_language: string;
  };
  // Statistics
  total_sessions: number;
  total_questions_answered: number;
  total_payments: number;
  conversations_count: number;
  achievements_count: number;
  payments_count: number;
}

// ================================
// Response Types
// ================================

export interface UserListResponse {
  items: User[];
  users?: User[]; // Backend may return 'users' instead of 'items'
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ImpersonateResponse {
  access_token: string;
  token?: string; // Alias for backward compatibility
  user_id: string;
  expires_at: string;
  read_only: boolean;
}

export interface BulkActionResponse {
  action: string;
  total_requested: number;
  successful: number;
  failed: number;
  failed_ids: string[];
  success?: boolean;
  affected?: number;
}

// ================================
// Filter Types
// ================================

export interface UserFilters {
  // Role and subscription
  role?: UserRole;
  subscription_tier?: SubscriptionTier;
  // Status
  is_active?: boolean;
  is_verified?: boolean;
  // Date ranges
  registration_date_from?: string;
  registration_date_to?: string;
  last_active_from?: string;
  last_active_to?: string;
  // Education filters (for students)
  education_level?: EducationLevel;
  province?: string;
  district?: string;
  school?: string;
  // Search
  search?: string;
  // Pagination
  page?: number;
  page_size?: number;
  // Sorting
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// ================================
// Bulk Actions
// ================================

export interface BulkUserAction {
  user_ids: string[];
  action: BulkAction;
}

export enum BulkAction {
  ACTIVATE = 'activate',
  DEACTIVATE = 'deactivate',
  DELETE = 'delete',
  SUSPEND = 'suspend',
  VERIFY = 'verify',
  UPGRADE = 'upgrade',
  DOWNGRADE = 'downgrade'
}

// ================================
// Enums
// ================================

export enum EducationLevel {
  PRIMARY = 'primary',
  SECONDARY = 'secondary',
  A_LEVEL = 'a_level'
}

// Zimbabwe Provinces for filtering
export const ZIMBABWE_PROVINCES = [
  'Bulawayo',
  'Harare',
  'Manicaland',
  'Mashonaland Central',
  'Mashonaland East',
  'Mashonaland West',
  'Masvingo',
  'Matabeleland North',
  'Matabeleland South',
  'Midlands'
] as const;

export type ZimbabweProvince = typeof ZIMBABWE_PROVINCES[number];

// Note: ExportFormat is defined in analytics.models.ts

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  phone_number?: string;
  role: UserRole;
  permissions: string[];
  created_at: string;
  last_login: string;
  last_active?: string;
  is_active: boolean;
  is_verified?: boolean;
}

export interface CreateAdminRequest {
  email: string;
  password: string;
  name?: string;
  phone_number?: string;
  role?: UserRole;
  permissions?: string[];
}

export interface StudentListResponse {
  items: StudentDetails[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface StudentDetails {
  id: string;
  user_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone_number: string;
  school_name?: string;
  district?: string;
  province?: string;
  education_level: string;
  grade: string;
  subjects: string[];
  total_xp: number;
  level: number;
  current_streak: number;
  longest_streak: number;
  total_questions: number;
  correct_answers: number;
  accuracy: number;
  subscription_tier: SubscriptionTier;
  subscription_expires_at?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_active: string;
}

export interface StudentDetailResponse {
  id: string;
  user_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone_number: string;
  grade: string;
  education_level: string;
  school_name?: string;
  district?: string;
  province?: string;
  subjects: string[];
  preferred_language: string;
  daily_goal_minutes: number;
  total_xp: number;
  level: number;
  subscription_tier: string;
  subscription_expires_at?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_active: string;
  statistics: StudentStatistics;
  analytics: StudentAnalytics;
}

export interface StudentStatistics {
  current_streak: number;
  longest_streak: number;
  total_active_days: number;
  total_sessions: number;
  total_questions: number;
  correct_answers: number;
  accuracy: number;
  total_study_hours: number;
  achievements_count: number;
  conversations_count: number;
}

export interface StudentAnalytics {
  overview: StudentOverview;
  activity: StudentActivityData;
  performance: Record<string, PerformanceByDifficulty>;
  subjects: SubjectAnalytics[];
  trends: TrendData;
  predictions: PredictionData;
}

export interface StudentOverview {
  total_xp: number;
  level: number;
  total_questions: number;
  correct_answers: number;
  accuracy: number;
  current_streak: number;
  longest_streak: number;
  total_active_days: number;
}

export interface StudentActivityData {
  daily_activity_30d: Record<string, number>;
  hourly_distribution: Record<string, number>;
  peak_study_hour: number;
  most_active_day?: string;
}

export interface PerformanceByDifficulty {
  attempted: number;
  correct: number;
  accuracy: number;
}

export interface SubjectAnalytics {
  subject: string;
  questions_attempted: number;
  correct: number;
  accuracy: number;
}

export interface TrendData {
  weekly_data: WeeklyTrend[];
  trend_direction: 'improving' | 'declining' | 'stable' | 'insufficient_data';
}

export interface WeeklyTrend {
  week: string;
  questions: number;
  accuracy: number;
}

export interface PredictionData {
  exam_readiness_score: number;
  topics_needing_review: TopicReview[];
  ready_for_advancement: TopicAdvancement[];
  recommended_daily_goal: number;
}

export interface TopicReview {
  topic: string;
  mastery: number;
  priority: 'high' | 'medium';
}

export interface TopicAdvancement {
  topic: string;
  mastery: number;
}

export interface StudentSession {
  id: string;
  session_type: string;
  subject_id?: string;
  subject_name?: string;
  topic_id?: string;
  topic_name?: string;
  started_at: string;
  ended_at?: string;
  duration_minutes?: number;
  total_questions: number;
  correct_answers: number;
  score_percentage?: number;
  total_marks_earned?: number;
  total_marks_possible?: number;
  time_spent_seconds: number;
  difficulty_level?: string;
  xp_earned: number;
  status: string;
}

export interface StudentSessionsResponse {
  sessions: StudentSession[];
  total: number;
  limit: number;
  offset: number;
}

export interface StudentActivity {
  id: string;
  type: string;
  icon: string;
  title: string;
  description: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface StudentActivityResponse {
  activities: StudentActivity[];
  total: number;
}

export interface StudentStatsOverview {
  total_students: number;
  active_today: number;
  premium_students: number;
  new_this_week: number;
  by_education_level: Record<string, number>;
  by_subscription_tier: Record<string, number>;
}

// Legacy interfaces for backward compatibility
export interface SubjectEngagement {
  subject: string;
  messages: number;
  time_spent: number;
  mastery_level: number;
}

export interface LearningProgress {
  date: string;
  xp_earned: number;
  questions_answered: number;
  accuracy: number;
}

export interface WeeklyActivity {
  day: string;
  sessions: number;
  messages: number;
}
