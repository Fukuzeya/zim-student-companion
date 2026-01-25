import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  template: `
    <div class="auth-container">
      <div class="background-decoration">
        <div class="decoration-circle primary"></div>
        <div class="decoration-circle secondary"></div>
      </div>

      <div class="auth-card">
        <div class="auth-header">
          <div class="brand">
            <div class="brand-icon">
              <span class="material-symbols-outlined">school</span>
            </div>
            <h2>EduBot Zimbabwe</h2>
          </div>
          <div class="auth-title">
            @if (!emailSent()) {
              <h1>Reset Password</h1>
              <p>Enter your email to receive a password reset link</p>
            } @else {
              <div class="success-icon">
                <span class="material-symbols-outlined">mark_email_read</span>
              </div>
              <h1>Check Your Email</h1>
              <p>We've sent a password reset link to {{ submittedEmail() }}</p>
            }
          </div>
        </div>

        @if (!emailSent()) {
          <form class="auth-form" [formGroup]="forgotForm" (ngSubmit)="onSubmit()">
            <div class="form-group">
              <label for="email">Email Address</label>
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

            <div class="form-actions">
              <button type="submit" class="btn-submit" [disabled]="isLoading()">
                @if (isLoading()) {
                  <span class="spinner"></span>
                  <span>Sending...</span>
                } @else {
                  <span>Send Reset Link</span>
                }
              </button>
            </div>

            <div class="auth-links">
              <a routerLink="/auth/login" class="link-back">
                <span class="material-symbols-outlined">arrow_back</span>
                Back to Login
              </a>
            </div>
          </form>
        } @else {
          <div class="success-content">
            <p class="success-message">
              If an account exists with this email, you will receive a password reset link shortly.
              Please check your spam folder if you don't see it.
            </p>

            <div class="form-actions">
              <button class="btn-submit" (click)="resetForm()">
                Try Another Email
              </button>
            </div>

            <div class="auth-links">
              <a routerLink="/auth/login" class="link-back">
                <span class="material-symbols-outlined">arrow_back</span>
                Back to Login
              </a>
            </div>
          </div>
        }

        <div class="auth-footer">
          <div class="trust-badge">
            <span class="material-symbols-outlined">support_agent</span>
            <span>Need Help?</span>
          </div>
          <p class="trust-text">Contact support at support&#64;edubot.co.zw</p>
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

    .success-icon {
      width: 64px;
      height: 64px;
      background-color: rgba(0, 102, 70, 0.2);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 1rem;

      .material-symbols-outlined {
        font-size: 2rem;
        color: var(--primary);
      }
    }

    .auth-title {
      h1 {
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.5rem;
      }

      p {
        font-size: 0.875rem;
        color: #8dceb9;
      }
    }

    .auth-form, .success-content {
      padding: 2rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .success-message {
      font-size: 0.875rem;
      color: #9ca3af;
      line-height: 1.6;
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

    .input-wrapper {
      display: flex;
      border-radius: 0.5rem;
      overflow: hidden;

      input {
        flex: 1;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        color: white;
        background-color: #1A2B3C;
        border: 1px solid #2A3F55;
        border-right: none;
        border-radius: 0.5rem 0 0 0.5rem;
        transition: border-color 0.15s ease;

        &::placeholder {
          color: #6b7280;
        }

        &:focus {
          outline: none;
          border-color: var(--primary);
        }

        &.error {
          border-color: var(--error);
        }
      }
    }

    .input-icon {
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

    .error-message {
      font-size: 0.75rem;
      color: var(--error);
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
      justify-content: center;
    }

    .link-back {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      color: var(--primary);
      font-size: 0.875rem;
      font-weight: 500;
      transition: color 0.15s ease;

      &:hover {
        color: #10b981;
      }

      .material-symbols-outlined {
        font-size: 1.125rem;
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
export class ForgotPasswordComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private toastService = inject(ToastService);

  isLoading = signal(false);
  emailSent = signal(false);
  submittedEmail = signal('');

  forgotForm: FormGroup = this.fb.group({
    email: ['', [Validators.required, Validators.email]]
  });

  isFieldInvalid(field: string): boolean {
    const control = this.forgotForm.get(field);
    return !!(control?.invalid && (control?.dirty || control?.touched));
  }

  onSubmit(): void {
    if (this.forgotForm.invalid) {
      this.forgotForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    const { email } = this.forgotForm.value;

    this.authService.forgotPassword({ email }).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.submittedEmail.set(email);
        this.emailSent.set(true);
      },
      error: () => {
        this.isLoading.set(false);
        this.submittedEmail.set(email);
        this.emailSent.set(true);
      }
    });
  }

  resetForm(): void {
    this.emailSent.set(false);
    this.submittedEmail.set('');
    this.forgotForm.reset();
  }
}
