import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { HeaderComponent } from '../header/header.component';
import { ToastComponent } from '../../shared/components/toast/toast.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, RouterModule, SidebarComponent, HeaderComponent, ToastComponent],
  template: `
    <div class="main-layout">
      <app-sidebar />
      <div class="main-content">
        <app-header />
        <main class="content-area">
          <router-outlet />
        </main>
        <footer class="main-footer">
          <p>&copy; 2024 EduBot Zimbabwe. Bank-Grade Security Enabled.</p>
          <div class="footer-links">
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Service</a>
            <a href="#">Support</a>
          </div>
        </footer>
      </div>
      <app-toast />
    </div>
  `,
  styles: [`
    .main-layout {
      display: flex;
      min-height: 100vh;
      background-color: var(--background);
    }

    .main-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
      overflow: hidden;
    }

    .content-area {
      flex: 1;
      overflow-y: auto;
      padding: 1.5rem 2rem;
    }

    .main-footer {
      padding: 1.5rem 2rem;
      border-top: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--text-muted);
      flex-shrink: 0;

      @media (max-width: 768px) {
        flex-direction: column;
        gap: 0.5rem;
        text-align: center;
      }
    }

    .footer-links {
      display: flex;
      gap: 1.5rem;

      a {
        color: var(--text-muted);
        transition: color 0.15s ease;

        &:hover {
          color: var(--text-primary);
        }
      }
    }
  `]
})
export class MainLayoutComponent {}
