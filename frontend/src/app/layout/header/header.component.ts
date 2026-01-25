import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { ThemeService } from '../../core/services/theme.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  template: `
    <header class="header">
      <!-- Search -->
      <div class="header-search">
        <div class="search-wrapper">
          <span class="material-symbols-outlined">search</span>
          <input
            type="text"
            placeholder="Search users, transactions, or logs... (Ctrl+K)"
            [(ngModel)]="searchQuery"
          />
          <kbd>⌘K</kbd>
        </div>
      </div>

      <!-- Right Actions -->
      <div class="header-actions">
        <!-- System Health Status -->
        <div class="system-status">
          <span class="status-dot online pulse"></span>
          <span class="status-text">System Operational</span>
        </div>

        <!-- Theme Toggle -->
        <button class="icon-btn" (click)="toggleTheme()" title="Toggle theme">
          <span class="material-symbols-outlined">
            {{ themeService.isDark() ? 'light_mode' : 'dark_mode' }}
          </span>
        </button>

        <!-- Notifications -->
        <button class="icon-btn" (click)="toggleNotifications()" title="Notifications">
          <span class="material-symbols-outlined">notifications</span>
          @if (unreadCount() > 0) {
            <span class="notification-badge">{{ unreadCount() }}</span>
          }
        </button>

        <!-- Help -->
        <button class="icon-btn" title="Help">
          <span class="material-symbols-outlined">help</span>
        </button>

        <div class="divider"></div>

        <!-- User Profile -->
        <div class="user-profile" (click)="toggleProfileMenu()">
          <div class="user-info">
            <span class="user-name">{{ currentUser()?.email || 'Admin User' }}</span>
            <span class="user-role">{{ currentUser()?.role || 'Super Administrator' }}</span>
          </div>
          <div class="user-avatar">
            {{ getInitials() }}
          </div>
          <span class="material-symbols-outlined expand-icon">expand_more</span>
        </div>

        <!-- Profile Dropdown -->
        @if (showProfileMenu()) {
          <div class="profile-dropdown">
            <a class="dropdown-item" routerLink="/profile">
              <span class="material-symbols-outlined">person</span>
              My Profile
            </a>
            <a class="dropdown-item" routerLink="/settings">
              <span class="material-symbols-outlined">settings</span>
              Settings
            </a>
            <div class="dropdown-divider"></div>
            <button class="dropdown-item logout" (click)="logout()">
              <span class="material-symbols-outlined">logout</span>
              Logout
            </button>
          </div>
        }
      </div>
    </header>
  `,
  styles: [`
    .header {
      height: 80px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1.5rem;
      background-color: var(--header-bg);
      border-bottom: 1px solid var(--header-border);
      backdrop-filter: blur(8px);
      position: sticky;
      top: 0;
      z-index: 20;
    }

    .header-search {
      flex: 1;
      max-width: 600px;
    }

    .search-wrapper {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      padding: 0 1rem;
      transition: border-color 0.15s ease;

      &:focus-within {
        border-color: var(--primary);
      }

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: var(--text-secondary);
      }

      input {
        flex: 1;
        border: none;
        background: transparent;
        padding: 0.625rem 0;
        font-size: 0.875rem;

        &:focus {
          outline: none;
          box-shadow: none;
        }
      }

      kbd {
        font-size: 0.6875rem;
        padding: 0.125rem 0.375rem;
        border: 1px solid var(--border);
        border-radius: 0.25rem;
        color: var(--text-muted);
        font-family: inherit;
      }
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      position: relative;
    }

    .system-status {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.375rem 0.75rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 9999px;
      margin-right: 0.5rem;

      @media (max-width: 768px) {
        display: none;
      }
    }

    .status-dot {
      width: 0.5rem;
      height: 0.5rem;
      border-radius: 50%;
      background-color: var(--success);

      &.pulse {
        animation: pulse 2s ease-in-out infinite;
      }
    }

    .status-text {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-primary);
      text-transform: uppercase;
      letter-spacing: 0.025em;
    }

    .icon-btn {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      color: var(--text-secondary);
      border-radius: 0.5rem;
      cursor: pointer;
      transition: all 0.15s ease;
      position: relative;

      &:hover {
        background-color: var(--surface);
        color: var(--text-primary);
      }

      .material-symbols-outlined {
        font-size: 1.5rem;
      }
    }

    .notification-badge {
      position: absolute;
      top: 6px;
      right: 6px;
      width: 8px;
      height: 8px;
      background-color: var(--error);
      border-radius: 50%;
      border: 2px solid var(--header-bg);
    }

    .divider {
      width: 1px;
      height: 32px;
      background-color: var(--border);
      margin: 0 0.75rem;
    }

    .user-profile {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.5rem;
      border-radius: 0.5rem;
      cursor: pointer;
      transition: background-color 0.15s ease;

      &:hover {
        background-color: var(--surface);
      }
    }

    .user-info {
      display: flex;
      flex-direction: column;
      text-align: right;

      @media (max-width: 768px) {
        display: none;
      }
    }

    .user-name {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--text-primary);
    }

    .user-role {
      font-size: 0.75rem;
      color: var(--text-secondary);
    }

    .user-avatar {
      width: 40px;
      height: 40px;
      background-color: var(--primary);
      color: white;
      font-size: 0.875rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      border: 2px solid var(--border);
    }

    .expand-icon {
      font-size: 1.25rem;
      color: var(--text-muted);
    }

    .profile-dropdown {
      position: absolute;
      top: calc(100% + 0.5rem);
      right: 0;
      width: 200px;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      box-shadow: var(--shadow-lg);
      padding: 0.5rem;
      animation: fadeIn 0.15s ease;
    }

    .dropdown-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.625rem 0.75rem;
      border-radius: 0.5rem;
      color: var(--text-primary);
      text-decoration: none;
      font-size: 0.875rem;
      transition: background-color 0.15s ease;
      cursor: pointer;
      background: transparent;
      border: none;
      width: 100%;
      text-align: left;
      font-family: inherit;

      &:hover {
        background-color: var(--background);
      }

      &.logout {
        color: var(--error);
      }

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .dropdown-divider {
      height: 1px;
      background-color: var(--border);
      margin: 0.5rem 0;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-4px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `]
})
export class HeaderComponent {
  authService = inject(AuthService);
  themeService = inject(ThemeService);

  searchQuery = '';
  showProfileMenu = signal(false);
  unreadCount = signal(3);

  currentUser = this.authService.currentUser;

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  toggleNotifications(): void {
    // TODO: Implement notifications panel
  }

  toggleProfileMenu(): void {
    this.showProfileMenu.update(v => !v);
  }

  getInitials(): string {
    const email = this.currentUser()?.email;
    if (!email) return 'AU';
    return email.substring(0, 2).toUpperCase();
  }

  logout(): void {
    this.authService.logout().subscribe();
  }
}
