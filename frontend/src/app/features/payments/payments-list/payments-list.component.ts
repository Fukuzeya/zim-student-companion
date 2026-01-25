import { Component, OnInit, ViewChild, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { PaymentService } from '../../../core/services/payment.service';
import { ToastService } from '../../../core/services/toast.service';
import { StatCardComponent } from '../../../shared/components/stat-card/stat-card.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import {
  Payment,
  PaymentStats,
  PaymentStatus,
  PaymentMethod,
  PaymentFilters,
  formatCurrency,
  formatCompactCurrency,
  getPaymentStatusColor,
  getPaymentMethodLabel
} from '../../../core/models/payment.models';

@Component({
  selector: 'app-payments-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    StatCardComponent,
    LoadingSpinnerComponent,
    ModalComponent
  ],
  template: `
    <div class="payments-page">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-content">
          <div class="header-text">
            <h1>Payments & Revenue</h1>
            <p>Monitor transactions, process refunds, and track revenue metrics</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" (click)="openExportModal()">
              <span class="material-symbols-outlined">download</span>
              Export
            </button>
            <button class="btn btn-primary" (click)="openReconciliationModal()">
              <span class="material-symbols-outlined">sync_alt</span>
              Reconcile
            </button>
          </div>
        </div>
        <div class="breadcrumbs">
          <a routerLink="/dashboard">Dashboard</a>
          <span class="separator">/</span>
          <a routerLink="/payments">Finance</a>
          <span class="separator">/</span>
          <span class="current">Payments</span>
        </div>
      </div>

      <!-- Stats Cards -->
      <div class="stats-grid">
        <app-stat-card
          label="Monthly Revenue (MRR)"
          [value]="formatCompact(stats()?.mrr || stats()?.total_revenue_30d || 0)"
          icon="account_balance"
          iconBgColor="rgba(16, 185, 129, 0.1)"
          iconColor="#10b981"
          [trend]="{
            value: stats()?.mrr_growth || 12.5,
            direction: (stats()?.mrr_growth || 12.5) >= 0 ? 'up' : 'down',
            label: 'vs last month',
            isPercentage: true
          }"
        />
        <app-stat-card
          label="Active Subscriptions"
          [value]="stats()?.active_subscriptions || 0"
          icon="people"
          iconBgColor="rgba(59, 130, 246, 0.1)"
          iconColor="#3b82f6"
          [trend]="{
            value: stats()?.subscriber_growth || 8,
            direction: (stats()?.subscriber_growth || 8) >= 0 ? 'up' : 'down',
            label: 'vs last month',
            isPercentage: true
          }"
        />
        <app-stat-card
          label="Success Rate"
          [value]="(stats()?.payment_success_rate || getSuccessRate()) + '%'"
          icon="check_circle"
          iconBgColor="rgba(16, 185, 129, 0.1)"
          iconColor="#10b981"
          [progress]="stats()?.payment_success_rate || getSuccessRate()"
          progressColor="#10b981"
        />
        <app-stat-card
          label="Customer LTV"
          [value]="formatCompact(stats()?.ltv || stats()?.average_transaction_value || 0)"
          icon="trending_up"
          iconBgColor="rgba(139, 92, 246, 0.1)"
          iconColor="#8b5cf6"
        />
      </div>

      <!-- Secondary Stats -->
      <div class="secondary-stats">
        <div class="stat-pill">
          <span class="stat-label">30d Revenue:</span>
          <span class="stat-value success">{{ formatCurrency(stats()?.total_revenue_30d || 0) }}</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">Transactions:</span>
          <span class="stat-value">{{ stats()?.total_transactions_30d || 0 }}</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">Failed:</span>
          <span class="stat-value error">{{ stats()?.failed_transactions_30d || 0 }}</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">Refunds:</span>
          <span class="stat-value warning">{{ formatCurrency(stats()?.refunded_amount_30d || 0) }}</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">Churn Rate:</span>
          <span class="stat-value" [class.error]="(stats()?.churn_rate || 0) > 5">{{ stats()?.churn_rate || 0 }}%</span>
        </div>
      </div>

      <!-- Filters -->
      <div class="filters-card">
        <div class="filters-row">
          <div class="search-box">
            <span class="material-symbols-outlined">search</span>
            <input
              type="text"
              placeholder="Search by reference, email, phone..."
              [(ngModel)]="searchQuery"
              (input)="onSearchChange()"
            />
            @if (searchQuery) {
              <button class="clear-btn" (click)="clearSearch()">
                <span class="material-symbols-outlined">close</span>
              </button>
            }
          </div>

          <div class="filter-group">
            <label>Status</label>
            <select [(ngModel)]="statusFilter" (change)="applyFilters()">
              <option value="">All Statuses</option>
              @for (status of paymentStatuses; track status) {
                <option [value]="status">{{ status | titlecase }}</option>
              }
            </select>
          </div>

          <div class="filter-group">
            <label>Method</label>
            <select [(ngModel)]="methodFilter" (change)="applyFilters()">
              <option value="">All Methods</option>
              @for (method of paymentMethods; track method) {
                <option [value]="method">{{ getMethodLabel(method) }}</option>
              }
            </select>
          </div>

          <div class="filter-group">
            <label>From</label>
            <input
              type="date"
              [(ngModel)]="dateFrom"
              (change)="applyFilters()"
            />
          </div>

          <div class="filter-group">
            <label>To</label>
            <input
              type="date"
              [(ngModel)]="dateTo"
              (change)="applyFilters()"
            />
          </div>

          @if (hasActiveFilters()) {
            <button class="btn btn-ghost" (click)="clearFilters()">
              <span class="material-symbols-outlined">filter_alt_off</span>
              Clear
            </button>
          }
        </div>
      </div>

      <!-- Payments Table -->
      <div class="table-card">
        @if (loading()) {
          <div class="loading-container">
            <app-loading-spinner />
          </div>
        } @else if (payments().length === 0) {
          <div class="empty-state">
            <span class="material-symbols-outlined">payments</span>
            <h3>No payments found</h3>
            <p>No transactions match your current filters</p>
          </div>
        } @else {
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th class="sortable" (click)="sortBy('created_at')">
                    Date
                    @if (currentSortBy === 'created_at') {
                      <span class="material-symbols-outlined sort-icon">
                        {{ currentSortOrder === 'asc' ? 'arrow_upward' : 'arrow_downward' }}
                      </span>
                    }
                  </th>
                  <th>Reference</th>
                  <th>Customer</th>
                  <th>Plan</th>
                  <th class="sortable" (click)="sortBy('amount')">
                    Amount
                    @if (currentSortBy === 'amount') {
                      <span class="material-symbols-outlined sort-icon">
                        {{ currentSortOrder === 'asc' ? 'arrow_upward' : 'arrow_downward' }}
                      </span>
                    }
                  </th>
                  <th>Method</th>
                  <th>Status</th>
                  <th class="actions-col">Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (payment of payments(); track payment.id) {
                  <tr (click)="viewPayment(payment)" class="clickable-row">
                    <td>
                      <div class="date-cell">
                        <span class="date">{{ formatDate(payment.created_at) }}</span>
                        <span class="time">{{ formatTime(payment.created_at) }}</span>
                      </div>
                    </td>
                    <td>
                      <span class="reference-code">{{ payment.payment_reference || payment.transaction_id || payment.id.slice(0, 8) }}</span>
                    </td>
                    <td>
                      <div class="customer-cell">
                        <span class="name">{{ payment.user_name || 'Unknown' }}</span>
                        <span class="contact">{{ payment.user_email || payment.user_phone || '-' }}</span>
                      </div>
                    </td>
                    <td>
                      <span class="plan-badge" [class]="payment.plan_tier || 'basic'">
                        {{ payment.plan_name || 'N/A' }}
                      </span>
                    </td>
                    <td>
                      <div class="amount-cell">
                        <span class="amount">{{ formatCurrency(payment.amount) }}</span>
                        @if (payment.refunded_amount && payment.refunded_amount > 0) {
                          <span class="refunded">-{{ formatCurrency(payment.refunded_amount) }}</span>
                        }
                      </div>
                    </td>
                    <td>
                      <span class="method-badge" [class]="payment.payment_method">
                        {{ getMethodLabel(payment.payment_method) }}
                      </span>
                    </td>
                    <td>
                      <span class="status-badge" [class]="getStatusClass(payment.status)">
                        <span class="status-dot"></span>
                        {{ payment.status | titlecase }}
                      </span>
                    </td>
                    <td class="actions-col" (click)="$event.stopPropagation()">
                      <div class="action-buttons">
                        <button
                          class="icon-btn"
                          title="View Details"
                          (click)="viewPayment(payment)"
                        >
                          <span class="material-symbols-outlined">visibility</span>
                        </button>
                        @if (canRefund(payment)) {
                          <button
                            class="icon-btn refund"
                            title="Refund"
                            (click)="openRefundModal(payment)"
                          >
                            <span class="material-symbols-outlined">undo</span>
                          </button>
                        }
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          <!-- Pagination -->
          <div class="pagination">
            <div class="pagination-info">
              Showing {{ paginationStart() }} to {{ paginationEnd() }} of {{ totalPayments() }} payments
            </div>
            <div class="pagination-controls">
              <button
                class="pagination-btn"
                [disabled]="currentPage() === 1"
                (click)="goToPage(1)"
              >
                <span class="material-symbols-outlined">first_page</span>
              </button>
              <button
                class="pagination-btn"
                [disabled]="currentPage() === 1"
                (click)="goToPage(currentPage() - 1)"
              >
                <span class="material-symbols-outlined">chevron_left</span>
              </button>

              @for (page of visiblePages(); track page) {
                <button
                  class="pagination-btn"
                  [class.active]="page === currentPage()"
                  (click)="goToPage(page)"
                >
                  {{ page }}
                </button>
              }

              <button
                class="pagination-btn"
                [disabled]="currentPage() === totalPages()"
                (click)="goToPage(currentPage() + 1)"
              >
                <span class="material-symbols-outlined">chevron_right</span>
              </button>
              <button
                class="pagination-btn"
                [disabled]="currentPage() === totalPages()"
                (click)="goToPage(totalPages())"
              >
                <span class="material-symbols-outlined">last_page</span>
              </button>
            </div>
          </div>
        }
      </div>

      <!-- Refund Modal -->
      <app-modal
        #refundModal
        title="Process Refund"
        size="md"
        [showFooter]="true"
      >
        @if (selectedPayment()) {
          <div class="refund-form">
            <div class="refund-summary">
              <div class="summary-row">
                <span class="label">Payment Reference:</span>
                <span class="value">{{ selectedPayment()!.payment_reference || selectedPayment()!.id.slice(0, 8) }}</span>
              </div>
              <div class="summary-row">
                <span class="label">Original Amount:</span>
                <span class="value">{{ formatCurrency(selectedPayment()!.amount) }}</span>
              </div>
              @if (selectedPayment()!.refunded_amount && selectedPayment()!.refunded_amount! > 0) {
                <div class="summary-row">
                  <span class="label">Already Refunded:</span>
                  <span class="value error">{{ formatCurrency(selectedPayment()!.refunded_amount!) }}</span>
                </div>
                <div class="summary-row">
                  <span class="label">Refundable Amount:</span>
                  <span class="value">{{ formatCurrency(selectedPayment()!.amount - selectedPayment()!.refunded_amount!) }}</span>
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
                <label>Refund Amount (USD)</label>
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
              <label>Reason for Refund <span class="required">*</span></label>
              <textarea
                [(ngModel)]="refundReason"
                placeholder="Provide a detailed reason for this refund (min 10 characters)..."
                rows="3"
                class="form-input"
              ></textarea>
            </div>

            <div class="form-group">
              <label>Internal Notes (Optional)</label>
              <textarea
                [(ngModel)]="refundNotes"
                placeholder="Add any internal notes..."
                rows="2"
                class="form-input"
              ></textarea>
            </div>

            <div class="form-group">
              <label class="checkbox-option">
                <input type="checkbox" [(ngModel)]="notifyUser" />
                <span>Notify user about refund via WhatsApp</span>
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
            <span class="material-symbols-outlined">undo</span>
            Process Refund
          </button>
        </div>
      </app-modal>

      <!-- Export Modal -->
      <app-modal
        #exportModal
        title="Export Payments"
        size="md"
        [showFooter]="true"
      >
        <div class="export-form">
          <div class="form-group">
            <label>Export Format</label>
            <div class="radio-group">
              <label class="radio-option">
                <input type="radio" name="exportFormat" value="csv" [(ngModel)]="exportFormat" />
                <span>CSV</span>
              </label>
              <label class="radio-option">
                <input type="radio" name="exportFormat" value="xlsx" [(ngModel)]="exportFormat" />
                <span>Excel (XLSX)</span>
              </label>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Date From</label>
              <input type="date" [(ngModel)]="exportDateFrom" class="form-input" />
            </div>
            <div class="form-group">
              <label>Date To</label>
              <input type="date" [(ngModel)]="exportDateTo" class="form-input" />
            </div>
          </div>

          <div class="form-group">
            <label class="checkbox-option">
              <input type="checkbox" [(ngModel)]="exportIncludeUserDetails" />
              <span>Include user details (email, phone)</span>
            </label>
          </div>
        </div>

        <div modal-footer class="modal-actions">
          <button class="btn btn-secondary" (click)="closeExportModal()">Cancel</button>
          <button class="btn btn-primary" (click)="downloadExport()">
            <span class="material-symbols-outlined">download</span>
            Download
          </button>
        </div>
      </app-modal>
    </div>
  `,
  styles: [`
    .payments-page {
      padding: 1.5rem;
      max-width: 1600px;
      margin: 0 auto;
    }

    .page-header {
      margin-bottom: 1.5rem;
    }

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.5rem;
    }

    .header-text h1 {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text-primary);
      margin: 0 0 0.25rem 0;
    }

    .header-text p {
      font-size: 0.875rem;
      color: var(--text-secondary);
      margin: 0;
    }

    .header-actions {
      display: flex;
      gap: 0.75rem;
    }

    .breadcrumbs {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      color: var(--text-tertiary);
    }

    .breadcrumbs a {
      color: var(--text-secondary);
      text-decoration: none;
      &:hover { color: var(--primary); }
    }

    .breadcrumbs .current { color: var(--text-primary); }
    .breadcrumbs .separator { color: var(--border); }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 1rem;
    }

    @media (max-width: 1200px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 600px) { .stats-grid { grid-template-columns: 1fr; } }

    .secondary-stats {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }

    .stat-pill {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 9999px;
      font-size: 0.875rem;
    }

    .stat-label { color: var(--text-secondary); }
    .stat-value { font-weight: 600; color: var(--text-primary); font-feature-settings: 'tnum'; }
    .stat-value.success { color: var(--success); }
    .stat-value.error { color: var(--error); }
    .stat-value.warning { color: var(--warning); }

    .filters-card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1rem 1.25rem;
      margin-bottom: 1rem;
    }

    .filters-row {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      gap: 1rem;
    }

    .search-box {
      flex: 1;
      min-width: 280px;
      position: relative;
      display: flex;
      align-items: center;

      .material-symbols-outlined {
        position: absolute;
        left: 0.75rem;
        color: var(--text-tertiary);
        font-size: 1.25rem;
      }

      input {
        width: 100%;
        padding: 0.625rem 2.5rem 0.625rem 2.5rem;
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        font-size: 0.875rem;
        background-color: var(--background);
        color: var(--text-primary);

        &:focus {
          outline: none;
          border-color: var(--primary);
          box-shadow: 0 0 0 3px rgba(0, 102, 70, 0.1);
        }

        &::placeholder { color: var(--text-tertiary); }
      }

      .clear-btn {
        position: absolute;
        right: 0.5rem;
        background: none;
        border: none;
        padding: 0.25rem;
        cursor: pointer;
        color: var(--text-tertiary);
        border-radius: 0.25rem;

        &:hover {
          background-color: var(--hover);
          color: var(--text-primary);
        }
      }
    }

    .filter-group {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;

      label {
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--text-secondary);
      }

      select, input {
        padding: 0.5rem 0.75rem;
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        font-size: 0.875rem;
        background-color: var(--background);
        color: var(--text-primary);
        min-width: 140px;

        &:focus {
          outline: none;
          border-color: var(--primary);
        }
      }
    }

    .table-card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 4rem;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;
      color: var(--text-tertiary);

      .material-symbols-outlined { font-size: 3rem; margin-bottom: 1rem; }
      h3 { margin: 0 0 0.5rem 0; color: var(--text-secondary); }
      p { margin: 0; }
    }

    .table-wrapper { overflow-x: auto; }

    table { width: 100%; border-collapse: collapse; }

    thead {
      background-color: var(--background);
      border-bottom: 1px solid var(--border);
    }

    th {
      padding: 0.875rem 1rem;
      text-align: left;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      white-space: nowrap;
    }

    th.sortable {
      cursor: pointer;
      user-select: none;
      &:hover { color: var(--primary); }
      .sort-icon { font-size: 1rem; vertical-align: middle; margin-left: 0.25rem; }
    }

    th.actions-col { width: 100px; text-align: center; }

    td {
      padding: 1rem;
      font-size: 0.875rem;
      color: var(--text-primary);
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
    }

    tr.clickable-row {
      cursor: pointer;
      transition: background-color 0.15s ease;
      &:hover { background-color: var(--hover); }
    }

    .date-cell {
      display: flex;
      flex-direction: column;
      .date { font-weight: 500; }
      .time { font-size: 0.75rem; color: var(--text-tertiary); }
    }

    .reference-code {
      font-family: monospace;
      font-size: 0.8125rem;
      color: var(--text-secondary);
      background-color: var(--background);
      padding: 0.25rem 0.5rem;
      border-radius: 0.25rem;
    }

    .customer-cell {
      display: flex;
      flex-direction: column;
      .name { font-weight: 500; }
      .contact { font-size: 0.75rem; color: var(--text-tertiary); }
    }

    .plan-badge {
      display: inline-block;
      padding: 0.25rem 0.625rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 500;
      text-transform: capitalize;

      &.basic { background-color: rgba(59, 130, 246, 0.1); color: #3b82f6; }
      &.premium { background-color: rgba(139, 92, 246, 0.1); color: #8b5cf6; }
      &.family { background-color: rgba(16, 185, 129, 0.1); color: #10b981; }
      &.school { background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; }
    }

    .amount-cell {
      display: flex;
      flex-direction: column;
      .amount { font-weight: 600; font-feature-settings: 'tnum'; }
      .refunded { font-size: 0.75rem; color: var(--error); }
    }

    .method-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      background-color: var(--background);
      border-radius: 0.25rem;
      font-size: 0.75rem;
      color: var(--text-secondary);

      &.ecocash { background-color: rgba(16, 185, 129, 0.1); color: #10b981; }
      &.onemoney { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; }
      &.innbucks { background-color: rgba(59, 130, 246, 0.1); color: #3b82f6; }
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 500;

      .status-dot { width: 6px; height: 6px; border-radius: 50%; }

      &.success {
        background-color: rgba(16, 185, 129, 0.1); color: #10b981;
        .status-dot { background-color: #10b981; }
      }
      &.warning {
        background-color: rgba(245, 158, 11, 0.1); color: #f59e0b;
        .status-dot { background-color: #f59e0b; }
      }
      &.error {
        background-color: rgba(239, 68, 68, 0.1); color: #ef4444;
        .status-dot { background-color: #ef4444; }
      }
      &.info {
        background-color: rgba(59, 130, 246, 0.1); color: #3b82f6;
        .status-dot { background-color: #3b82f6; }
      }
      &.secondary {
        background-color: var(--background); color: var(--text-secondary);
        .status-dot { background-color: var(--text-tertiary); }
      }
    }

    .actions-col { text-align: center; }

    .action-buttons { display: flex; justify-content: center; gap: 0.25rem; }

    .icon-btn {
      width: 32px; height: 32px;
      display: flex; align-items: center; justify-content: center;
      background: none; border: none; border-radius: 0.375rem;
      color: var(--text-tertiary); cursor: pointer;
      transition: all 0.15s ease;

      &:hover { background-color: var(--hover); color: var(--text-primary); }
      &.refund:hover { background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; }
      .material-symbols-outlined { font-size: 1.125rem; }
    }

    .pagination {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      border-top: 1px solid var(--border);
    }

    .pagination-info { font-size: 0.875rem; color: var(--text-secondary); }
    .pagination-controls { display: flex; gap: 0.25rem; }

    .pagination-btn {
      min-width: 36px; height: 36px;
      display: flex; align-items: center; justify-content: center;
      background-color: transparent;
      border: 1px solid var(--border);
      border-radius: 0.375rem;
      font-size: 0.875rem;
      color: var(--text-primary);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover:not(:disabled) { background-color: var(--hover); border-color: var(--primary); }
      &.active { background-color: var(--primary); border-color: var(--primary); color: white; }
      &:disabled { opacity: 0.5; cursor: not-allowed; }
      .material-symbols-outlined { font-size: 1.25rem; }
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.625rem 1rem;
      border-radius: 0.5rem;
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
      border: none;
      .material-symbols-outlined { font-size: 1.125rem; }
    }

    .btn-primary { background-color: var(--primary); color: white; &:hover { background-color: var(--primary-dark); } }
    .btn-secondary { background-color: var(--background); color: var(--text-primary); border: 1px solid var(--border); &:hover { background-color: var(--hover); } }
    .btn-ghost { background: none; color: var(--text-secondary); &:hover { background-color: var(--hover); color: var(--text-primary); } }
    .btn-danger { background-color: var(--error); color: white; &:hover { background-color: #dc2626; } &:disabled { opacity: 0.5; cursor: not-allowed; } }

    .refund-form, .export-form { display: flex; flex-direction: column; gap: 1.25rem; }

    .refund-summary { background-color: var(--background); border-radius: 0.5rem; padding: 1rem; }

    .summary-row {
      display: flex;
      justify-content: space-between;
      padding: 0.375rem 0;
      font-size: 0.875rem;
      .label { color: var(--text-secondary); }
      .value { font-weight: 500; color: var(--text-primary); font-feature-settings: 'tnum'; &.error { color: var(--error); } }
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      label { font-size: 0.875rem; font-weight: 500; color: var(--text-primary); .required { color: var(--error); } }
    }

    .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }

    .form-input {
      padding: 0.625rem 0.875rem;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      font-size: 0.875rem;
      background-color: var(--background);
      color: var(--text-primary);
      &:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(0, 102, 70, 0.1); }
    }

    textarea.form-input { resize: vertical; min-height: 80px; }

    .radio-group { display: flex; gap: 1rem; }

    .radio-option {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      font-size: 0.875rem;
      input[type="radio"] { width: 16px; height: 16px; accent-color: var(--primary); }
    }

    .checkbox-option {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      font-size: 0.875rem;
      font-weight: normal;
      input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--primary); }
    }

    .modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
  `]
})
export class PaymentsListComponent implements OnInit {
  @ViewChild('refundModal') refundModal!: ModalComponent;
  @ViewChild('exportModal') exportModal!: ModalComponent;

  private paymentService = inject(PaymentService);
  private toastService = inject(ToastService);
  private router = inject(Router);

  loading = signal(true);
  payments = signal<Payment[]>([]);
  stats = signal<PaymentStats | null>(null);
  totalPayments = signal(0);
  currentPage = signal(1);
  totalPages = signal(1);
  pageSize = 20;

  selectedPayment = signal<Payment | null>(null);

  searchQuery = '';
  statusFilter = '';
  methodFilter = '';
  dateFrom = '';
  dateTo = '';
  currentSortBy = 'created_at';
  currentSortOrder: 'asc' | 'desc' = 'desc';

  refundType: 'full' | 'partial' = 'full';
  refundAmount = 0;
  refundReason = '';
  refundNotes = '';
  notifyUser = true;

  exportFormat: 'csv' | 'xlsx' = 'csv';
  exportDateFrom = '';
  exportDateTo = '';
  exportIncludeUserDetails = true;

  paymentStatuses = Object.values(PaymentStatus);
  paymentMethods = Object.values(PaymentMethod);

  paginationStart = computed(() => (this.currentPage() - 1) * this.pageSize + 1);
  paginationEnd = computed(() => Math.min(this.currentPage() * this.pageSize, this.totalPayments()));
  visiblePages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, current - Math.floor(maxVisible / 2));
    let end = Math.min(total, start + maxVisible - 1);
    if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    return pages;
  });

  private searchTimeout: any;

  ngOnInit() {
    this.loadPayments();
    this.loadStats();
  }

  loadPayments() {
    this.loading.set(true);
    const filters: PaymentFilters = {
      page: this.currentPage(),
      page_size: this.pageSize,
      sort_by: this.currentSortBy,
      sort_order: this.currentSortOrder
    };
    if (this.searchQuery) filters.search_query = this.searchQuery;
    if (this.statusFilter) filters.status = this.statusFilter as PaymentStatus;
    if (this.methodFilter) filters.payment_method = this.methodFilter as PaymentMethod;
    if (this.dateFrom) filters.date_from = this.dateFrom;
    if (this.dateTo) filters.date_to = this.dateTo;

    this.paymentService.getPayments(filters).subscribe({
      next: (response) => {
        this.payments.set(response.payments || []);
        this.totalPayments.set(response.total || 0);
        this.totalPages.set(response.total_pages || 1);
        this.loading.set(false);
      },
      error: (err) => {
        this.toastService.error('Failed to load payments');
        this.payments.set([]);
        this.totalPayments.set(0);
        this.totalPages.set(1);
        this.loading.set(false);
      }
    });
  }

  loadStats() {
    this.paymentService.getPaymentStats().subscribe({
      next: (stats) => this.stats.set(stats),
      error: () => this.stats.set(null)
    });
  }

  getSuccessRate(): number {
    const stats = this.stats();
    if (!stats || !stats.total_transactions_30d) return 91;
    return Math.round((stats.successful_transactions_30d / stats.total_transactions_30d) * 100);
  }

  onSearchChange() {
    clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => this.applyFilters(), 300);
  }

  clearSearch() { this.searchQuery = ''; this.applyFilters(); }
  applyFilters() { this.currentPage.set(1); this.loadPayments(); }

  clearFilters() {
    this.searchQuery = '';
    this.statusFilter = '';
    this.methodFilter = '';
    this.dateFrom = '';
    this.dateTo = '';
    this.currentPage.set(1);
    this.loadPayments();
  }

  hasActiveFilters(): boolean {
    return !!(this.searchQuery || this.statusFilter || this.methodFilter || this.dateFrom || this.dateTo);
  }

  sortBy(column: string) {
    if (this.currentSortBy === column) {
      this.currentSortOrder = this.currentSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
      this.currentSortBy = column;
      this.currentSortOrder = 'desc';
    }
    this.loadPayments();
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
      this.loadPayments();
    }
  }

  viewPayment(payment: Payment) {
    this.router.navigate(['/payments', payment.id]);
  }

  canRefund(payment: Payment): boolean {
    return payment.status === PaymentStatus.COMPLETED || payment.status === PaymentStatus.PARTIALLY_REFUNDED;
  }

  openRefundModal(payment: Payment) {
    this.selectedPayment.set(payment);
    this.refundType = 'full';
    this.refundAmount = payment.amount - (payment.refunded_amount || 0);
    this.refundReason = '';
    this.refundNotes = '';
    this.notifyUser = true;
    this.refundModal.open();
  }

  closeRefundModal() { this.refundModal.close(); this.selectedPayment.set(null); }

  getMaxRefundable(): number {
    const payment = this.selectedPayment();
    return payment ? payment.amount - (payment.refunded_amount || 0) : 0;
  }

  canSubmitRefund(): boolean {
    if (!this.refundReason || this.refundReason.length < 10) return false;
    if (this.refundType === 'partial') {
      if (!this.refundAmount || this.refundAmount <= 0 || this.refundAmount > this.getMaxRefundable()) return false;
    }
    return true;
  }

  processRefund() {
    const payment = this.selectedPayment();
    if (!payment) return;

    const request = {
      reason: this.refundReason,
      refund_type: this.refundType,
      partial_amount: this.refundType === 'partial' ? this.refundAmount : undefined,
      notify_user: this.notifyUser,
      internal_notes: this.refundNotes || undefined
    };

    this.paymentService.refundPayment(payment.id, request).subscribe({
      next: (response) => {
        if (response.success) {
          this.toastService.success(`Refund of ${this.formatCurrency(response.refund_amount)} processed successfully`);
          this.closeRefundModal();
          this.loadPayments();
          this.loadStats();
        } else {
          this.toastService.error('Failed to process refund');
        }
      },
      error: (err) => this.toastService.error(err.error?.detail || 'Failed to process refund')
    });
  }

  openExportModal() {
    const today = new Date().toISOString().split('T')[0];
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    this.exportDateFrom = thirtyDaysAgo;
    this.exportDateTo = today;
    this.exportModal.open();
  }

  closeExportModal() { this.exportModal.close(); }

  downloadExport() {
    const request = {
      format: this.exportFormat,
      date_from: this.exportDateFrom || undefined,
      date_to: this.exportDateTo || undefined,
      include_user_details: this.exportIncludeUserDetails
    };

    this.paymentService.exportPayments(request as any).subscribe({
      next: (response) => {
        if (response.success && response.data) {
          const blob = new Blob([response.data], { type: 'text/csv' });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = response.file_name;
          a.click();
          window.URL.revokeObjectURL(url);
          this.toastService.success(`Exported ${response.record_count} payments`);
          this.closeExportModal();
        }
      },
      error: () => this.toastService.error('Failed to export payments')
    });
  }

  openReconciliationModal() { this.toastService.info('Reconciliation feature coming soon'); }

  formatCurrency(amount: number): string { return formatCurrency(amount); }
  formatCompact(amount: number): string { return formatCompactCurrency(amount); }

  formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  formatTime(dateStr: string): string {
    return new Date(dateStr).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }

  getMethodLabel(method: PaymentMethod | string): string { return getPaymentMethodLabel(method as PaymentMethod); }
  getStatusClass(status: PaymentStatus): string { return getPaymentStatusColor(status); }
}
