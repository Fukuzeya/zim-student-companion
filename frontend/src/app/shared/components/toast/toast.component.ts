import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService, Toast } from '../../../core/services/toast.service';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast-container">
      @for (toast of toastService.toasts(); track toast.id) {
        <div class="toast" [class]="'toast-' + toast.type" (click)="dismiss(toast)">
          <div class="toast-icon">
            <span class="material-symbols-outlined">{{ getIcon(toast.type) }}</span>
          </div>
          <div class="toast-content">
            <p class="toast-title">{{ toast.title }}</p>
            @if (toast.message) {
              <p class="toast-message">{{ toast.message }}</p>
            }
          </div>
          @if (toast.dismissible) {
            <button class="toast-close" (click)="dismiss(toast); $event.stopPropagation()">
              <span class="material-symbols-outlined">close</span>
            </button>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      top: 1rem;
      right: 1rem;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      max-width: 24rem;
    }

    .toast {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      padding: 1rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      box-shadow: var(--shadow-lg);
      cursor: pointer;
      animation: slideIn 0.3s ease-out;

      &-success {
        border-left: 4px solid var(--success);
        .toast-icon { color: var(--success); }
      }

      &-error {
        border-left: 4px solid var(--error);
        .toast-icon { color: var(--error); }
      }

      &-warning {
        border-left: 4px solid var(--warning);
        .toast-icon { color: var(--warning); }
      }

      &-info {
        border-left: 4px solid var(--info);
        .toast-icon { color: var(--info); }
      }
    }

    .toast-icon {
      flex-shrink: 0;
      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .toast-content {
      flex: 1;
      min-width: 0;
    }

    .toast-title {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 0.25rem;
    }

    .toast-message {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .toast-close {
      flex-shrink: 0;
      padding: 0.25rem;
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      border-radius: 0.25rem;
      transition: background-color 0.15s ease;

      &:hover {
        background-color: var(--background);
        color: var(--text-primary);
      }

      .material-symbols-outlined {
        font-size: 1rem;
      }
    }

    @keyframes slideIn {
      from {
        opacity: 0;
        transform: translateX(100%);
      }
      to {
        opacity: 1;
        transform: translateX(0);
      }
    }
  `]
})
export class ToastComponent {
  toastService = inject(ToastService);

  getIcon(type: string): string {
    const icons: Record<string, string> = {
      success: 'check_circle',
      error: 'error',
      warning: 'warning',
      info: 'info'
    };
    return icons[type] || 'info';
  }

  dismiss(toast: Toast): void {
    this.toastService.dismiss(toast.id);
  }
}
