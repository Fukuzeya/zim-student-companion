import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ToastService } from '../../../core/services/toast.service';
import { AdminService, AuditLogFilters } from '../../../core/services/admin.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';

interface AuditEntry {
  id: string;
  action: string;
  category: string;
  user: string;
  user_email: string;
  ip_address: string;
  details: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error';
}

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [CommonModule, FormsModule, PageHeaderComponent, LoadingSpinnerComponent],
  template: `
    <div class="page-container">
      <app-page-header
        title="Audit Log"
        description="Track system activities and security events"
        [breadcrumbs]="[
          { label: 'Home', link: '/dashboard' },
          { label: 'System', link: '/system' },
          { label: 'Audit Log' }
        ]"
      >
        <div headerActions>
          <button class="btn btn-secondary" (click)="refreshLogs()">
            <span class="material-symbols-outlined">refresh</span>
            Refresh
          </button>
          <button class="btn btn-primary" (click)="exportLogs()">
            <span class="material-symbols-outlined">download</span>
            Export CSV
          </button>
        </div>
      </app-page-header>

      <div class="filters-bar">
        <div class="search-box">
          <span class="material-symbols-outlined">search</span>
          <input type="text" placeholder="Search logs..." [(ngModel)]="searchQuery" (input)="applyFilters()" />
          @if (searchQuery) {
            <button class="clear-search" (click)="clearSearch()">
              <span class="material-symbols-outlined">close</span>
            </button>
          }
        </div>
        <div class="filter-group">
          <select [(ngModel)]="actionFilter" (change)="loadEntries()">
            <option value="">All Actions</option>
            <option value="create">Create</option>
            <option value="update">Update</option>
            <option value="delete">Delete</option>
            <option value="login">Login</option>
            <option value="logout">Logout</option>
            <option value="export">Export</option>
            <option value="settings_change">Settings Change</option>
          </select>
          <select [(ngModel)]="resourceFilter" (change)="loadEntries()">
            <option value="">All Resources</option>
            <option value="admin_user">Admin Users</option>
            <option value="user">Users</option>
            <option value="student">Students</option>
            <option value="system_settings">System Settings</option>
            <option value="feature_flag">Feature Flags</option>
          </select>
          <input type="date" [(ngModel)]="dateFilter" (change)="loadEntries()" class="date-input" />
          @if (hasActiveFilters()) {
            <button class="btn-clear-filters" (click)="clearFilters()">
              <span class="material-symbols-outlined">filter_alt_off</span>
              Clear
            </button>
          }
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-card">
          <span class="stat-value">{{ entries().length }}</span>
          <span class="stat-label">Total Events</span>
        </div>
        <div class="stat-card success">
          <span class="stat-value">{{ getSuccessCount() }}</span>
          <span class="stat-label">Successful</span>
        </div>
        <div class="stat-card warning">
          <span class="stat-value">{{ getWarningCount() }}</span>
          <span class="stat-label">Warnings</span>
        </div>
        <div class="stat-card error">
          <span class="stat-value">{{ getErrorCount() }}</span>
          <span class="stat-label">Errors</span>
        </div>
      </div>

      @if (isLoading()) {
        <div class="loading-state">
          <app-loading-spinner message="Loading audit logs..." />
        </div>
      } @else {
        <div class="log-table">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Category</th>
                <th>User</th>
                <th>IP Address</th>
                <th>Status</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              @for (entry of filteredEntries(); track entry.id) {
                <tr>
                  <td class="timestamp">{{ entry.timestamp | date:'short' }}</td>
                  <td class="action">{{ entry.action }}</td>
                  <td>
                    <span class="category-badge" [class]="entry.category">{{ entry.category }}</span>
                  </td>
                  <td>
                    <div class="user-cell">
                      <span class="user-name">{{ entry.user }}</span>
                      <span class="user-email">{{ entry.user_email }}</span>
                    </div>
                  </td>
                  <td class="ip">{{ entry.ip_address }}</td>
                  <td>
                    <span class="status-badge" [class]="entry.status">
                      <span class="material-symbols-outlined">
                        {{ entry.status === 'success' ? 'check_circle' : entry.status === 'warning' ? 'warning' : 'error' }}
                      </span>
                      {{ entry.status }}
                    </span>
                  </td>
                  <td class="details">{{ entry.details }}</td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="7">
                    <div class="empty-state">
                      <span class="material-symbols-outlined">history</span>
                      <p>No audit logs found</p>
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <div class="pagination">
          <div class="page-size-select">
            <span>Rows per page:</span>
            <select [(ngModel)]="pageSize" (change)="onPageSizeChange()">
              <option [value]="10">10</option>
              <option [value]="20">20</option>
              <option [value]="50">50</option>
              <option [value]="100">100</option>
            </select>
          </div>
          <span class="page-info">
            {{ getStartIndex() + 1 }}-{{ getEndIndex() }} of {{ totalEntries() }}
          </span>
          <div class="page-controls">
            <button class="btn-page" [disabled]="currentPage() <= 1" (click)="previousPage()">
              <span class="material-symbols-outlined">chevron_left</span>
            </button>
            <span class="page-number">{{ currentPage() }}</span>
            <button class="btn-page" [disabled]="currentPage() >= getTotalPages()" (click)="nextPage()">
              <span class="material-symbols-outlined">chevron_right</span>
            </button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .page-container { padding: 1.5rem; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .header-info h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
    .header-info .subtitle { font-size: 0.875rem; color: var(--text-secondary); }
    .btn-secondary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; font-size: 0.875rem; font-weight: 500; background-color: var(--surface); color: var(--text-primary); border: 1px solid var(--border); border-radius: 0.5rem; cursor: pointer; &:hover { background-color: var(--hover); } }

    .filters-bar { display: flex; justify-content: space-between; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .search-box { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem; flex: 1; max-width: 400px; .material-symbols-outlined { color: var(--text-tertiary); } input { flex: 1; background: transparent; border: none; outline: none; color: var(--text-primary); font-size: 0.875rem; &::placeholder { color: var(--text-tertiary); } } }
    .filter-group { display: flex; gap: 0.75rem; }
    .filter-group select, .date-input { padding: 0.5rem 1rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem; color: var(--text-primary); font-size: 0.875rem; cursor: pointer; &:focus { outline: none; border-color: var(--primary); } }

    .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
    .stat-card { padding: 1rem 1.25rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; text-align: center; &.success { border-left: 3px solid #10b981; } &.warning { border-left: 3px solid #f59e0b; } &.error { border-left: 3px solid #ef4444; } }
    .stat-value { display: block; font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
    .stat-label { font-size: 0.75rem; color: var(--text-secondary); }

    .loading-state { display: flex; flex-direction: column; align-items: center; padding: 4rem; }
    .spinner { width: 2.5rem; height: 2.5rem; border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 1rem; }

    .log-table { background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; overflow: hidden; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }
    th { font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); background-color: var(--background); text-transform: uppercase; }
    td { font-size: 0.875rem; color: var(--text-primary); }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background-color: var(--hover); }

    .timestamp { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-tertiary); white-space: nowrap; }
    .action { font-weight: 500; }
    .ip { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-tertiary); }
    .details { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.75rem; color: var(--text-secondary); }

    .user-cell { .user-name { display: block; font-weight: 500; } .user-email { font-size: 0.75rem; color: var(--text-secondary); } }

    .category-badge { padding: 0.25rem 0.5rem; font-size: 0.625rem; font-weight: 600; border-radius: 0.25rem; text-transform: uppercase; &.auth { background-color: rgba(59, 130, 246, 0.1); color: #3b82f6; } &.user { background-color: rgba(139, 92, 246, 0.1); color: #8b5cf6; } &.content { background-color: rgba(16, 185, 129, 0.1); color: #10b981; } &.payment { background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; } &.system { background-color: var(--background); color: var(--text-secondary); } &.admin { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; } }

    .status-badge { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.25rem 0.5rem; font-size: 0.75rem; font-weight: 500; border-radius: 9999px; text-transform: capitalize; .material-symbols-outlined { font-size: 0.875rem; } &.success { background-color: rgba(16, 185, 129, 0.1); color: #10b981; } &.warning { background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; } &.error { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; } }

    .empty-state { display: flex; flex-direction: column; align-items: center; padding: 3rem; .material-symbols-outlined { font-size: 3rem; color: var(--text-tertiary); margin-bottom: 0.5rem; } p { color: var(--text-secondary); } }

    .clear-search { position: absolute; right: 0.5rem; padding: 0.25rem; background: transparent; border: none; color: var(--text-tertiary); cursor: pointer; border-radius: 0.25rem; &:hover { color: var(--text-primary); background-color: var(--hover); } .material-symbols-outlined { font-size: 1rem; } }
    .search-box { position: relative; }
    .btn-clear-filters { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.5rem 0.75rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem; color: var(--text-secondary); font-size: 0.75rem; cursor: pointer; &:hover { background-color: var(--hover); color: var(--text-primary); } .material-symbols-outlined { font-size: 1rem; } }

    .pagination { display: flex; justify-content: flex-end; align-items: center; gap: 1.5rem; padding: 1rem; border-top: 1px solid var(--border); }
    .page-size-select { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; color: var(--text-secondary); select { padding: 0.25rem 0.5rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.25rem; color: var(--text-primary); font-size: 0.875rem; cursor: pointer; } }
    .page-info { font-size: 0.875rem; color: var(--text-secondary); }
    .page-controls { display: flex; align-items: center; gap: 0.5rem; }
    .btn-page { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.375rem; color: var(--text-tertiary); cursor: pointer; &:hover:not(:disabled) { background-color: var(--hover); color: var(--text-primary); } &:disabled { opacity: 0.5; cursor: not-allowed; } }
    .page-number { padding: 0.25rem 0.75rem; font-size: 0.875rem; font-weight: 500; background-color: var(--primary); color: white; border-radius: 0.375rem; }

    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class AuditLogComponent implements OnInit {
  private toastService = inject(ToastService);
  private adminService = inject(AdminService);

  entries = signal<AuditEntry[]>([]);
  filteredEntries = signal<AuditEntry[]>([]);
  isLoading = signal(true);
  totalEntries = signal(0);
  currentPage = signal(1);
  pageSize = 20;

  searchQuery = '';
  actionFilter = '';
  resourceFilter = '';
  dateFilter = '';

  ngOnInit(): void { this.loadEntries(); }

  refreshLogs(): void {
    this.currentPage.set(1);
    this.loadEntries();
    this.toastService.info('Refreshing', 'Loading latest audit logs...');
  }

  loadEntries(): void {
    this.isLoading.set(true);

    const filters: AuditLogFilters = {
      page: this.currentPage(),
      page_size: this.pageSize,
      status: this.actionFilter || undefined,
      category: this.resourceFilter || undefined,
      from_date: this.dateFilter || undefined
    };

    this.adminService.getAuditLogs(filters).subscribe({
      next: (response) => {
        const mapped: AuditEntry[] = response.items.map(log => ({
          id: log.id,
          action: this.formatAction(log.action),
          category: log.category || 'system',
          user: log.user_email?.split('@')[0] || 'Unknown',
          user_email: log.user_email || 'Unknown',
          ip_address: log.ip_address || 'N/A',
          details: log.details,
          timestamp: log.timestamp,
          status: log.status || 'success'
        }));
        this.entries.set(mapped);
        this.filteredEntries.set(mapped);
        this.totalEntries.set(response.total);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load audit logs:', err);
        // Fallback to mock data for development
        const mock: AuditEntry[] = [
          { id: '1', action: 'Login', category: 'auth', user: 'admin', user_email: 'admin@edubot.co.zw', ip_address: '192.168.1.1', details: 'Successful login', timestamp: new Date().toISOString(), status: 'success' },
          { id: '2', action: 'Create Admin', category: 'admin_user', user: 'superadmin', user_email: 'superadmin@edubot.co.zw', ip_address: '192.168.1.100', details: '{"email":"new@admin.com"}', timestamp: new Date(Date.now() - 3600000).toISOString(), status: 'success' },
          { id: '3', action: 'Update Settings', category: 'system_settings', user: 'admin', user_email: 'admin@edubot.co.zw', ip_address: '192.168.1.1', details: '{"maintenance_mode":false}', timestamp: new Date(Date.now() - 7200000).toISOString(), status: 'success' },
          { id: '4', action: 'Delete User', category: 'user', user: 'admin', user_email: 'admin@edubot.co.zw', ip_address: '192.168.1.1', details: '{"user_id":"123"}', timestamp: new Date(Date.now() - 86400000).toISOString(), status: 'success' },
          { id: '5', action: 'Export Data', category: 'system', user: 'admin', user_email: 'admin@edubot.co.zw', ip_address: '192.168.1.1', details: 'User data export', timestamp: new Date(Date.now() - 172800000).toISOString(), status: 'success' },
        ];
        this.entries.set(mock);
        this.filteredEntries.set(mock);
        this.totalEntries.set(mock.length);
        this.isLoading.set(false);
      }
    });
  }

  formatAction(action: string): string {
    return action
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  }

  applyFilters(): void {
    let result = this.entries();
    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      result = result.filter(e =>
        e.action.toLowerCase().includes(q) ||
        e.user.toLowerCase().includes(q) ||
        e.user_email.toLowerCase().includes(q) ||
        e.details.toLowerCase().includes(q) ||
        e.category.toLowerCase().includes(q)
      );
    }
    this.filteredEntries.set(result);
  }

  getSuccessCount(): number { return this.entries().filter(e => e.status === 'success').length; }
  getWarningCount(): number { return this.entries().filter(e => e.status === 'warning').length; }
  getErrorCount(): number { return this.entries().filter(e => e.status === 'error').length; }

  clearSearch(): void {
    this.searchQuery = '';
    this.applyFilters();
  }

  hasActiveFilters(): boolean {
    return !!(this.actionFilter || this.resourceFilter || this.dateFilter);
  }

  clearFilters(): void {
    this.actionFilter = '';
    this.resourceFilter = '';
    this.dateFilter = '';
    this.searchQuery = '';
    this.currentPage.set(1);
    this.loadEntries();
  }

  // Pagination methods
  onPageSizeChange(): void {
    this.currentPage.set(1);
    this.loadEntries();
  }

  getStartIndex(): number {
    return (this.currentPage() - 1) * this.pageSize;
  }

  getEndIndex(): number {
    return Math.min(this.currentPage() * this.pageSize, this.totalEntries());
  }

  getTotalPages(): number {
    return Math.ceil(this.totalEntries() / this.pageSize);
  }

  previousPage(): void {
    if (this.currentPage() > 1) {
      this.currentPage.set(this.currentPage() - 1);
      this.loadEntries();
    }
  }

  nextPage(): void {
    if (this.currentPage() < this.getTotalPages()) {
      this.currentPage.set(this.currentPage() + 1);
      this.loadEntries();
    }
  }

  exportLogs(): void {
    this.toastService.info('Exporting...', 'Preparing audit log export');

    const filters: AuditLogFilters = {
      category: this.resourceFilter || undefined,
      status: this.actionFilter || undefined,
      from_date: this.dateFilter || undefined
    };

    this.adminService.exportAuditLogs(filters).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.toastService.success('Export Complete', 'Audit logs exported successfully');
      },
      error: (err) => {
        console.error('Export failed:', err);
        this.toastService.error('Export Failed', 'Failed to export audit logs');
      }
    });
  }
}
