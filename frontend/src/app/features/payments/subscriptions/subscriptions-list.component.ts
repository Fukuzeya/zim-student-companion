import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ToastService } from '../../../core/services/toast.service';
import { PaymentService } from '../../../core/services/payment.service';

interface Subscription {
  id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  plan_name: string;
  plan_price: number;
  status: 'active' | 'cancelled' | 'expired' | 'pending';
  start_date: string;
  end_date: string;
  auto_renew: boolean;
  payment_method: string;
}

@Component({
  selector: 'app-subscriptions-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>Subscriptions</h1>
          <p class="subtitle">Manage user subscription plans</p>
        </div>
        <div class="header-actions">
          <button class="btn-secondary">
            <span class="material-symbols-outlined">download</span>
            Export
          </button>
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon green">
            <span class="material-symbols-outlined">check_circle</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ getActiveCount() }}</span>
            <span class="stat-label">Active</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon orange">
            <span class="material-symbols-outlined">schedule</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ getExpiringCount() }}</span>
            <span class="stat-label">Expiring Soon</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon red">
            <span class="material-symbols-outlined">cancel</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ getCancelledCount() }}</span>
            <span class="stat-label">Cancelled</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon blue">
            <span class="material-symbols-outlined">attach_money</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">\${{ getMRR() }}</span>
            <span class="stat-label">Monthly Revenue</span>
          </div>
        </div>
      </div>

      <div class="filters-bar">
        <div class="search-box">
          <span class="material-symbols-outlined">search</span>
          <input type="text" placeholder="Search by user or plan..." [(ngModel)]="searchQuery" (input)="applyFilters()" />
        </div>
        <div class="filter-group">
          <select [(ngModel)]="statusFilter" (change)="applyFilters()">
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="pending">Pending</option>
            <option value="cancelled">Cancelled</option>
            <option value="expired">Expired</option>
          </select>
          <select [(ngModel)]="planFilter" (change)="applyFilters()">
            <option value="">All Plans</option>
            <option value="Basic">Basic</option>
            <option value="Premium">Premium</option>
            <option value="Enterprise">Enterprise</option>
          </select>
        </div>
      </div>

      @if (isLoading()) {
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Loading subscriptions...</p>
        </div>
      } @else {
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Plan</th>
                <th>Status</th>
                <th>Started</th>
                <th>Expires</th>
                <th>Auto-Renew</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (sub of filteredSubscriptions(); track sub.id) {
                <tr>
                  <td>
                    <div class="user-info">
                      <div class="avatar">{{ getInitials(sub.user_name) }}</div>
                      <div>
                        <span class="name">{{ sub.user_name }}</span>
                        <span class="email">{{ sub.user_email }}</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div class="plan-info">
                      <span class="plan-name">{{ sub.plan_name }}</span>
                      <span class="plan-price">\${{ sub.plan_price }}/mo</span>
                    </div>
                  </td>
                  <td>
                    <span class="status-badge" [class]="sub.status">{{ sub.status }}</span>
                  </td>
                  <td>{{ sub.start_date | date:'mediumDate' }}</td>
                  <td>{{ sub.end_date | date:'mediumDate' }}</td>
                  <td>
                    <span class="auto-renew" [class.active]="sub.auto_renew">
                      <span class="material-symbols-outlined">{{ sub.auto_renew ? 'check_circle' : 'cancel' }}</span>
                    </span>
                  </td>
                  <td>
                    <div class="table-actions">
                      <button class="action-btn" title="View Details" (click)="viewDetails(sub)">
                        <span class="material-symbols-outlined">visibility</span>
                      </button>
                      @if (sub.status === 'active') {
                        <button class="action-btn danger" title="Cancel" (click)="cancelSubscription(sub)">
                          <span class="material-symbols-outlined">cancel</span>
                        </button>
                      } @else if (sub.status === 'cancelled' || sub.status === 'expired') {
                        <button class="action-btn success" title="Reactivate" (click)="reactivate(sub)">
                          <span class="material-symbols-outlined">refresh</span>
                        </button>
                      }
                    </div>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="7">
                    <div class="empty-state">
                      <span class="material-symbols-outlined">credit_card_off</span>
                      <p>No subscriptions found</p>
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
  styles: [`
    .page-container { padding: 1.5rem; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .header-info h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
    .header-info .subtitle { font-size: 0.875rem; color: var(--text-secondary); }

    .btn-secondary {
      display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem;
      font-size: 0.875rem; font-weight: 500; background-color: var(--surface);
      color: var(--text-primary); border: 1px solid var(--border); border-radius: 0.5rem;
      cursor: pointer; &:hover { background-color: var(--hover); }
    }

    .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
    @media (max-width: 1024px) { .stats-row { grid-template-columns: repeat(2, 1fr); } }

    .stat-card {
      display: flex; align-items: center; gap: 1rem; padding: 1rem 1.25rem;
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem;
    }

    .stat-icon {
      width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 0.75rem;
      &.green { background-color: rgba(16, 185, 129, 0.1); .material-symbols-outlined { color: #10b981; } }
      &.orange { background-color: rgba(245, 158, 11, 0.1); .material-symbols-outlined { color: #f59e0b; } }
      &.red { background-color: rgba(239, 68, 68, 0.1); .material-symbols-outlined { color: #ef4444; } }
      &.blue { background-color: rgba(59, 130, 246, 0.1); .material-symbols-outlined { color: #3b82f6; } }
    }

    .stat-info { display: flex; flex-direction: column; }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
    .stat-label { font-size: 0.75rem; color: var(--text-secondary); }

    .filters-bar { display: flex; justify-content: space-between; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }

    .search-box {
      display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem;
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem;
      flex: 1; max-width: 400px;
      .material-symbols-outlined { color: var(--text-tertiary); }
      input { flex: 1; background: transparent; border: none; outline: none; color: var(--text-primary); font-size: 0.875rem; &::placeholder { color: var(--text-tertiary); } }
    }

    .filter-group { display: flex; gap: 0.75rem; }
    .filter-group select {
      padding: 0.5rem 1rem; background-color: var(--surface); border: 1px solid var(--border);
      border-radius: 0.5rem; color: var(--text-primary); font-size: 0.875rem; cursor: pointer;
      &:focus { outline: none; border-color: var(--primary); }
    }

    .loading-state { display: flex; flex-direction: column; align-items: center; padding: 4rem; }
    .spinner { width: 2.5rem; height: 2.5rem; border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 1rem; }

    .table-container {
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; overflow: hidden;
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 0.875rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }
      th { font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); background-color: var(--background); text-transform: uppercase; }
      td { font-size: 0.875rem; color: var(--text-primary); }
      tr:last-child td { border-bottom: none; }
      tr:hover td { background-color: var(--hover); }
    }

    .user-info { display: flex; align-items: center; gap: 0.75rem; }
    .avatar { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background-color: var(--primary); color: white; font-size: 0.75rem; font-weight: 600; border-radius: 50%; }
    .user-info .name { display: block; font-weight: 500; }
    .user-info .email { display: block; font-size: 0.75rem; color: var(--text-secondary); }

    .plan-info .plan-name { display: block; font-weight: 500; }
    .plan-info .plan-price { font-size: 0.75rem; color: var(--text-secondary); }

    .status-badge {
      display: inline-flex; padding: 0.25rem 0.75rem; font-size: 0.75rem; font-weight: 500; border-radius: 9999px; text-transform: capitalize;
      &.active { background-color: rgba(16, 185, 129, 0.1); color: #10b981; }
      &.pending { background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; }
      &.cancelled { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; }
      &.expired { background-color: var(--background); color: var(--text-tertiary); }
    }

    .auto-renew { .material-symbols-outlined { font-size: 1.25rem; color: var(--text-tertiary); } &.active .material-symbols-outlined { color: #10b981; } }

    .table-actions { display: flex; gap: 0.25rem; }
    .action-btn {
      width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
      background: transparent; border: none; border-radius: 0.375rem; color: var(--text-tertiary); cursor: pointer;
      &:hover { background-color: var(--hover); color: var(--text-primary); }
      &.danger:hover { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; }
      &.success:hover { background-color: rgba(16, 185, 129, 0.1); color: #10b981; }
      .material-symbols-outlined { font-size: 1.125rem; }
    }

    .empty-state { display: flex; flex-direction: column; align-items: center; padding: 3rem; .material-symbols-outlined { font-size: 3rem; color: var(--text-tertiary); margin-bottom: 0.5rem; } p { color: var(--text-secondary); } }

    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class SubscriptionsListComponent implements OnInit {
  private toastService = inject(ToastService);
  private paymentService = inject(PaymentService);

  subscriptions = signal<Subscription[]>([]);
  filteredSubscriptions = signal<Subscription[]>([]);
  isLoading = signal(true);

  searchQuery = '';
  statusFilter = '';
  planFilter = '';

  ngOnInit(): void { this.loadSubscriptions(); }

  loadSubscriptions(): void {
    this.isLoading.set(true);
    const filters: any = {};
    if (this.statusFilter) filters.status = this.statusFilter;
    if (this.planFilter) filters.tier = this.planFilter;

    this.paymentService.getSubscriptions(filters).subscribe({
      next: (response) => {
        if (response && response.subscriptions && Array.isArray(response.subscriptions)) {
          const subs = response.subscriptions.map((s: any) => ({
            id: s.id,
            user_id: s.user_id,
            user_name: s.user_name || 'Unknown',
            user_email: s.user_email || '',
            plan_name: s.plan_name || s.tier || 'Basic',
            plan_price: s.plan_price || 9.99,
            status: s.status as 'active' | 'cancelled' | 'expired' | 'pending',
            start_date: s.start_date || s.created_at,
            end_date: s.end_date || '',
            auto_renew: s.auto_renew ?? true,
            payment_method: s.payment_method || 'card'
          }));
          this.subscriptions.set(subs);
          this.applyFilters();
        } else {
          this.subscriptions.set([]);
          this.filteredSubscriptions.set([]);
        }
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load subscriptions:', err);
        const mock: Subscription[] = [
          { id: '1', user_id: 'u1', user_name: 'John Doe', user_email: 'john@example.com', plan_name: 'Premium', plan_price: 9.99, status: 'active', start_date: '2024-01-01', end_date: '2024-12-31', auto_renew: true, payment_method: 'card' },
          { id: '2', user_id: 'u2', user_name: 'Jane Smith', user_email: 'jane@example.com', plan_name: 'Basic', plan_price: 4.99, status: 'active', start_date: '2024-02-15', end_date: '2024-08-15', auto_renew: true, payment_method: 'mobile' },
          { id: '3', user_id: 'u3', user_name: 'Bob Wilson', user_email: 'bob@example.com', plan_name: 'Premium', plan_price: 9.99, status: 'cancelled', start_date: '2024-01-10', end_date: '2024-04-10', auto_renew: false, payment_method: 'card' }
        ];
        this.subscriptions.set(mock);
        this.filteredSubscriptions.set(mock);
        this.isLoading.set(false);
      }
    });
  }

  applyFilters(): void {
    let result = this.subscriptions();
    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      result = result.filter(s => s.user_name.toLowerCase().includes(q) || s.user_email.toLowerCase().includes(q) || s.plan_name.toLowerCase().includes(q));
    }
    if (this.statusFilter) result = result.filter(s => s.status === this.statusFilter);
    if (this.planFilter) result = result.filter(s => s.plan_name === this.planFilter);
    this.filteredSubscriptions.set(result);
  }

  getInitials(name: string): string { return name.split(' ').map(n => n[0]).join('').toUpperCase(); }
  getActiveCount(): number { return this.subscriptions().filter(s => s.status === 'active').length; }
  getExpiringCount(): number { return this.subscriptions().filter(s => s.status === 'active').length; }
  getCancelledCount(): number { return this.subscriptions().filter(s => s.status === 'cancelled').length; }
  getMRR(): string { return this.subscriptions().filter(s => s.status === 'active').reduce((sum, s) => sum + s.plan_price, 0).toFixed(2); }

  viewDetails(sub: Subscription): void { this.toastService.info(`View subscription: ${sub.user_name}`); }
  cancelSubscription(sub: Subscription): void { this.toastService.warning(`Cancel subscription for: ${sub.user_name}`); }
  reactivate(sub: Subscription): void { this.toastService.info(`Reactivate subscription for: ${sub.user_name}`); }
}
