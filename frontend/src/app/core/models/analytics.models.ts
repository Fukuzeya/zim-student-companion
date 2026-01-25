// Analytics models based on OpenAPI specification

export interface EngagementAnalytics {
  total_sessions: number;
  total_users: number;
  total_messages: number;
  avg_session_duration: number;
  avg_messages_per_session: number;
  daily_active_users: DailyActiveUsers[];
  hourly_distribution: HourlyDistribution[];
  device_distribution: DeviceDistribution;
  retention_rate: number;
  bounce_rate: number;
}

export interface DailyActiveUsers {
  date: string;
  count: number;
  new_users: number;
  returning_users: number;
}

export interface HourlyDistribution {
  hour: number;
  sessions: number;
  messages: number;
}

export interface DeviceDistribution {
  mobile: number;
  desktop: number;
  tablet: number;
}

export interface LearningAnalytics {
  total_questions_answered: number;
  total_questions_correct: number;
  avg_accuracy: number;
  subject_performance: SubjectPerformance[];
  difficulty_distribution: DifficultyDistribution;
  learning_paths: LearningPathStats[];
  improvement_trends: ImprovementTrend[];
}

export interface SubjectPerformance {
  subject: string;
  questions_answered: number;
  accuracy: number;
  avg_time_per_question: number;
  improvement: number;
}

export interface DifficultyDistribution {
  easy: DifficultyStats;
  medium: DifficultyStats;
  hard: DifficultyStats;
}

export interface DifficultyStats {
  attempted: number;
  correct: number;
  accuracy: number;
}

export interface LearningPathStats {
  path_name: string;
  users_enrolled: number;
  completion_rate: number;
  avg_score: number;
}

export interface ImprovementTrend {
  date: string;
  avg_accuracy: number;
  total_questions: number;
}

export interface RevenueAnalytics {
  total_revenue: number;
  revenue_growth: number;
  mrr: number;
  arr: number;
  avg_revenue_per_user: number;
  lifetime_value: number;
  churn_rate: number;
  conversion_rate: number;
  revenue_by_tier: RevenueByTier[];
  revenue_trend: RevenueTrend[];
  payment_method_breakdown: PaymentMethodBreakdown[];
}

export interface RevenueByTier {
  tier: string;
  revenue: number;
  subscribers: number;
  percentage: number;
}

export interface RevenueTrend {
  date: string;
  revenue: number;
  subscriptions: number;
  refunds: number;
  net_revenue: number;
}

export interface PaymentMethodBreakdown {
  method: string;
  amount: number;
  transactions: number;
  percentage: number;
}

export interface CustomReportRequest {
  report_type: ReportType;
  date_from: string;
  date_to: string;
  metrics: string[];
  dimensions?: string[];
  filters?: Record<string, any>;
  format: ExportFormat;
}

export enum ReportType {
  ENGAGEMENT = 'engagement',
  LEARNING = 'learning',
  REVENUE = 'revenue',
  USERS = 'users',
  CONTENT = 'content',
  CUSTOM = 'custom'
}

export enum ExportFormat {
  CSV = 'csv',
  EXCEL = 'xlsx',
  PDF = 'pdf',
  JSON = 'json'
}

export interface AnalyticsFilters {
  time_range?: TimeRange;
  date_from?: string;
  date_to?: string;
  education_level?: string;
  grade?: string;
  subject?: string;
}

export enum TimeRange {
  TODAY = 'today',
  YESTERDAY = 'yesterday',
  LAST_7_DAYS = 'last_7_days',
  LAST_30_DAYS = 'last_30_days',
  LAST_90_DAYS = 'last_90_days',
  THIS_MONTH = 'this_month',
  LAST_MONTH = 'last_month',
  THIS_YEAR = 'this_year',
  CUSTOM = 'custom'
}
