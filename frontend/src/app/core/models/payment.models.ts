// ============================================================================
// Payment Models - Production Grade
// ============================================================================

// Import shared types from auth.models
import { SubscriptionTier } from './auth.models';

// Enums
export enum PaymentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  REFUNDED = 'refunded',
  PARTIALLY_REFUNDED = 'partially_refunded',
  CANCELLED = 'cancelled',
  DISPUTED = 'disputed',
  EXPIRED = 'expired'
}

export enum PaymentMethod {
  ECOCASH = 'ecocash',
  ONEMONEY = 'onemoney',
  INNBUCKS = 'innbucks',
  TELECASH = 'telecash',
  ZIPIT = 'zipit',
  VISA = 'visa',
  MASTERCARD = 'mastercard',
  BANK_TRANSFER = 'bank_transfer',
  CARD = 'card',
  PAYPAL = 'paypal'
}

export enum SubscriptionStatus {
  ACTIVE = 'active',
  EXPIRED = 'expired',
  EXPIRING_SOON = 'expiring_soon',
  CANCELLED = 'cancelled',
  SUSPENDED = 'suspended',
  PENDING = 'pending'
}

export enum BillingCycle {
  MONTHLY = 'monthly',
  QUARTERLY = 'quarterly',
  YEARLY = 'yearly'
}

// Payment Interfaces
export interface Payment {
  id: string;
  user_id: string;
  user_email?: string;
  user_phone?: string;
  user_name?: string;
  plan_id?: string;
  plan_name?: string;
  plan_tier?: string;
  amount: number;
  original_amount?: number;
  refunded_amount?: number;
  currency: string;
  status: PaymentStatus;
  payment_method: PaymentMethod;
  payment_reference?: string;
  external_reference?: string;
  gateway_transaction_id?: string;
  error_message?: string;
  failure_reason?: string;
  transaction_id?: string;
  ip_address?: string;
  user_agent?: string;
  payment_metadata?: Record<string, any>;
  refund_history?: RefundRecord[];
  status_history?: StatusChange[];
  created_at: string;
  updated_at?: string;
  completed_at?: string;
  expires_at?: string;
}

export interface RefundRecord {
  reference: string;
  amount: number;
  reason: string;
  internal_notes?: string;
  processed_by?: string;
  processed_at: string;
  notify_user: boolean;
}

export interface StatusChange {
  from_status: string;
  to_status: string;
  changed_at: string;
  changed_by?: string;
  reason?: string;
}

export interface PaymentListResponse {
  payments: Payment[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary?: PaymentSummary;
}

export interface PaymentSummary {
  total_amount: number;
  by_status: Record<string, { count: number; total: number }>;
}

export interface PaymentFilters {
  status?: PaymentStatus;
  payment_method?: PaymentMethod;
  date_from?: string;
  date_to?: string;
  min_amount?: number;
  max_amount?: number;
  user_id?: string;
  search_query?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

// Payment Statistics
export interface PaymentStats {
  // Key Metrics
  mrr: number;
  arr: number;
  active_subscriptions: number;
  total_subscribers: number;

  // Health Metrics
  churn_rate: number;
  ltv: number;
  arpu: number;

  // Transaction Metrics
  total_revenue_30d: number;
  total_transactions_30d: number;
  successful_transactions_30d: number;
  failed_transactions_30d: number;
  refunded_amount_30d: number;
  average_transaction_value: number;

  // Success Metrics
  payment_success_rate: number;
  refund_rate: number;
  dispute_rate: number;

  // Breakdowns
  revenue_by_plan: RevenueByPlan[];
  revenue_by_method: RevenueByMethod[];
  revenue_trend: RevenueTrendItem[];

  // Growth Metrics
  mrr_growth: number;
  subscriber_growth: number;

  // Period Info
  period_start: string;
  period_end: string;
  currency: string;

  // Legacy compatibility
  total_revenue?: number;
  total_transactions?: number;
  successful_transactions?: number;
  failed_transactions?: number;
  refunded_amount?: number;
  average_transaction?: number;
}

export interface RevenueByPlan {
  plan_id: string;
  plan_name: string;
  tier: string;
  revenue: number;
  transaction_count: number;
  percentage: number;
}

export interface RevenueByMethod {
  method: string;
  revenue: number;
  transaction_count: number;
  percentage: number;
  success_rate: number;
}

export interface RevenueTrendItem {
  date: string;
  revenue: number;
  transaction_count: number;
  new_subscriptions?: number;
  churned_subscriptions?: number;
}

// Refund
export interface RefundRequest {
  reason: string;
  refund_type?: 'full' | 'partial';
  partial_amount?: number;
  notify_user?: boolean;
  internal_notes?: string;
}

export interface RefundResponse {
  success: boolean;
  payment_id: string;
  refund_amount: number;
  refund_reference?: string;
  new_payment_status: PaymentStatus;
  message: string;
  processed_at: string;
  processed_by?: string;
}

// Subscription Interfaces
export interface Subscription {
  user_id: string;
  phone_number?: string;
  email?: string;
  user_name?: string;
  tier: string;
  plan_id?: string;
  plan_name?: string;
  status: SubscriptionStatus;
  expires_at?: string;
  started_at?: string;
  is_active: boolean;
  days_remaining: number;
  auto_renew: boolean;
  next_billing_date?: string;
  last_payment_id?: string;
  last_payment_date?: string;
  total_spent?: number;
  created_at?: string;
  id?: string;
  amount?: number;
  currency?: string;
  billing_cycle?: BillingCycle;
}

export interface SubscriptionListResponse {
  subscriptions: Subscription[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary?: SubscriptionSummary;
}

export interface SubscriptionSummary {
  active: number;
  expiring_soon: number;
  expired: number;
  by_tier: Record<string, number>;
}

export interface SubscriptionFilters {
  tier?: SubscriptionTier;
  status?: 'active' | 'expired' | 'expiring_soon';
  search_query?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface ModifySubscriptionRequest {
  new_tier: SubscriptionTier;
  expires_at?: string;
  reason: string;
  notify_user?: boolean;
}

export interface ModifySubscriptionResponse {
  success: boolean;
  user_id: string;
  old_tier: string;
  new_tier: string;
  old_expires_at?: string;
  expires_at?: string;
  message: string;
  modified_at: string;
  modified_by?: string;
}

// Plan Interfaces
export interface Plan {
  id: string;
  name: string;
  tier: SubscriptionTier;
  description?: string;
  price_usd: number;
  price_zwl?: number;
  price_monthly?: number;
  price_quarterly?: number;
  price_yearly?: number;
  duration_days: number;
  features: string[];
  limits: PlanLimits;
  max_students: number;
  discount_percentage: number;
  is_popular: boolean;
  is_active: boolean;
  subscriber_count?: number;
  currency?: string;
  max_messages_per_day?: number;
  max_sessions_per_day?: number;
  created_at: string;
  updated_at?: string;
}

export interface PlanLimits {
  daily_questions: number;
  max_subjects: number;
  max_practice_sessions: number;
  ai_explanations: boolean;
  priority_support: boolean;
  offline_access: boolean;
  parent_dashboard: boolean;
  progress_reports: boolean;
  advanced_analytics: boolean;
}

export interface PlanListResponse {
  items: Plan[];
  total: number;
  active_count: number;
  popular_plan_id?: string;
}

export interface CreatePlanRequest {
  name: string;
  tier: SubscriptionTier;
  description?: string;
  price_usd: number;
  price_zwl?: number;
  duration_days: number;
  features: string[];
  limits?: Partial<PlanLimits>;
  max_students?: number;
  discount_percentage?: number;
  is_popular?: boolean;
}

export interface UpdatePlanRequest {
  name?: string;
  description?: string;
  price_usd?: number;
  price_zwl?: number;
  features?: string[];
  limits?: Partial<PlanLimits>;
  discount_percentage?: number;
  is_popular?: boolean;
  is_active?: boolean;
}

// Export Interfaces
export interface PaymentExportRequest {
  format: 'csv' | 'xlsx' | 'pdf';
  date_from?: string;
  date_to?: string;
  status?: PaymentStatus[];
  payment_method?: PaymentMethod[];
  include_user_details?: boolean;
  include_metadata?: boolean;
}

export interface PaymentExportResponse {
  success: boolean;
  file_name: string;
  data?: string;
  file_url?: string;
  file_size?: number;
  record_count: number;
  generated_at: string;
  expires_at?: string;
}

// Reconciliation Interfaces
export interface ReconciliationRequest {
  start_date: string;
  end_date: string;
  payment_method?: PaymentMethod;
  provider_report_data?: string;
}

export interface ReconciliationItem {
  payment_id?: string;
  external_reference: string;
  expected_amount: number;
  actual_amount?: number;
  discrepancy?: number;
  status: 'matched' | 'discrepancy' | 'missing_in_provider' | 'missing_in_system' | 'pending_verification';
  notes?: string;
}

export interface ReconciliationResponse {
  total_payments: number;
  matched: number;
  unmatched: number;
  discrepancies: number;
  total_expected: number;
  total_actual: number;
  total_discrepancy: number;
  items: ReconciliationItem[];
  reconciled_at: string;
  reconciled_by?: string;
}

// Helper Functions
export function getPaymentStatusColor(status: PaymentStatus): string {
  const colors: Record<PaymentStatus, string> = {
    [PaymentStatus.PENDING]: 'warning',
    [PaymentStatus.PROCESSING]: 'info',
    [PaymentStatus.COMPLETED]: 'success',
    [PaymentStatus.FAILED]: 'error',
    [PaymentStatus.REFUNDED]: 'secondary',
    [PaymentStatus.PARTIALLY_REFUNDED]: 'secondary',
    [PaymentStatus.CANCELLED]: 'secondary',
    [PaymentStatus.DISPUTED]: 'error',
    [PaymentStatus.EXPIRED]: 'secondary'
  };
  return colors[status] || 'secondary';
}

export function getPaymentMethodLabel(method: PaymentMethod): string {
  const labels: Record<PaymentMethod, string> = {
    [PaymentMethod.ECOCASH]: 'EcoCash',
    [PaymentMethod.ONEMONEY]: 'OneMoney',
    [PaymentMethod.INNBUCKS]: 'InnBucks',
    [PaymentMethod.TELECASH]: 'Telecash',
    [PaymentMethod.ZIPIT]: 'Zipit',
    [PaymentMethod.VISA]: 'Visa',
    [PaymentMethod.MASTERCARD]: 'Mastercard',
    [PaymentMethod.BANK_TRANSFER]: 'Bank Transfer',
    [PaymentMethod.CARD]: 'Card',
    [PaymentMethod.PAYPAL]: 'PayPal'
  };
  return labels[method] || method;
}

export function getSubscriptionStatusColor(status: SubscriptionStatus): string {
  const colors: Record<SubscriptionStatus, string> = {
    [SubscriptionStatus.ACTIVE]: 'success',
    [SubscriptionStatus.EXPIRED]: 'error',
    [SubscriptionStatus.EXPIRING_SOON]: 'warning',
    [SubscriptionStatus.CANCELLED]: 'secondary',
    [SubscriptionStatus.SUSPENDED]: 'error',
    [SubscriptionStatus.PENDING]: 'info'
  };
  return colors[status] || 'secondary';
}

export function getTierColor(tier: SubscriptionTier): string {
  const colors: Record<SubscriptionTier, string> = {
    [SubscriptionTier.FREE]: 'secondary',
    [SubscriptionTier.BASIC]: 'info',
    [SubscriptionTier.PREMIUM]: 'primary',
    [SubscriptionTier.FAMILY]: 'success',
    [SubscriptionTier.SCHOOL]: 'warning',
    [SubscriptionTier.ENTERPRISE]: 'primary'
  };
  return colors[tier] || 'secondary';
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(amount);
}

export function formatCompactCurrency(amount: number): string {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M`;
  }
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(1)}K`;
  }
  return formatCurrency(amount);
}
