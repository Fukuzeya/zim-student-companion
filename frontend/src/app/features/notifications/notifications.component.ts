import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ToastService } from '../../core/services/toast.service';

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actionUrl?: string;
  actionLabel?: string;
}

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>Notifications</h1>
          <p class="subtitle">View and manage system notifications</p>
        </div>
        <div class="header-actions">
          <button class="btn-secondary" (click)="markAllRead()">
            <span class="material-symbols-outlined">done_all</span>
            Mark All Read
          </button>
          <button class="btn-secondary" (click)="clearAll()">
            <span class="material-symbols-outlined">delete_sweep</span>
            Clear All
          </button>
        </div>
      </div>

      <div class="filters-bar">
        <div class="filter-tabs">
          <button [class.active]="activeFilter === 'all'" (click)="activeFilter = 'all'; applyFilter()">
            All
            <span class="count">{{ notifications().length }}</span>
          </button>
          <button [class.active]="activeFilter === 'unread'" (click)="activeFilter = 'unread'; applyFilter()">
            Unread
            <span class="count">{{ getUnreadCount() }}</span>
          </button>
          <button [class.active]="activeFilter === 'info'" (click)="activeFilter = 'info'; applyFilter()">
            <span class="material-symbols-outlined">info</span>
            Info
          </button>
          <button [class.active]="activeFilter === 'success'" (click)="activeFilter = 'success'; applyFilter()">
            <span class="material-symbols-outlined">check_circle</span>
            Success
          </button>
          <button [class.active]="activeFilter === 'warning'" (click)="activeFilter = 'warning'; applyFilter()">
            <span class="material-symbols-outlined">warning</span>
            Warning
          </button>
          <button [class.active]="activeFilter === 'error'" (click)="activeFilter = 'error'; applyFilter()">
            <span class="material-symbols-outlined">error</span>
            Error
          </button>
        </div>
      </div>

      @if (isLoading()) {
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Loading notifications...</p>
        </div>
      } @else {
        <div class="notifications-list">
          @for (notification of filteredNotifications(); track notification.id) {
            <div class="notification-card" [class]="notification.type" [class.unread]="!notification.read">
              <div class="notification-icon" [class]="notification.type">
                <span class="material-symbols-outlined">
                  {{ getIcon(notification.type) }}
                </span>
              </div>
              <div class="notification-content">
                <div class="notification-header">
                  <h4>{{ notification.title }}</h4>
                  <span class="timestamp">{{ notification.timestamp }}</span>
                </div>
                <p class="notification-message">{{ notification.message }}</p>
                @if (notification.actionUrl) {
                  <a class="notification-action" [href]="notification.actionUrl">
                    {{ notification.actionLabel || 'View Details' }}
                    <span class="material-symbols-outlined">arrow_forward</span>
                  </a>
                }
              </div>
              <div class="notification-actions">
                @if (!notification.read) {
                  <button class="action-btn" title="Mark as read" (click)="markAsRead(notification)">
                    <span class="material-symbols-outlined">check</span>
                  </button>
                }
                <button class="action-btn" title="Delete" (click)="deleteNotification(notification)">
                  <span class="material-symbols-outlined">close</span>
                </button>
              </div>
            </div>
          } @empty {
            <div class="empty-state">
              <span class="material-symbols-outlined">notifications_off</span>
              <h3>No notifications</h3>
              <p>You're all caught up! No notifications to display.</p>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .page-container { padding: 1.5rem; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .header-info h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
    .header-info .subtitle { font-size: 0.875rem; color: var(--text-secondary); }
    .header-actions { display: flex; gap: 0.75rem; }
    .btn-secondary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; font-size: 0.875rem; font-weight: 500; background-color: var(--surface); color: var(--text-primary); border: 1px solid var(--border); border-radius: 0.5rem; cursor: pointer; &:hover { background-color: var(--hover); } }

    .filters-bar { margin-bottom: 1.5rem; }
    .filter-tabs {
      display: flex; gap: 0.5rem; flex-wrap: wrap;
      button {
        display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem;
        font-size: 0.875rem; font-weight: 500; background-color: var(--surface);
        color: var(--text-secondary); border: 1px solid var(--border); border-radius: 0.5rem; cursor: pointer;
        .material-symbols-outlined { font-size: 1.125rem; }
        .count { padding: 0.125rem 0.5rem; font-size: 0.75rem; background-color: var(--background); border-radius: 9999px; }
        &.active { background-color: var(--primary); color: white; border-color: var(--primary); .count { background-color: rgba(255, 255, 255, 0.2); } }
        &:hover:not(.active) { background-color: var(--hover); }
      }
    }

    .loading-state { display: flex; flex-direction: column; align-items: center; padding: 4rem; }
    .spinner { width: 2.5rem; height: 2.5rem; border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 1rem; }

    .notifications-list { display: flex; flex-direction: column; gap: 0.75rem; }

    .notification-card {
      display: flex; align-items: flex-start; gap: 1rem; padding: 1.25rem;
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem;
      transition: all 0.15s ease;
      &:hover { border-color: var(--primary); }
      &.unread { background-color: rgba(0, 102, 70, 0.03); border-left: 3px solid var(--primary); }
      &.info.unread { border-left-color: #3b82f6; }
      &.success.unread { border-left-color: #10b981; }
      &.warning.unread { border-left-color: #f59e0b; }
      &.error.unread { border-left-color: #ef4444; }
    }

    .notification-icon {
      width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;
      border-radius: 0.5rem; flex-shrink: 0;
      &.info { background-color: rgba(59, 130, 246, 0.1); .material-symbols-outlined { color: #3b82f6; } }
      &.success { background-color: rgba(16, 185, 129, 0.1); .material-symbols-outlined { color: #10b981; } }
      &.warning { background-color: rgba(245, 158, 11, 0.1); .material-symbols-outlined { color: #f59e0b; } }
      &.error { background-color: rgba(239, 68, 68, 0.1); .material-symbols-outlined { color: #ef4444; } }
    }

    .notification-content { flex: 1; min-width: 0; }
    .notification-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 0.25rem; }
    .notification-header h4 { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); }
    .timestamp { font-size: 0.75rem; color: var(--text-tertiary); white-space: nowrap; }
    .notification-message { font-size: 0.875rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 0.75rem; }
    .notification-action {
      display: inline-flex; align-items: center; gap: 0.25rem; font-size: 0.875rem; font-weight: 500;
      color: var(--primary); text-decoration: none;
      .material-symbols-outlined { font-size: 1rem; transition: transform 0.15s ease; }
      &:hover .material-symbols-outlined { transform: translateX(4px); }
    }

    .notification-actions { display: flex; gap: 0.25rem; flex-shrink: 0; }
    .action-btn {
      width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
      background: transparent; border: none; border-radius: 0.375rem; color: var(--text-tertiary); cursor: pointer;
      &:hover { background-color: var(--hover); color: var(--text-primary); }
      .material-symbols-outlined { font-size: 1.125rem; }
    }

    .empty-state {
      display: flex; flex-direction: column; align-items: center; padding: 4rem;
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem;
      .material-symbols-outlined { font-size: 4rem; color: var(--text-tertiary); margin-bottom: 1rem; }
      h3 { font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; }
      p { color: var(--text-secondary); }
    }

    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class NotificationsComponent implements OnInit {
  private toastService = inject(ToastService);

  notifications = signal<Notification[]>([]);
  filteredNotifications = signal<Notification[]>([]);
  isLoading = signal(true);
  activeFilter: 'all' | 'unread' | 'info' | 'success' | 'warning' | 'error' = 'all';

  ngOnInit(): void { this.loadNotifications(); }

  loadNotifications(): void {
    this.isLoading.set(true);
    const mock: Notification[] = [
      { id: '1', type: 'success', title: 'New User Registered', message: 'John Doe has just created a new account and started the free trial.', timestamp: '5 minutes ago', read: false, actionUrl: '/users', actionLabel: 'View User' },
      { id: '2', type: 'success', title: 'Payment Received', message: 'Successfully processed payment of $9.99 from jane@example.com for Premium subscription.', timestamp: '15 minutes ago', read: false, actionUrl: '/payments', actionLabel: 'View Transaction' },
      { id: '3', type: 'warning', title: 'High Server Load', message: 'CPU usage has exceeded 80% threshold. Consider scaling resources if this persists.', timestamp: '1 hour ago', read: false, actionUrl: '/system/health', actionLabel: 'View System Health' },
      { id: '4', type: 'info', title: 'Competition Starting Soon', message: 'The "Math Challenge 2024" competition will begin in 30 minutes with 156 registered participants.', timestamp: '2 hours ago', read: true, actionUrl: '/live/competitions' },
      { id: '5', type: 'error', title: 'Payment Failed', message: 'Payment processing failed for user bob@example.com. Card declined by issuer.', timestamp: '3 hours ago', read: true, actionUrl: '/payments' },
      { id: '6', type: 'info', title: 'System Backup Complete', message: 'Daily automated backup completed successfully. All data has been secured.', timestamp: '6 hours ago', read: true },
      { id: '7', type: 'success', title: 'Content Updated', message: '25 new questions have been added to the Mathematics question bank by the content team.', timestamp: 'Yesterday', read: true, actionUrl: '/content/questions' },
      { id: '8', type: 'warning', title: 'Subscription Expiring', message: '15 premium subscriptions are expiring within the next 7 days. Consider sending renewal reminders.', timestamp: 'Yesterday', read: true, actionUrl: '/payments/subscriptions' },
    ];
    setTimeout(() => { this.notifications.set(mock); this.filteredNotifications.set(mock); this.isLoading.set(false); }, 500);
  }

  applyFilter(): void {
    let result = this.notifications();
    switch (this.activeFilter) {
      case 'unread': result = result.filter(n => !n.read); break;
      case 'info': result = result.filter(n => n.type === 'info'); break;
      case 'success': result = result.filter(n => n.type === 'success'); break;
      case 'warning': result = result.filter(n => n.type === 'warning'); break;
      case 'error': result = result.filter(n => n.type === 'error'); break;
    }
    this.filteredNotifications.set(result);
  }

  getIcon(type: string): string {
    const icons: Record<string, string> = { info: 'info', success: 'check_circle', warning: 'warning', error: 'error' };
    return icons[type] || 'info';
  }

  getUnreadCount(): number { return this.notifications().filter(n => !n.read).length; }

  markAsRead(notification: Notification): void {
    notification.read = true;
    this.applyFilter();
    this.toastService.success('Marked as read');
  }

  deleteNotification(notification: Notification): void {
    this.notifications.set(this.notifications().filter(n => n.id !== notification.id));
    this.applyFilter();
    this.toastService.success('Notification deleted');
  }

  markAllRead(): void {
    this.notifications().forEach(n => n.read = true);
    this.applyFilter();
    this.toastService.success('All notifications marked as read');
  }

  clearAll(): void {
    this.notifications.set([]);
    this.filteredNotifications.set([]);
    this.toastService.success('All notifications cleared');
  }
}
