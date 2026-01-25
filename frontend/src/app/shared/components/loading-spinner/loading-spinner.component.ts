import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-loading-spinner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="loading-container" [class.overlay]="overlay" [class.fullscreen]="fullscreen">
      <div class="spinner-wrapper">
        <div class="spinner" [style.width.rem]="size" [style.height.rem]="size"></div>
        @if (message) {
          <p class="loading-message">{{ message }}</p>
        }
      </div>
    </div>
  `,
  styles: [`
    .loading-container {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;

      &.overlay {
        position: absolute;
        inset: 0;
        background-color: rgba(var(--background-rgb), 0.8);
        backdrop-filter: blur(4px);
        z-index: 50;
      }

      &.fullscreen {
        position: fixed;
        inset: 0;
        background-color: var(--background);
        z-index: 100;
      }
    }

    .spinner-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
    }

    .spinner {
      border: 3px solid var(--border);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    .loading-message {
      font-size: 0.875rem;
      color: var(--text-secondary);
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class LoadingSpinnerComponent {
  @Input() size = 2;
  @Input() message?: string;
  @Input() overlay = false;
  @Input() fullscreen = false;
}
