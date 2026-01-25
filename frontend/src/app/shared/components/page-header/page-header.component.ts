import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

export interface Breadcrumb {
  label: string;
  link?: string;
}

@Component({
  selector: 'app-page-header',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="page-header">
      <!-- Breadcrumbs -->
      @if (breadcrumbs.length > 0) {
        <nav class="breadcrumbs" aria-label="Breadcrumb">
          <ol>
            @for (crumb of breadcrumbs; track crumb.label; let isLast = $last) {
              <li>
                @if (crumb.link && !isLast) {
                  <a [routerLink]="crumb.link" class="breadcrumb-link">
                    @if ($first) {
                      <span class="material-symbols-outlined">home</span>
                    }
                    {{ crumb.label }}
                  </a>
                } @else {
                  <span class="breadcrumb-current">{{ crumb.label }}</span>
                }
                @if (!isLast) {
                  <span class="material-symbols-outlined separator">chevron_right</span>
                }
              </li>
            }
          </ol>
        </nav>
      }

      <!-- Header content -->
      <div class="header-content">
        <div class="header-text">
          <h1 class="page-title">{{ title }}</h1>
          @if (description) {
            <p class="page-description">{{ description }}</p>
          }
        </div>
        <div class="header-actions">
          <ng-content select="[headerActions]"></ng-content>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .page-header {
      margin-bottom: 1.5rem;
    }

    .breadcrumbs {
      margin-bottom: 1rem;

      ol {
        display: flex;
        align-items: center;
        list-style: none;
        padding: 0;
        margin: 0;
        gap: 0.25rem;
      }

      li {
        display: flex;
        align-items: center;
        gap: 0.25rem;
      }
    }

    .breadcrumb-link {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      font-size: 0.875rem;
      color: var(--text-secondary);
      transition: color 0.15s ease;

      &:hover {
        color: var(--primary);
      }

      .material-symbols-outlined {
        font-size: 1rem;
      }
    }

    .breadcrumb-current {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-primary);
    }

    .separator {
      font-size: 1rem;
      color: var(--border);
    }

    .header-content {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 1rem;
      flex-wrap: wrap;
    }

    .header-text {
      flex: 1;
      min-width: 0;
    }

    .page-title {
      font-size: 1.875rem;
      font-weight: 800;
      color: var(--text-primary);
      margin-bottom: 0.25rem;
      letter-spacing: -0.025em;
    }

    .page-description {
      font-size: 0.875rem;
      color: var(--text-secondary);
      max-width: 40rem;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-shrink: 0;
    }
  `]
})
export class PageHeaderComponent {
  @Input() title!: string;
  @Input() description?: string;
  @Input() breadcrumbs: Breadcrumb[] = [];
}
