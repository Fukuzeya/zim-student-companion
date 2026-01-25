import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (isOpen) {
      <div class="dialog-overlay" (click)="onCancel()">
        <div class="dialog" (click)="$event.stopPropagation()">
          <div class="dialog-header">
            <div class="dialog-icon" [class]="type">
              <span class="material-symbols-outlined">{{ getIcon() }}</span>
            </div>
            <h2 class="dialog-title">{{ title }}</h2>
          </div>

          <div class="dialog-body">
            <p>{{ message }}</p>
          </div>

          <div class="dialog-footer">
            <button class="btn btn-secondary" (click)="onCancel()">
              {{ cancelText }}
            </button>
            <button class="btn" [class]="getConfirmButtonClass()" (click)="onConfirm()">
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .dialog-overlay {
      position: fixed;
      inset: 0;
      background-color: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      animation: fadeIn 0.15s ease;
    }

    .dialog {
      background-color: var(--surface);
      border-radius: 0.75rem;
      box-shadow: var(--shadow-lg);
      width: 100%;
      max-width: 24rem;
      animation: slideUp 0.2s ease;
    }

    .dialog-header {
      padding: 1.5rem 1.5rem 1rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
    }

    .dialog-icon {
      width: 3rem;
      height: 3rem;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 1rem;

      &.danger {
        background-color: rgba(239, 68, 68, 0.1);
        color: var(--error);
      }

      &.warning {
        background-color: rgba(245, 158, 11, 0.1);
        color: var(--warning);
      }

      &.info {
        background-color: rgba(59, 130, 246, 0.1);
        color: var(--info);
      }

      .material-symbols-outlined {
        font-size: 1.5rem;
      }
    }

    .dialog-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--text-primary);
    }

    .dialog-body {
      padding: 0 1.5rem 1.5rem;
      text-align: center;

      p {
        font-size: 0.875rem;
        color: var(--text-secondary);
      }
    }

    .dialog-footer {
      padding: 1rem 1.5rem;
      background-color: var(--background);
      border-top: 1px solid var(--border);
      border-radius: 0 0 0.75rem 0.75rem;
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes slideUp {
      from {
        opacity: 0;
        transform: translateY(10px) scale(0.98);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }
  `]
})
export class ConfirmDialogComponent {
  @Input() isOpen = false;
  @Input() title = 'Confirm Action';
  @Input() message = 'Are you sure you want to proceed?';
  @Input() confirmText = 'Confirm';
  @Input() cancelText = 'Cancel';
  @Input() type: 'danger' | 'warning' | 'info' = 'danger';

  @Output() confirm = new EventEmitter<void>();
  @Output() cancel = new EventEmitter<void>();

  getIcon(): string {
    const icons = {
      danger: 'warning',
      warning: 'help',
      info: 'info'
    };
    return icons[this.type];
  }

  getConfirmButtonClass(): string {
    return this.type === 'danger' ? 'btn-danger' : 'btn-primary';
  }

  onConfirm(): void {
    this.confirm.emit();
  }

  onCancel(): void {
    this.cancel.emit();
  }
}
