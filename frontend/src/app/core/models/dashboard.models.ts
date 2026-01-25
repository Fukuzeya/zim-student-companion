// Dashboard models matching backend API response schema

// ============================================================================
// KPI Card Response (from /api/v1/admin/dashboard/stats)
// ============================================================================
export interface KPICard {
  value: number | string;
  label: string;
  change_percent: number | null;
  change_direction: 'up' | 'down' | 'stable' | null;
  period: string;
  suffix?: string;
  currency?: string;
}

export interface DashboardStats {
  total_users: KPICard;
  active_students_today: KPICard;
  messages_24h: KPICard;
  revenue_this_month: KPICard;
  active_subscriptions: KPICard;
  conversion_rate: KPICard;
  avg_session_duration: KPICard;
  questions_answered_today: KPICard;
}

// ============================================================================
// Chart Data Response (from /api/v1/admin/dashboard/charts)
// ============================================================================
export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
  label?: string;
}

export interface ChartDataPoint {
  label: string;
  value: number;
  metadata?: Record<string, any>;
}

export interface DashboardCharts {
  user_growth: TimeSeriesPoint[];
  revenue_trend: TimeSeriesPoint[];
  subscription_distribution: ChartDataPoint[];
  active_hours_heatmap: Record<string, number[]>;
  subject_popularity: ChartDataPoint[];
  daily_active_users: TimeSeriesPoint[];
}

// ============================================================================
// Activity Feed Response (from /api/v1/admin/dashboard/activity)
// ============================================================================
export interface ActivityItem {
  id: string;
  type: ActivityType;
  title: string;
  description: string;
  user_id?: string;
  user_name?: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export enum ActivityType {
  REGISTRATION = 'registration',
  UPGRADE = 'upgrade',
  COMPETITION = 'competition',
  TICKET = 'ticket',
  ALERT = 'alert'
}

export interface DashboardActivity {
  items: ActivityItem[];
  total_count: number;
  has_more: boolean;
}

// ============================================================================
// Legacy/Compatibility Types (for gradual migration)
// ============================================================================
export enum HealthStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  DOWN = 'down',
  UNKNOWN = 'unknown'
}

export interface SystemHealth {
  api_status: HealthStatus;
  database_status: HealthStatus;
  vector_store_status: HealthStatus;
  cache_status: HealthStatus;
  websocket_status: HealthStatus;
  avg_response_time: number;
  uptime_percentage: number;
}

// ============================================================================
// UI Component Types
// ============================================================================
export interface KpiCardConfig {
  title: string;
  value: string | number;
  icon: string;
  iconColor?: string;
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
    label: string;
    isPercentage?: boolean;
  };
  progress?: number;
  progressColor?: string;
  suffix?: string;
  prefix?: string;
}
