// System and settings models based on OpenAPI specification

export interface AuditLogEntry {
  id: string;
  action: AuditAction;
  entity_type: string;
  entity_id: string;
  user_id: string;
  user_email: string;
  user_role: string;
  ip_address: string;
  user_agent: string;
  details: Record<string, any>;
  timestamp: string;
  status: AuditStatus;
}

export enum AuditAction {
  CREATE = 'create',
  UPDATE = 'update',
  DELETE = 'delete',
  LOGIN = 'login',
  LOGOUT = 'logout',
  EXPORT = 'export',
  IMPORT = 'import',
  BULK_ACTION = 'bulk_action',
  PERMISSION_CHANGE = 'permission_change',
  SETTINGS_CHANGE = 'settings_change'
}

export enum AuditStatus {
  SUCCESS = 'success',
  FAILURE = 'failure',
  PARTIAL = 'partial'
}

export interface AuditLogResponse {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogFilters {
  action?: AuditAction;
  entity_type?: string;
  user_id?: string;
  date_from?: string;
  date_to?: string;
  status?: AuditStatus;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface GlobalSettings {
  site_name: string;
  site_description: string;
  support_email: string;
  support_phone: string;
  timezone: string;
  date_format: string;
  currency: string;
  maintenance_mode: boolean;
  maintenance_message?: string;
  registration_enabled: boolean;
  require_email_verification: boolean;
  require_phone_verification: boolean;
  max_login_attempts: number;
  session_timeout_minutes: number;
  ai_settings: AISettings;
  notification_settings: NotificationSettings;
}

export interface AISettings {
  model_name: string;
  max_tokens_per_message: number;
  max_messages_per_day_free: number;
  max_messages_per_day_basic: number;
  max_messages_per_day_premium: number;
  temperature: number;
  enable_content_filtering: boolean;
  enable_rag: boolean;
}

export interface NotificationSettings {
  email_notifications_enabled: boolean;
  sms_notifications_enabled: boolean;
  push_notifications_enabled: boolean;
  marketing_emails_enabled: boolean;
}

export interface FeatureFlag {
  id: string;
  name: string;
  description: string;
  is_enabled: boolean;
  rollout_percentage?: number;
  user_roles?: string[];
  created_at: string;
  updated_at: string;
}

export interface SystemHealthStatus {
  status: OverallStatus;
  components: ComponentHealth[];
  last_checked: string;
  uptime_seconds: number;
}

export enum OverallStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  CRITICAL = 'critical',
  UNKNOWN = 'unknown'
}

export interface ComponentHealth {
  name: string;
  status: OverallStatus;
  response_time_ms?: number;
  last_checked: string;
  error_message?: string;
  details?: Record<string, any>;
}

export interface ErrorLog {
  id: string;
  level: ErrorLevel;
  message: string;
  stack_trace?: string;
  source: string;
  user_id?: string;
  request_id?: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export enum ErrorLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical'
}

export interface ErrorLogResponse {
  items: ErrorLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: NotificationType;
  channel: NotificationChannel;
  target_type: TargetType;
  target_ids?: string[];
  target_filters?: Record<string, any>;
  status: NotificationStatus;
  sent_count: number;
  delivered_count: number;
  read_count: number;
  scheduled_at?: string;
  sent_at?: string;
  created_by: string;
  created_at: string;
}

export enum NotificationType {
  INFO = 'info',
  WARNING = 'warning',
  ALERT = 'alert',
  PROMOTION = 'promotion',
  SYSTEM = 'system'
}

export enum NotificationChannel {
  EMAIL = 'email',
  SMS = 'sms',
  PUSH = 'push',
  IN_APP = 'in_app',
  ALL = 'all'
}

export enum TargetType {
  ALL_USERS = 'all_users',
  SPECIFIC_USERS = 'specific_users',
  USER_SEGMENT = 'user_segment',
  ROLE_BASED = 'role_based'
}

export enum NotificationStatus {
  DRAFT = 'draft',
  SCHEDULED = 'scheduled',
  SENDING = 'sending',
  SENT = 'sent',
  FAILED = 'failed'
}

export interface BroadcastRequest {
  title: string;
  message: string;
  type: NotificationType;
  channel: NotificationChannel;
  target_type: TargetType;
  target_ids?: string[];
  target_filters?: Record<string, any>;
  scheduled_at?: string;
}

export interface RAGStats {
  total_documents: number;
  total_chunks: number;
  total_embeddings: number;
  index_size_mb: number;
  avg_query_time_ms: number;
  documents_by_status: DocumentsByStatus;
  recent_queries: RecentQuery[];
}

export interface DocumentsByStatus {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export interface RecentQuery {
  query: string;
  response_time_ms: number;
  chunks_retrieved: number;
  timestamp: string;
}
