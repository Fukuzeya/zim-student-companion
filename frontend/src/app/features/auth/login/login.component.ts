import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { ToastComponent } from '../../../shared/components/toast/toast.component';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, ToastComponent],
  template: `
    <app-toast />
    <div class="auth-container">
      <!-- Background decoration -->
      <div class="background-decoration">
        <div class="decoration-circle primary"></div>
        <div class="decoration-circle secondary"></div>
      </div>

      <!-- Login Card -->
      <div class="auth-card">
        <!-- Header -->
        <div class="auth-header">
          <div class="brand">
            <div class="brand-icon">
              <span class="material-symbols-outlined">school</span>
            </div>
            <h2>EduBot Zimbabwe</h2>
          </div>
          <div class="auth-title">
            <h1>Admin Portal Access</h1>
            <p>Secure login for authorized personnel only</p>
          </div>
        </div>

        <!-- Form -->
        <form class="auth-form" [formGroup]="loginForm" (ngSubmit)="onSubmit()">
          <!-- Email Field -->
          <div class="form-group">
            <label for="email">Administrator Email</label>
            <div class="input-wrapper">
              <input
                id="email"
                type="email"
                formControlName="email"
                placeholder="admin&#64;edubot.co.zw"
                [class.error]="isFieldInvalid('email')"
              />
              <span class="material-symbols-outlined input-icon">mail</span>
            </div>
            @if (isFieldInvalid('email')) {
              <span class="error-message">Please enter a valid email address</span>
            }
          </div>

          <!-- Password Field -->
          <div class="form-group">
            <div class="label-row">
              <label for="password">Password</label>
            </div>
            <div class="input-wrapper">
              <input
                id="password"
                [type]="showPassword() ? 'text' : 'password'"
                formControlName="password"
                placeholder="••••••••••••"
                [class.error]="isFieldInvalid('password')"
              />
              <button
                type="button"
                class="toggle-password"
                (click)="togglePassword()"
              >
                <span class="material-symbols-outlined">
                  {{ showPassword() ? 'visibility' : 'visibility_off' }}
                </span>
              </button>
            </div>
            @if (isFieldInvalid('password')) {
              <span class="error-message">Password is required</span>
            }
          </div>

          <!-- 2FA Toggle -->
          <div class="toggle-group">
            <div class="toggle-info">
              <p class="toggle-label">Use Authenticator App (2FA)</p>
              <p class="toggle-hint">Required for remote access</p>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" formControlName="use2FA" />
              <span class="toggle-slider"></span>
            </label>
          </div>

          <!-- Submit Button -->
          <div class="form-actions">
            <button
              type="submit"
              class="btn-submit"
              [disabled]="isLoading()"
            >
              @if (isLoading()) {
                <span class="spinner"></span>
                <span>Signing in...</span>
              } @else {
                <span>Secure Login</span>
              }
            </button>
          </div>

          <!-- Links -->
          <div class="auth-links">
            <a href="#" class="link-secondary">Contact Support</a>
            <a routerLink="/auth/forgot-password" class="link-primary">Forgot Password?</a>
          </div>
        </form>

        <!-- Trust Footer -->
        <div class="auth-footer">
          <div class="trust-badge">
            <span class="material-symbols-outlined">lock</span>
            <span>Secure Environment</span>
          </div>
          <p class="trust-text">End-to-End Encrypted • 256-bit SSL • Bank-Grade Security</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .auth-container {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      background-color: #1A2B3C;
      position: relative;
      overflow: hidden;
    }

    .background-decoration {
      position: absolute;
      inset: 0;
      pointer-events: none;
      opacity: 0.2;
    }

    .decoration-circle {
      position: absolute;
      border-radius: 50%;
      filter: blur(100px);

      &.primary {
        width: 600px;
        height: 600px;
        background-color: var(--primary);
        top: -20%;
        right: -10%;
      }

      &.secondary {
        width: 500px;
        height: 500px;
        background-color: #1A2B3C;
        bottom: -20%;
        left: -10%;
      }
    }

    .auth-card {
      width: 100%;
      max-width: 480px;
      background-color: #111e2b;
      border: 1px solid #2A3F55;
      border-radius: 0.75rem;
      box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
      overflow: hidden;
      z-index: 10;
    }

    .auth-header {
      padding: 2.5rem 2rem 1.5rem;
      border-bottom: 1px solid rgba(42, 63, 85, 0.5);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 2rem;

      h2 {
        font-size: 1.25rem;
        font-weight: 700;
        color: white;
      }
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
        font-size: 1.75rem;
        color: var(--primary);
      }
    }

    .auth-title {
      h1 {
        font-size: 1.875rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.5rem;
        letter-spacing: -0.025em;
      }

      p {
        font-size: 0.875rem;
        color: #8dceb9;
      }
    }

    .auth-form {
      padding: 2rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;

      label {
        font-size: 0.875rem;
        font-weight: 500;
        color: white;
      }
    }

    .label-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .input-wrapper {
      display: flex;
      border-radius: 0.5rem;
      overflow: hidden;
      box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);

      input {
        flex: 1;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        color: white;
        background-color: #1A2B3C;
        border: 1px solid #2A3F55;
        border-right: none;
        border-radius: 0.5rem 0 0 0.5rem;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;

        &::placeholder {
          color: #6b7280;
        }

        &:focus {
          outline: none;
          border-color: var(--primary);
          box-shadow: 0 0 0 1px var(--primary);
        }

        &.error {
          border-color: var(--error);
        }
      }
    }

    .input-icon, .toggle-password {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 1rem;
      background-color: #1A2B3C;
      border: 1px solid #2A3F55;
      border-left: none;
      border-radius: 0 0.5rem 0.5rem 0;
      color: #6b7280;
    }

    .toggle-password {
      cursor: pointer;
      transition: color 0.15s ease;

      &:hover {
        color: white;
      }
    }

    .error-message {
      font-size: 0.75rem;
      color: var(--error);
    }

    .toggle-group {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1rem;
      background-color: rgba(26, 43, 60, 0.5);
      border: 1px solid rgba(42, 63, 85, 0.5);
      border-radius: 0.5rem;
    }

    .toggle-info {
      .toggle-label {
        font-size: 0.875rem;
        font-weight: 500;
        color: white;
      }

      .toggle-hint {
        font-size: 0.75rem;
        color: #6b7280;
        margin-top: 0.125rem;
      }
    }

    .toggle-switch {
      position: relative;
      width: 44px;
      height: 24px;

      input {
        opacity: 0;
        width: 0;
        height: 0;

        &:checked + .toggle-slider {
          background-color: var(--primary);
        }

        &:checked + .toggle-slider::before {
          transform: translateX(20px);
        }
      }
    }

    .toggle-slider {
      position: absolute;
      inset: 0;
      background-color: #2A3F55;
      border-radius: 9999px;
      cursor: pointer;
      transition: background-color 0.2s ease;

      &::before {
        content: '';
        position: absolute;
        width: 20px;
        height: 20px;
        left: 2px;
        bottom: 2px;
        background-color: white;
        border-radius: 50%;
        transition: transform 0.2s ease;
        box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.1);
      }
    }

    .form-actions {
      margin-top: 0.5rem;
    }

    .btn-submit {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 0.75rem 1rem;
      font-size: 1rem;
      font-weight: 700;
      color: white;
      background-color: var(--primary);
      border: none;
      border-radius: 0.5rem;
      cursor: pointer;
      transition: background-color 0.15s ease;
      box-shadow: 0 4px 14px 0 rgba(0, 102, 70, 0.25);

      &:hover:not(:disabled) {
        background-color: #005238;
      }

      &:disabled {
        opacity: 0.7;
        cursor: not-allowed;
      }
    }

    .spinner {
      width: 1.25rem;
      height: 1.25rem;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    .auth-links {
      display: flex;
      justify-content: space-between;
      font-size: 0.875rem;

      a {
        font-weight: 500;
        transition: color 0.15s ease;
      }

      .link-secondary {
        color: #6b7280;

        &:hover {
          color: white;
        }
      }

      .link-primary {
        color: var(--primary);

        &:hover {
          color: #10b981;
        }
      }
    }

    .auth-footer {
      padding: 1rem;
      background-color: rgba(0, 0, 0, 0.2);
      border-top: 1px solid rgba(42, 63, 85, 0.5);
      text-align: center;
    }

    .trust-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      color: #8dceb9;
      margin-bottom: 0.5rem;

      .material-symbols-outlined {
        font-size: 1.125rem;
      }

      span:last-child {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
      }
    }

    .trust-text {
      font-size: 0.625rem;
      color: #6b7280;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private toastService = inject(ToastService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  isLoading = signal(false);
  showPassword = signal(false);

  loginForm: FormGroup = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    use2FA: [true]
  });

  togglePassword(): void {
    this.showPassword.update(v => !v);
  }

  isFieldInvalid(field: string): boolean {
    const control = this.loginForm.get(field);
    return !!(control?.invalid && (control?.dirty || control?.touched));
  }

  onSubmit(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    const { email, password } = this.loginForm.value;

    this.authService.login({ email, password }).subscribe({
      next: () => {
        this.toastService.success('Welcome back!', 'You have successfully logged in.');
        // Check for redirect URL from session expiry first, then query params
        const sessionRedirect = sessionStorage.getItem('redirectUrl');
        const queryRedirect = this.route.snapshot.queryParams['returnUrl'];
        const returnUrl = sessionRedirect || queryRedirect || '/dashboard';
        // Clear the stored redirect URL
        sessionStorage.removeItem('redirectUrl');
        this.router.navigateByUrl(returnUrl);
      },
      error: (error) => {
        this.isLoading.set(false);
        const message = error.error?.detail || 'Invalid credentials. Please try again.';
        this.toastService.error('Login Failed', message);
      }
    });
  }
}
