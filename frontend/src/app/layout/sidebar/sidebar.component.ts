import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

interface NavItem {
  label: string;
  icon: string;
  route?: string;
  children?: NavItem[];
  badge?: number;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <aside class="sidebar" [class.collapsed]="isCollapsed()">
      <!-- Logo/Brand -->
      <div class="sidebar-header">
        <div class="brand">
          <div class="brand-icon">
            <span class="material-symbols-outlined">school</span>
          </div>
          @if (!isCollapsed()) {
            <div class="brand-text">
              <h1>EduBot Zimbabwe</h1>
              <p>Admin Portal</p>
            </div>
          }
        </div>
        <button class="collapse-btn" (click)="toggleCollapse()">
          <span class="material-symbols-outlined">
            {{ isCollapsed() ? 'chevron_right' : 'chevron_left' }}
          </span>
        </button>
      </div>

      <!-- Navigation -->
      <nav class="sidebar-nav">
        @for (group of navGroups; track group.title) {
          <div class="nav-group">
            @if (!isCollapsed()) {
              <p class="nav-group-title">{{ group.title }}</p>
            }
            @for (item of group.items; track item.label) {
              @if (item.children) {
                <div class="nav-item-wrapper">
                  <button
                    class="nav-item has-children"
                    [class.expanded]="expandedItems().has(item.label)"
                    (click)="toggleExpand(item.label)"
                  >
                    <span class="material-symbols-outlined nav-icon">{{ item.icon }}</span>
                    @if (!isCollapsed()) {
                      <span class="nav-label">{{ item.label }}</span>
                      <span class="material-symbols-outlined expand-icon">
                        {{ expandedItems().has(item.label) ? 'expand_less' : 'expand_more' }}
                      </span>
                    }
                  </button>
                  @if (!isCollapsed() && expandedItems().has(item.label)) {
                    <div class="nav-children">
                      @for (child of item.children; track child.label) {
                        <a
                          class="nav-item child"
                          [routerLink]="child.route"
                          routerLinkActive="active"
                        >
                          <span class="material-symbols-outlined nav-icon">{{ child.icon }}</span>
                          <span class="nav-label">{{ child.label }}</span>
                          @if (child.badge) {
                            <span class="nav-badge">{{ child.badge }}</span>
                          }
                        </a>
                      }
                    </div>
                  }
                </div>
              } @else {
                <a
                  class="nav-item"
                  [routerLink]="item.route"
                  routerLinkActive="active"
                  [routerLinkActiveOptions]="{ exact: item.route === '/dashboard' }"
                  [title]="isCollapsed() ? item.label : ''"
                >
                  <span class="material-symbols-outlined nav-icon">{{ item.icon }}</span>
                  @if (!isCollapsed()) {
                    <span class="nav-label">{{ item.label }}</span>
                    @if (item.badge) {
                      <span class="nav-badge">{{ item.badge }}</span>
                    }
                  }
                </a>
              }
            }
          </div>
        }
      </nav>

      <!-- Footer -->
      <div class="sidebar-footer">
        <a class="nav-item" routerLink="/system/settings" routerLinkActive="active" [title]="isCollapsed() ? 'Settings' : ''">
          <span class="material-symbols-outlined nav-icon">settings</span>
          @if (!isCollapsed()) {
            <span class="nav-label">Settings</span>
          }
        </a>
        <button class="nav-item logout" (click)="logout()" [title]="isCollapsed() ? 'Logout' : ''">
          <span class="material-symbols-outlined nav-icon">logout</span>
          @if (!isCollapsed()) {
            <span class="nav-label">Logout</span>
          }
        </button>
      </div>
    </aside>
  `,
  styles: [`
    .sidebar {
      width: 280px;
      height: 100vh;
      background-color: var(--sidebar-bg);
      border-right: 1px solid var(--sidebar-border);
      display: flex;
      flex-direction: column;
      transition: width 0.2s ease;
      flex-shrink: 0;
      z-index: 30;

      &.collapsed {
        width: 72px;

        .sidebar-header {
          padding: 1rem;
          justify-content: center;
        }

        .brand-icon {
          margin-right: 0;
        }

        .collapse-btn {
          position: absolute;
          right: -12px;
          top: 50%;
          transform: translateY(-50%);
          background: var(--sidebar-bg);
          border: 1px solid var(--sidebar-border);
          border-radius: 50%;
          width: 24px;
          height: 24px;
        }

        .nav-item {
          justify-content: center;
          padding: 0.75rem;
        }

        .nav-icon {
          margin-right: 0;
        }
      }
    }

    .sidebar-header {
      height: 80px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1rem 0 1.5rem;
      border-bottom: 1px solid var(--sidebar-border);
      position: relative;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .brand-icon {
      width: 40px;
      height: 40px;
      background-color: rgba(0, 102, 70, 0.2);
      border-radius: 0.5rem;
      display: flex;
      align-items: center;
      justify-content: center;

      .material-symbols-outlined {
        font-size: 1.5rem;
        color: var(--primary);
      }
    }

    .brand-text {
      h1 {
        font-size: 1rem;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1.2;
      }

      p {
        font-size: 0.75rem;
        color: var(--text-secondary);
      }
    }

    .collapse-btn {
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      border-radius: 0.25rem;
      transition: all 0.15s ease;

      &:hover {
        background-color: var(--surface);
        color: var(--text-primary);
      }

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .sidebar-nav {
      flex: 1;
      overflow-y: auto;
      padding: 1.5rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .nav-group-title {
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--text-secondary);
      padding: 0 0.75rem;
      margin-bottom: 0.5rem;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.625rem 0.75rem;
      border-radius: 0.5rem;
      color: var(--text-secondary);
      text-decoration: none;
      transition: all 0.15s ease;
      cursor: pointer;
      background: transparent;
      border: none;
      width: 100%;
      text-align: left;
      font-size: 0.875rem;
      font-family: inherit;

      &:hover {
        background-color: var(--surface);
        color: var(--text-primary);
      }

      &.active {
        background-color: var(--primary);
        color: white;
        box-shadow: 0 2px 8px rgba(0, 102, 70, 0.25);

        .nav-icon {
          color: white;
        }
      }

      &.has-children {
        &.expanded {
          background-color: var(--surface);
        }
      }

      &.child {
        padding-left: 2.5rem;
        font-size: 0.8125rem;
      }

      &.logout {
        color: var(--error);

        &:hover {
          background-color: rgba(239, 68, 68, 0.1);
        }
      }
    }

    .nav-icon {
      font-size: 1.25rem;
      color: var(--text-secondary);
      flex-shrink: 0;
    }

    .nav-label {
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .expand-icon {
      font-size: 1.125rem;
      color: var(--text-muted);
      margin-left: auto;
    }

    .nav-badge {
      background-color: var(--primary);
      color: white;
      font-size: 0.6875rem;
      font-weight: 600;
      padding: 0.125rem 0.5rem;
      border-radius: 9999px;
      margin-left: auto;
    }

    .nav-children {
      margin-top: 0.25rem;
    }

    .sidebar-footer {
      padding: 1rem;
      border-top: 1px solid var(--sidebar-border);
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }
  `]
})
export class SidebarComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  isCollapsed = signal(false);
  expandedItems = signal<Set<string>>(new Set());

  navGroups: NavGroup[] = [
    {
      title: 'Overview',
      items: [
        { label: 'Dashboard', icon: 'dashboard', route: '/dashboard' },
        { label: 'Analytics', icon: 'analytics', route: '/analytics' }
      ]
    },
    {
      title: 'Management',
      items: [
        {
          label: 'Users',
          icon: 'group',
          children: [
            { label: 'All Users', icon: 'people', route: '/users' },
            { label: 'Students', icon: 'school', route: '/students' },
            { label: 'Admins', icon: 'admin_panel_settings', route: '/users/admins' }
          ]
        },
        {
          label: 'Content',
          icon: 'library_books',
          children: [
            { label: 'Questions', icon: 'quiz', route: '/content/questions' },
            { label: 'Subjects', icon: 'category', route: '/content/subjects' },
            { label: 'Documents', icon: 'description', route: '/content/documents' },
            { label: 'Curriculum', icon: 'account_tree', route: '/content/curriculum' }
          ]
        },
        {
          label: 'Finance',
          icon: 'payments',
          children: [
            { label: 'Payments', icon: 'receipt_long', route: '/payments' },
            { label: 'Subscriptions', icon: 'card_membership', route: '/payments/subscriptions' },
            { label: 'Plans', icon: 'loyalty', route: '/payments/plans' }
          ]
        }
      ]
    },
    {
      title: 'Live Operations',
      items: [
        { label: 'Conversations', icon: 'chat', route: '/live/conversations', badge: 5 },
        { label: 'Competitions', icon: 'emoji_events', route: '/live/competitions' },
        { label: 'Broadcasts', icon: 'campaign', route: '/live/broadcasts' }
      ]
    },
    {
      title: 'System',
      items: [
        { label: 'Audit Log', icon: 'history', route: '/system/audit' },
        { label: 'System Health', icon: 'monitor_heart', route: '/system/health' }
      ]
    }
  ];

  toggleCollapse(): void {
    this.isCollapsed.update(v => !v);
  }

  toggleExpand(label: string): void {
    this.expandedItems.update(items => {
      const newItems = new Set(items);
      if (newItems.has(label)) {
        newItems.delete(label);
      } else {
        newItems.add(label);
      }
      return newItems;
    });
  }

  logout(): void {
    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/auth/login']),
      error: () => this.router.navigate(['/auth/login'])
    });
  }
}
