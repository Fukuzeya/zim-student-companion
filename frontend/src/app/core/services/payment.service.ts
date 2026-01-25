import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import {
  PaymentListResponse,
  PaymentFilters,
  Payment,
  PaymentStats,
  RefundRequest,
  RefundResponse,
  Subscription,
  SubscriptionListResponse,
  SubscriptionFilters,
  ModifySubscriptionRequest,
  ModifySubscriptionResponse,
  Plan,
  PlanListResponse,
  CreatePlanRequest,
  UpdatePlanRequest,
  PaymentExportRequest,
  PaymentExportResponse,
  ReconciliationRequest,
  ReconciliationResponse
} from '../models';

@Injectable({
  providedIn: 'root',
})
export class PaymentService {
  private readonly basePath = '/admin';

  constructor(private api: ApiService) {}

  // =========================================================================
  // Payments
  // =========================================================================

  /**
   * Get paginated list of payments with filtering
   */
  getPayments(filters?: PaymentFilters): Observable<PaymentListResponse> {
    const params: Record<string, any> = {};

    if (filters) {
      if (filters.status) params['status'] = filters.status;
      if (filters.payment_method) params['payment_method'] = filters.payment_method;
      if (filters.date_from) params['date_from'] = filters.date_from;
      if (filters.date_to) params['date_to'] = filters.date_to;
      if (filters.min_amount !== undefined) params['min_amount'] = filters.min_amount;
      if (filters.max_amount !== undefined) params['max_amount'] = filters.max_amount;
      if (filters.user_id) params['user_id'] = filters.user_id;
      if (filters.search_query) params['search_query'] = filters.search_query;
      if (filters.sort_by) params['sort_by'] = filters.sort_by;
      if (filters.sort_order) params['sort_order'] = filters.sort_order;
      if (filters.page) params['page'] = filters.page;
      if (filters.page_size) params['page_size'] = filters.page_size;
    }

    return this.api.get<PaymentListResponse>(`${this.basePath}/payments`, params);
  }

  /**
   * Get detailed information for a single payment
   */
  getPaymentById(paymentId: string): Observable<Payment> {
    return this.api.get<Payment>(`${this.basePath}/payments/${paymentId}`);
  }

  /**
   * Process a refund for a payment
   */
  refundPayment(paymentId: string, data: RefundRequest): Observable<RefundResponse> {
    // Convert to form data for backend compatibility
    const formData = new FormData();
    formData.append('reason', data.reason);
    if (data.partial_amount !== undefined) {
      formData.append('partial_amount', data.partial_amount.toString());
    }

    return this.api.post<RefundResponse>(
      `${this.basePath}/payments/${paymentId}/refund`,
      formData
    );
  }

  /**
   * Get comprehensive payment statistics
   */
  getPaymentStats(periodDays: number = 30): Observable<PaymentStats> {
    return this.api.get<PaymentStats>(`${this.basePath}/payments/stats`, {
      period_days: periodDays
    });
  }

  /**
   * Get payment details by ID
   */
  getPaymentDetails(paymentId: string): Observable<Payment> {
    return this.api.get<Payment>(`${this.basePath}/payments/${paymentId}`);
  }

  /**
   * Export payments to file
   */
  exportPayments(request: PaymentExportRequest): Observable<PaymentExportResponse> {
    return this.api.post<PaymentExportResponse>(
      `${this.basePath}/payments/export`,
      request
    );
  }

  /**
   * Download exported payment file
   */
  downloadExport(fileName: string): Observable<Blob> {
    return this.api.download(`${this.basePath}/payments/export/${fileName}`);
  }

  /**
   * Reconcile payments with provider data
   */
  reconcilePayments(request: ReconciliationRequest): Observable<ReconciliationResponse> {
    return this.api.post<ReconciliationResponse>(
      `${this.basePath}/payments/reconcile`,
      request
    );
  }

  // =========================================================================
  // Subscriptions
  // =========================================================================

  /**
   * Get paginated list of subscriptions with filtering
   */
  getSubscriptions(filters?: SubscriptionFilters): Observable<SubscriptionListResponse> {
    const params: Record<string, any> = {};

    if (filters) {
      if (filters.tier) params['tier'] = filters.tier;
      if (filters.status) params['status'] = filters.status;
      if (filters.search_query) params['search_query'] = filters.search_query;
      if (filters.sort_by) params['sort_by'] = filters.sort_by;
      if (filters.sort_order) params['sort_order'] = filters.sort_order;
      if (filters.page) params['page'] = filters.page;
      if (filters.page_size) params['page_size'] = filters.page_size;
    }

    return this.api.get<SubscriptionListResponse>(`${this.basePath}/subscriptions`, params);
  }

  /**
   * Get subscription details for a specific user
   */
  getSubscriptionByUserId(userId: string): Observable<Subscription> {
    return this.api.get<Subscription>(`${this.basePath}/subscriptions/${userId}`);
  }

  /**
   * Modify a user's subscription
   */
  modifySubscription(
    userId: string,
    data: ModifySubscriptionRequest
  ): Observable<ModifySubscriptionResponse> {
    // Convert to form data for backend compatibility
    const formData = new FormData();
    formData.append('new_tier', data.new_tier);
    formData.append('reason', data.reason);
    if (data.expires_at) {
      formData.append('expires_at', data.expires_at);
    }
    if (data.notify_user !== undefined) {
      formData.append('notify_user', data.notify_user.toString());
    }

    return this.api.post<ModifySubscriptionResponse>(
      `${this.basePath}/subscriptions/${userId}/modify`,
      formData
    );
  }

  /**
   * Cancel a subscription
   */
  cancelSubscription(userId: string, reason: string): Observable<ModifySubscriptionResponse> {
    return this.modifySubscription(userId, {
      new_tier: 'free' as any,
      reason: reason,
      notify_user: true
    });
  }

  /**
   * Extend a subscription
   */
  extendSubscription(
    userId: string,
    days: number,
    reason: string
  ): Observable<ModifySubscriptionResponse> {
    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + days);

    const formData = new FormData();
    formData.append('extends_at', expiresAt.toISOString());
    formData.append('reason', reason);

    return this.api.post<ModifySubscriptionResponse>(
      `${this.basePath}/subscriptions/${userId}/extend`,
      formData
    );
  }

  // =========================================================================
  // Plans
  // =========================================================================

  /**
   * Get all subscription plans
   */
  getPlans(includeInactive: boolean = false): Observable<PlanListResponse> {
    return this.api.get<PlanListResponse>(`${this.basePath}/plans`, {
      include_inactive: includeInactive
    });
  }

  /**
   * Get a specific plan by ID
   */
  getPlanById(planId: string): Observable<Plan> {
    return this.api.get<Plan>(`${this.basePath}/plans/${planId}`);
  }

  /**
   * Create a new subscription plan
   */
  createPlan(data: CreatePlanRequest): Observable<{ success: boolean; id: string; message: string }> {
    // Convert to form data for backend compatibility
    const formData = new FormData();
    formData.append('name', data.name);
    formData.append('tier', data.tier);
    formData.append('price_usd', data.price_usd.toString());
    formData.append('duration_days', data.duration_days.toString());

    if (data.description) formData.append('description', data.description);
    if (data.price_zwl !== undefined) formData.append('price_zwl', data.price_zwl.toString());
    if (data.features) formData.append('features', JSON.stringify(data.features));
    if (data.limits) formData.append('limits', JSON.stringify(data.limits));
    if (data.max_students !== undefined) formData.append('max_students', data.max_students.toString());
    if (data.discount_percentage !== undefined) formData.append('discount_percentage', data.discount_percentage.toString());
    if (data.is_popular !== undefined) formData.append('is_popular', data.is_popular.toString());

    return this.api.post(`${this.basePath}/plans`, formData);
  }

  /**
   * Update an existing subscription plan
   */
  updatePlan(
    planId: string,
    data: UpdatePlanRequest
  ): Observable<{ success: boolean; id: string; message: string; changes?: any[] }> {
    // Convert to form data for backend compatibility
    const formData = new FormData();

    if (data.name !== undefined) formData.append('name', data.name);
    if (data.description !== undefined) formData.append('description', data.description);
    if (data.price_usd !== undefined) formData.append('price_usd', data.price_usd.toString());
    if (data.price_zwl !== undefined) formData.append('price_zwl', data.price_zwl.toString());
    if (data.features !== undefined) formData.append('features', JSON.stringify(data.features));
    if (data.limits !== undefined) formData.append('limits', JSON.stringify(data.limits));
    if (data.discount_percentage !== undefined) formData.append('discount_percentage', data.discount_percentage.toString());
    if (data.is_popular !== undefined) formData.append('is_popular', data.is_popular.toString());
    if (data.is_active !== undefined) formData.append('is_active', data.is_active.toString());

    return this.api.put(`${this.basePath}/plans/${planId}`, formData);
  }

  /**
   * Delete (deactivate) a subscription plan
   */
  deletePlan(planId: string): Observable<{ success: boolean; message: string }> {
    return this.api.delete(`${this.basePath}/plans/${planId}`);
  }

  /**
   * Toggle plan popularity status
   */
  togglePlanPopular(planId: string, isPopular: boolean): Observable<{ success: boolean }> {
    return this.updatePlan(planId, { is_popular: isPopular });
  }

  /**
   * Toggle plan active status
   */
  togglePlanActive(planId: string, isActive: boolean): Observable<{ success: boolean }> {
    return this.updatePlan(planId, { is_active: isActive });
  }

  // =========================================================================
  // Analytics & Reports
  // =========================================================================

  /**
   * Get revenue analytics
   */
  getRevenueAnalytics(
    timeRange: string = 'last_30_days',
    dateFrom?: string,
    dateTo?: string
  ): Observable<any> {
    const params: Record<string, any> = { time_range: timeRange };
    if (dateFrom) params['date_from'] = dateFrom;
    if (dateTo) params['date_to'] = dateTo;

    return this.api.get(`${this.basePath}/analytics/revenue`, params);
  }

  /**
   * Generate a report
   */
  generateReport(
    reportType: string,
    format: string = 'pdf',
    timeRange: string = 'last_30_days'
  ): Observable<any> {
    const formData = new FormData();
    formData.append('report_type', reportType);
    formData.append('format', format);
    formData.append('time_range', timeRange);

    return this.api.post(`${this.basePath}/reports/generate`, formData);
  }
}
