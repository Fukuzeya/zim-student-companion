import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-stat-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="stat-card" [class.clickable]="clickable">
      <div class="stat-header">
        <div class="stat-info">
          <p class="stat-label">{{ label }}</p>
          <h3 class="stat-value">{{ value }}</h3>
        </div>
        <div class="stat-icon" [style.background-color]="iconBgColor">
          <span class="material-symbols-outlined" [style.color]="iconColor">{{ icon }}</span>
        </div>
      </div>

      @if (trend) {
        <div class="stat-footer">
          <span class="stat-trend" [class.up]="trend.direction === 'up'" [class.down]="trend.direction === 'down'">
            <span class="material-symbols-outlined">
              {{ trend.direction === 'up' ? 'trending_up' : trend.direction === 'down' ? 'trending_down' : 'trending_flat' }}
            </span>
            {{ trend.value }}{{ trend.isPercentage ? '%' : '' }}
          </span>
          <span class="stat-period">{{ trend.label }}</span>
        </div>
      }

      @if (progress !== undefined) {
        <div class="stat-progress">
          <div class="progress-bar">
            <div class="progress-fill" [style.width.%]="progress" [style.background-color]="progressColor"></div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .stat-card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.25rem;
      transition: all 0.2s ease;

      &.clickable {
        cursor: pointer;

        &:hover {
          border-color: var(--primary);
          box-shadow: var(--shadow-md);
        }
      }
    }

    .stat-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .stat-info {
      flex: 1;
    }

    .stat-label {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-secondary);
      margin-bottom: 0.25rem;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text-primary);
      font-feature-settings: 'tnum';
    }

    .stat-icon {
      padding: 0.5rem;
      border-radius: 0.5rem;
      background-color: rgba(0, 102, 70, 0.1);

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: var(--primary);
      }
    }

    .stat-footer {
      margin-top: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.75rem;
    }

    .stat-trend {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      font-weight: 500;
      color: var(--text-muted);

      &.up {
        color: var(--success);
      }

      &.down {
        color: var(--error);
      }

      .material-symbols-outlined {
        font-size: 0.875rem;
      }
    }

    .stat-period {
      color: var(--text-muted);
    }

    .stat-progress {
      margin-top: 1rem;
    }

    .progress-bar {
      height: 0.25rem;
      background-color: var(--background);
      border-radius: 9999px;
      overflow: hidden;
    }

    .progress-fill {
      height: 100%;
      background-color: var(--primary);
      border-radius: 9999px;
      transition: width 0.5s ease;
    }
  `]
})
export class StatCardComponent {
  @Input() label!: string;
  @Input() value!: string | number;
  @Input() icon = 'analytics';
  @Input() iconColor?: string;
  @Input() iconBgColor?: string;
  @Input() clickable = false;
  @Input() trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
    label: string;
    isPercentage?: boolean;
  };
  @Input() progress?: number;
  @Input() progressColor?: string;
}
