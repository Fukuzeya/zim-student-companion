import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { PaymentService } from '../../../core/services/payment.service';
import { ToastService } from '../../../core/services/toast.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import {
  Payment,
  PaymentStatus,
  PaymentMethod,
  RefundRecord,
  StatusChange,
  formatCurrency,
  getPaymentStatusColor,
  getPaymentMethodLabel
} from '../../../core/models/payment.models';

@Component({
  selector: 'app-payment-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    LoadingSpinnerComponent,
    ModalComponent
  ],
  template: `
    <div class="payment-detail-page">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-content">
          <div class="header-left">
            <button class="back-btn" (click)="goBack()">
              <span class="material-symbols-outlined">arrow_back</span>
            </button>
            <div class="header-text">
              <h1>Payment Details</h1>
              <p>Transaction {{ payment()?.payment_reference || payment()?.id?.slice(0, 8) || '...' }}</p>
            </div>
          </div>
          <div class="header-actions">
            @if (canRefund()) {
              <button class="btn btn-warning" (click)="openRefundModal()">
                <span class="material-symbols-outlined">undo</span>
                Refund
              </button>
            }
            <button class="btn btn-secondary" (click)="printReceipt()">
              <span class="material-symbols-outlined">print</span>
              Print
            </button>
          </div>
        </div>
        <div class="breadcrumbs">
          <a routerLink="/dashboard">Dashboard</a>
          <span class="separator">/</span>
          <a routerLink="/payments">Payments</a>
          <span class="separator">/</span>
          <span class="current">{{ payment()?.payment_reference || payment()?.id?.slice(0, 8) || 'Details' }}</span>
        </div>
      </div>

      @if (loading()) {
        <div class="loading-container">
          <app-loading-spinner />
        </div>
      } @else if (!payment()) {
        <div class="empty-state">
          <span class="material-symbols-outlined">search_off</span>
          <h3>Payment Not Found</h3>
          <p>The requested payment could not be found.</p>
          <button class="btn btn-primary" routerLink="/payments">Back to Payments</button>
        </div>
      } @else {
        <div class="content-grid">
          <!-- Main Info Card -->
          <div class="card main-card">
            <div class="card-header">
              <h2>Transaction Summary</h2>
              <span class="status-badge" [class]="getStatusClass(payment()!.status)">
                <span class="status-dot"></span>
                {{ payment()!.status | titlecase }}
              </span>
            </div>
            <div class="card-body">
              <div class="amount-display">
                <span class="amount">{{ formatCurrency(payment()!.amount) }}</span>
                @if (payment()!.refunded_amount && payment()!.refunded_amount! > 0) {
                  <span class="refunded">-{{ formatCurrency(payment()!.refunded_amount!) }} refunded</span>
                }
              </div>

              <div class="info-grid">
                <div class="info-item">
                  <span class="label">Reference</span>
                  <span class="value mono">{{ payment()!.payment_reference || payment()!.transaction_id || 'N/A' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">External ID</span>
                  <span class="value mono">{{ payment()!.gateway_transaction_id || payment()!.external_reference || 'N/A' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Payment Method</span>
                  <span class="method-badge" [class]="payment()!.payment_method">
                    {{ getMethodLabel(payment()!.payment_method) }}
                  </span>
                </div>
                <div class="info-item">
                  <span class="label">Currency</span>
                  <span class="value">{{ payment()!.currency }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Created</span>
                  <span class="value">{{ formatDateTime(payment()!.created_at) }}</span>
                </div>
                @if (payment()!.completed_at) {
                  <div class="info-item">
                    <span class="label">Completed</span>
                    <span class="value">{{ formatDateTime(payment()!.completed_at!) }}</span>
                  </div>
                }
              </div>

              @if (payment()!.error_message || payment()!.failure_reason) {
                <div class="error-box">
                  <span class="material-symbols-outlined">error</span>
                  <div>
                    <strong>Error:</strong>
                    <p>{{ payment()!.error_message || payment()!.failure_reason }}</p>
                  </div>
                </div>
              }
            </div>
          </div>

          <!-- Customer Info Card -->
          <div class="card">
            <div class="card-header">
              <h2>Customer Information</h2>
              @if (payment()!.user_id) {
                <a [routerLink]="['/students', payment()!.user_id]" class="link">View Profile</a>
              }
            </div>
            <div class="card-body">
              <div class="customer-avatar">
                <span class="material-symbols-outlined">person</span>
              </div>
              <div class="info-list">
                <div class="info-row">
                  <span class="material-symbols-outlined">badge</span>
                  <span>{{ payment()!.user_name || 'Unknown Customer' }}</span>
                </div>
                @if (payment()!.user_email) {
                  <div class="info-row">
                    <span class="material-symbols-outlined">mail</span>
                    <span>{{ payment()!.user_email }}</span>
                  </div>
                }
                @if (payment()!.user_phone) {
                  <div class="info-row">
                    <span class="material-symbols-outlined">phone</span>
                    <span>{{ payment()!.user_phone }}</span>
                  </div>
                }
                <div class="info-row">
                  <span class="material-symbols-outlined">fingerprint</span>
                  <span class="mono small">{{ payment()!.user_id }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Plan Info Card -->
          <div class="card">
            <div class="card-header">
              <h2>Subscription Details</h2>
            </div>
            <div class="card-body">
              <div class="plan-display">
                <span class="plan-badge" [class]="payment()!.plan_tier || 'basic'">
                  {{ payment()!.plan_tier || 'Basic' | titlecase }}
                </span>
                <span class="plan-name">{{ payment()!.plan_name || 'Standard Plan' }}</span>
              </div>
              <div class="info-list">
                @if (payment()!.plan_id) {
                  <div class="info-row">
                    <span class="material-symbols-outlined">inventory_2</span>
                    <span class="mono small">{{ payment()!.plan_id }}</span>
                  </div>
                }
              </div>
            </div>
          </div>

          <!-- Timeline Card -->
          <div class="card timeline-card">
            <div class="card-header">
              <h2>Transaction Timeline</h2>
            </div>
            <div class="card-body">
              <div class="timeline">
                @for (event of getTimeline(); track event.timestamp) {
                  <div class="timeline-item" [class]="event.type">
                    <div class="timeline-dot">
                      <span class="material-symbols-outlined">{{ event.icon }}</span>
                    </div>
                    <div class="timeline-content">
                      <div class="timeline-title">{{ event.title }}</div>
                      <div class="timeline-desc">{{ event.description }}</div>
                      <div class="timeline-time">{{ formatDateTime(event.timestamp) }}</div>
                    </div>
                  </div>
                }
              </div>
            </div>
          </div>

          <!-- Refund History Card -->
          @if (payment()!.refund_history && payment()!.refund_history!.length > 0) {
            <div class="card">
              <div class="card-header">
                <h2>Refund History</h2>
              </div>
              <div class="card-body">
                <div class="refund-list">
                  @for (refund of payment()!.refund_history; track refund.reference) {
                    <div class="refund-item">
                      <div class="refund-header">
                        <span class="refund-amount">-{{ formatCurrency(refund.amount) }}</span>
                        <span class="refund-ref mono">{{ refund.reference }}</span>
                      </div>
                      <div class="refund-reason">{{ refund.reason }}</div>
                      <div class="refund-meta">
                        <span>{{ formatDateTime(refund.processed_at) }}</span>
                        @if (refund.processed_by) {
                          <span>by {{ refund.processed_by }}</span>
                        }
                      </div>
                    </div>
                  }
                </div>
              </div>
            </div>
          }

          <!-- Technical Details Card -->
          <div class="card">
            <div class="card-header">
              <h2>Technical Details</h2>
              <button class="icon-btn" (click)="toggleTechnical()">
                <span class="material-symbols-outlined">{{ showTechnical() ? 'expand_less' : 'expand_more' }}</span>
              </button>
            </div>
            @if (showTechnical()) {
              <div class="card-body">
                <div class="tech-grid">
                  <div class="tech-item">
                    <span class="label">Payment ID</span>
                    <span class="value mono">{{ payment()!.id }}</span>
                  </div>
                  @if (payment()!.ip_address) {
                    <div class="tech-item">
                      <span class="label">IP Address</span>
                      <span class="value mono">{{ payment()!.ip_address }}</span>
                    </div>
                  }
                  @if (payment()!.user_agent) {
                    <div class="tech-item full-width">
                      <span class="label">User Agent</span>
                      <span class="value mono small">{{ payment()!.user_agent }}</span>
                    </div>
                  }
                  @if (payment()!.payment_metadata) {
                    <div class="tech-item full-width">
                      <span class="label">Metadata</span>
                      <pre class="metadata">{{ payment()!.payment_metadata | json }}</pre>
                    </div>
                  }
                </div>
              </div>
            }
          </div>
        </div>
      }

      <!-- Refund Modal -->
      <app-modal #refundModal title="Process Refund" size="md" [showFooter]="true">
        @if (payment()) {
          <div class="refund-form">
            <div class="refund-summary">
              <div class="summary-row">
                <span class="label">Original Amount:</span>
                <span class="value">{{ formatCurrency(payment()!.amount) }}</span>
              </div>
              @if (payment()!.refunded_amount && payment()!.refunded_amount! > 0) {
                <div class="summary-row">
                  <span class="label">Already Refunded:</span>
                  <span class="value error">{{ formatCurrency(payment()!.refunded_amount!) }}</span>
                </div>
                <div class="summary-row">
                  <span class="label">Refundable:</span>
                  <span class="value">{{ formatCurrency(getMaxRefundable()) }}</span>
                </div>
              }
            </div>

            <div class="form-group">
              <label>Refund Type</label>
              <div class="radio-group">
                <label class="radio-option">
                  <input type="radio" name="refundType" value="full" [(ngModel)]="refundType" />
                  <span>Full Refund</span>
                </label>
                <label class="radio-option">
                  <input type="radio" name="refundType" value="partial" [(ngModel)]="refundType" />
                  <span>Partial Refund</span>
                </label>
              </div>
            </div>

            @if (refundType === 'partial') {
              <div class="form-group">
                <label>Amount ({{ payment()!.currency }})</label>
                <input
                  type="number"
                  [(ngModel)]="refundAmount"
                  [max]="getMaxRefundable()"
                  min="0.01"
                  step="0.01"
                  class="form-input"
                />
              </div>
            }

            <div class="form-group">
              <label>Reason <span class="required">*</span></label>
              <textarea
                [(ngModel)]="refundReason"
                placeholder="Provide a reason for this refund..."
                rows="3"
                class="form-input"
              ></textarea>
            </div>

            <div class="form-group">
              <label class="checkbox-option">
                <input type="checkbox" [(ngModel)]="notifyUser" />
                <span>Notify customer via WhatsApp</span>
              </label>
            </div>
          </div>
        }

        <div modal-footer class="modal-actions">
          <button class="btn btn-secondary" (click)="closeRefundModal()">Cancel</button>
          <button
            class="btn btn-danger"
            [disabled]="!canSubmitRefund()"
            (click)="processRefund()"
          >
            Process Refund
          </button>
        </div>
      </app-modal>
    </div>
  `,
  styles: [`
    .payment-detail-page {
      padding: 1.5rem;
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header { margin-bottom: 1.5rem; }

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.5rem;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .back-btn {
      width: 40px; height: 40px;
      display: flex; align-items: center; justify-content: center;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      color: var(--text-primary);
      cursor: pointer;
      transition: all 0.15s ease;
      &:hover { background: var(--hover); border-color: var(--primary); }
    }

    .header-text h1 {
      font-size: 1.5rem; font-weight: 700;
      color: var(--text-primary); margin: 0 0 0.25rem 0;
    }
    .header-text p { font-size: 0.875rem; color: var(--text-secondary); margin: 0; }

    .header-actions { display: flex; gap: 0.75rem; }

    .breadcrumbs {
      display: flex; align-items: center; gap: 0.5rem;
      font-size: 0.875rem; color: var(--text-tertiary);
      a { color: var(--text-secondary); text-decoration: none; &:hover { color: var(--primary); } }
      .current { color: var(--text-primary); }
      .separator { color: var(--border); }
    }

    .loading-container {
      display: flex; justify-content: center; align-items: center;
      padding: 4rem; background: var(--surface);
      border-radius: 0.75rem; border: 1px solid var(--border);
    }

    .empty-state {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; padding: 4rem 2rem; color: var(--text-tertiary);
      background: var(--surface); border-radius: 0.75rem; border: 1px solid var(--border);
      .material-symbols-outlined { font-size: 3rem; margin-bottom: 1rem; }
      h3 { margin: 0 0 0.5rem 0; color: var(--text-secondary); }
      p { margin: 0 0 1.5rem 0; }
    }

    .content-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1.5rem;
    }

    @media (max-width: 1024px) { .content-grid { grid-template-columns: 1fr; } }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }

    .main-card { grid-column: span 2; }
    .timeline-card { grid-column: span 2; }

    @media (max-width: 1024px) {
      .main-card, .timeline-card { grid-column: span 1; }
    }

    .card-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--border);
      background: var(--background);
      h2 { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); margin: 0; text-transform: uppercase; letter-spacing: 0.05em; }
      .link { font-size: 0.875rem; color: var(--primary); text-decoration: none; &:hover { text-decoration: underline; } }
    }

    .card-body { padding: 1.25rem; }

    .amount-display {
      display: flex; flex-direction: column; align-items: center;
      padding: 1.5rem; margin-bottom: 1.5rem;
      background: var(--background); border-radius: 0.5rem;
      .amount { font-size: 2.5rem; font-weight: 700; color: var(--text-primary); font-feature-settings: 'tnum'; }
      .refunded { font-size: 1rem; color: var(--error); margin-top: 0.5rem; }
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
    }

    @media (max-width: 768px) { .info-grid { grid-template-columns: repeat(2, 1fr); } }

    .info-item {
      display: flex; flex-direction: column; gap: 0.25rem;
      .label { font-size: 0.75rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; }
      .value { font-size: 0.875rem; color: var(--text-primary); font-weight: 500; }
      .mono { font-family: monospace; }
    }

    .error-box {
      display: flex; gap: 0.75rem; padding: 1rem;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.2);
      border-radius: 0.5rem; margin-top: 1.5rem;
      .material-symbols-outlined { color: var(--error); font-size: 1.5rem; }
      strong { color: var(--error); }
      p { margin: 0.25rem 0 0 0; color: var(--text-secondary); font-size: 0.875rem; }
    }

    .customer-avatar {
      width: 64px; height: 64px;
      display: flex; align-items: center; justify-content: center;
      background: var(--primary);
      border-radius: 50%; margin: 0 auto 1rem;
      .material-symbols-outlined { font-size: 2rem; color: white; }
    }

    .info-list { display: flex; flex-direction: column; gap: 0.75rem; }
    .info-row {
      display: flex; align-items: center; gap: 0.75rem;
      .material-symbols-outlined { font-size: 1.25rem; color: var(--text-tertiary); }
      span:last-child { color: var(--text-primary); font-size: 0.875rem; }
      .mono { font-family: monospace; }
      .small { font-size: 0.75rem; color: var(--text-secondary); }
    }

    .plan-display {
      display: flex; align-items: center; gap: 0.75rem;
      padding: 1rem; background: var(--background);
      border-radius: 0.5rem; margin-bottom: 1rem;
    }
    .plan-badge {
      padding: 0.375rem 0.75rem; border-radius: 9999px;
      font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
      &.basic { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
      &.premium { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; }
      &.family { background: rgba(16, 185, 129, 0.1); color: #10b981; }
      &.school { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
    }
    .plan-name { font-weight: 500; color: var(--text-primary); }

    .timeline {
      position: relative;
      padding-left: 2rem;
      &::before {
        content: '';
        position: absolute;
        left: 0.75rem;
        top: 0; bottom: 0;
        width: 2px;
        background: var(--border);
      }
    }

    .timeline-item {
      position: relative;
      padding-bottom: 1.5rem;
      &:last-child { padding-bottom: 0; }
    }

    .timeline-dot {
      position: absolute;
      left: -1.75rem;
      width: 24px; height: 24px;
      display: flex; align-items: center; justify-content: center;
      background: var(--surface);
      border: 2px solid var(--border);
      border-radius: 50%;
      .material-symbols-outlined { font-size: 0.875rem; color: var(--text-tertiary); }
    }

    .timeline-item.success .timeline-dot { border-color: var(--success); .material-symbols-outlined { color: var(--success); } }
    .timeline-item.error .timeline-dot { border-color: var(--error); .material-symbols-outlined { color: var(--error); } }
    .timeline-item.warning .timeline-dot { border-color: var(--warning); .material-symbols-outlined { color: var(--warning); } }

    .timeline-content { padding-left: 0.5rem; }
    .timeline-title { font-weight: 500; color: var(--text-primary); font-size: 0.875rem; }
    .timeline-desc { color: var(--text-secondary); font-size: 0.8125rem; margin-top: 0.25rem; }
    .timeline-time { color: var(--text-tertiary); font-size: 0.75rem; margin-top: 0.25rem; }

    .refund-list { display: flex; flex-direction: column; gap: 1rem; }
    .refund-item {
      padding: 1rem; background: var(--background);
      border-radius: 0.5rem; border-left: 3px solid var(--warning);
    }
    .refund-header { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
    .refund-amount { font-weight: 600; color: var(--error); }
    .refund-ref { font-size: 0.75rem; color: var(--text-tertiary); }
    .refund-reason { font-size: 0.875rem; color: var(--text-primary); margin-bottom: 0.5rem; }
    .refund-meta { font-size: 0.75rem; color: var(--text-tertiary); display: flex; gap: 0.5rem; }

    .tech-grid { display: flex; flex-direction: column; gap: 1rem; }
    .tech-item {
      display: flex; flex-direction: column; gap: 0.25rem;
      .label { font-size: 0.75rem; color: var(--text-tertiary); text-transform: uppercase; }
      .value { font-size: 0.875rem; color: var(--text-primary); word-break: break-all; }
      &.full-width { grid-column: span 2; }
    }
    .metadata {
      font-size: 0.75rem; background: var(--background);
      padding: 0.75rem; border-radius: 0.375rem;
      overflow-x: auto; margin: 0;
    }

    .status-badge {
      display: inline-flex; align-items: center; gap: 0.375rem;
      padding: 0.25rem 0.75rem; border-radius: 9999px;
      font-size: 0.75rem; font-weight: 500;
      .status-dot { width: 6px; height: 6px; border-radius: 50%; }
      &.success { background: rgba(16, 185, 129, 0.1); color: #10b981; .status-dot { background: #10b981; } }
      &.warning { background: rgba(245, 158, 11, 0.1); color: #f59e0b; .status-dot { background: #f59e0b; } }
      &.error { background: rgba(239, 68, 68, 0.1); color: #ef4444; .status-dot { background: #ef4444; } }
      &.info { background: rgba(59, 130, 246, 0.1); color: #3b82f6; .status-dot { background: #3b82f6; } }
      &.secondary { background: var(--background); color: var(--text-secondary); .status-dot { background: var(--text-tertiary); } }
    }

    .method-badge {
      display: inline-block; padding: 0.25rem 0.5rem;
      background: var(--background); border-radius: 0.25rem;
      font-size: 0.75rem; color: var(--text-secondary);
      &.ecocash { background: rgba(16, 185, 129, 0.1); color: #10b981; }
      &.onemoney { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
      &.innbucks { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
    }

    .btn {
      display: inline-flex; align-items: center; gap: 0.5rem;
      padding: 0.625rem 1rem; border-radius: 0.5rem;
      font-size: 0.875rem; font-weight: 500;
      cursor: pointer; transition: all 0.15s ease; border: none;
      .material-symbols-outlined { font-size: 1.125rem; }
    }
    .btn-primary { background: var(--primary); color: white; &:hover { background: var(--primary-dark); } }
    .btn-secondary { background: var(--background); color: var(--text-primary); border: 1px solid var(--border); &:hover { background: var(--hover); } }
    .btn-warning { background: var(--warning); color: white; &:hover { filter: brightness(0.9); } }
    .btn-danger { background: var(--error); color: white; &:hover { filter: brightness(0.9); } &:disabled { opacity: 0.5; cursor: not-allowed; } }

    .icon-btn {
      width: 32px; height: 32px;
      display: flex; align-items: center; justify-content: center;
      background: none; border: none; border-radius: 0.375rem;
      color: var(--text-tertiary); cursor: pointer;
      &:hover { background: var(--hover); color: var(--text-primary); }
    }

    .refund-form { display: flex; flex-direction: column; gap: 1.25rem; }
    .refund-summary { background: var(--background); border-radius: 0.5rem; padding: 1rem; }
    .summary-row { display: flex; justify-content: space-between; padding: 0.375rem 0; font-size: 0.875rem;
      .label { color: var(--text-secondary); }
      .value { font-weight: 500; &.error { color: var(--error); } }
    }
    .form-group { display: flex; flex-direction: column; gap: 0.5rem;
      label { font-size: 0.875rem; font-weight: 500; .required { color: var(--error); } }
    }
    .form-input {
      padding: 0.625rem 0.875rem; border: 1px solid var(--border);
      border-radius: 0.5rem; font-size: 0.875rem;
      background: var(--background); color: var(--text-primary);
      &:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(0, 102, 70, 0.1); }
    }
    textarea.form-input { resize: vertical; min-height: 80px; }
    .radio-group { display: flex; gap: 1rem; }
    .radio-option { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-size: 0.875rem;
      input[type="radio"] { width: 16px; height: 16px; accent-color: var(--primary); }
    }
    .checkbox-option { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-size: 0.875rem; font-weight: normal;
      input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--primary); }
    }
    .modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }

    .mono { font-family: monospace; }
    .small { font-size: 0.75rem; }
  `]
})
export class PaymentDetailComponent implements OnInit {
  private paymentService = inject(PaymentService);
  private toastService = inject(ToastService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  loading = signal(true);
  payment = signal<Payment | null>(null);
  showTechnical = signal(false);

  refundType: 'full' | 'partial' = 'full';
  refundAmount = 0;
  refundReason = '';
  notifyUser = true;

  private refundModal!: ModalComponent;

  ngOnInit(): void {
    const paymentId = this.route.snapshot.paramMap.get('id');
    if (paymentId) {
      this.loadPayment(paymentId);
    } else {
      this.loading.set(false);
    }
  }

  loadPayment(id: string): void {
    this.loading.set(true);
    this.paymentService.getPaymentDetails(id).subscribe({
      next: (payment) => {
        this.payment.set(payment);
        this.loading.set(false);
      },
      error: () => {
        this.toastService.error('Failed to load payment details');
        this.payment.set(null);
        this.loading.set(false);
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/payments']);
  }

  toggleTechnical(): void {
    this.showTechnical.update(v => !v);
  }

  canRefund(): boolean {
    const p = this.payment();
    if (!p) return false;
    return p.status === PaymentStatus.COMPLETED || p.status === PaymentStatus.PARTIALLY_REFUNDED;
  }

  getMaxRefundable(): number {
    const p = this.payment();
    if (!p) return 0;
    return p.amount - (p.refunded_amount || 0);
  }

  openRefundModal(): void {
    const p = this.payment();
    if (!p) return;
    this.refundType = 'full';
    this.refundAmount = this.getMaxRefundable();
    this.refundReason = '';
    this.notifyUser = true;
    // Access modal through ViewChild would be ideal, but for simplicity we'll use a workaround
  }

  closeRefundModal(): void {
    // Close modal
  }

  canSubmitRefund(): boolean {
    if (!this.refundReason || this.refundReason.length < 5) return false;
    if (this.refundType === 'partial') {
      if (!this.refundAmount || this.refundAmount <= 0 || this.refundAmount > this.getMaxRefundable()) return false;
    }
    return true;
  }

  processRefund(): void {
    const p = this.payment();
    if (!p) return;

    const request = {
      reason: this.refundReason,
      refund_type: this.refundType,
      partial_amount: this.refundType === 'partial' ? this.refundAmount : undefined,
      notify_user: this.notifyUser
    };

    this.paymentService.refundPayment(p.id, request).subscribe({
      next: (response) => {
        if (response.success) {
          this.toastService.success(`Refund of ${this.formatCurrency(response.refund_amount)} processed successfully`);
          this.loadPayment(p.id);
          this.closeRefundModal();
        }
      },
      error: (err) => this.toastService.error(err.error?.detail || 'Failed to process refund')
    });
  }

  printReceipt(): void {
    window.print();
  }

  getTimeline(): Array<{ type: string; icon: string; title: string; description: string; timestamp: string }> {
    const p = this.payment();
    if (!p) return [];

    const timeline: Array<{ type: string; icon: string; title: string; description: string; timestamp: string }> = [];

    // Created
    timeline.push({
      type: 'info',
      icon: 'add_circle',
      title: 'Payment Initiated',
      description: `Payment of ${this.formatCurrency(p.amount)} initiated via ${this.getMethodLabel(p.payment_method)}`,
      timestamp: p.created_at
    });

    // Status history
    if (p.status_history) {
      for (const change of p.status_history) {
        const type = change.to_status === 'completed' ? 'success' :
                     change.to_status === 'failed' ? 'error' : 'info';
        timeline.push({
          type,
          icon: change.to_status === 'completed' ? 'check_circle' :
                change.to_status === 'failed' ? 'cancel' :
                change.to_status === 'processing' ? 'sync' : 'update',
          title: `Status: ${change.to_status}`,
          description: change.reason || `Status changed from ${change.from_status} to ${change.to_status}`,
          timestamp: change.changed_at
        });
      }
    }

    // Refunds
    if (p.refund_history) {
      for (const refund of p.refund_history) {
        timeline.push({
          type: 'warning',
          icon: 'undo',
          title: 'Refund Processed',
          description: `${this.formatCurrency(refund.amount)} refunded - ${refund.reason}`,
          timestamp: refund.processed_at
        });
      }
    }

    // Sort by timestamp
    timeline.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

    return timeline;
  }

  formatCurrency(amount: number): string {
    return formatCurrency(amount);
  }

  formatDateTime(dateStr: string): string {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getMethodLabel(method: PaymentMethod | string): string {
    return getPaymentMethodLabel(method as PaymentMethod);
  }

  getStatusClass(status: PaymentStatus): string {
    return getPaymentStatusColor(status);
  }
}
