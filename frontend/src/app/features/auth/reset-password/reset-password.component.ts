import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-reset-password',
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
            @if (!resetSuccess()) {
              <h1>Create New Password</h1>
              <p>Enter your new password below</p>
            } @else {
              <div class="success-icon">
                <span class="material-symbols-outlined">check_circle</span>
              </div>
              <h1>Password Reset Successfully</h1>
              <p>You can now login with your new password</p>
            }
          </div>
        </div>

        @if (!resetSuccess()) {
          <form class="auth-form" [formGroup]="resetForm" (ngSubmit)="onSubmit()">
            <div class="form-group">
              <label for="password">New Password</label>
              <div class="input-wrapper">
                <input
                  id="password"
                  [type]="showPassword() ? 'text' : 'password'"
                  formControlName="password"
                  placeholder="Enter new password"
                  [class.error]="isFieldInvalid('password')"
                />
                <button type="button" class="toggle-password" (click)="togglePassword()">
                  <span class="material-symbols-outlined">
                    {{ showPassword() ? 'visibility_off' : 'visibility' }}
                  </span>
                </button>
              </div>
              @if (isFieldInvalid('password')) {
                <span class="error-message">Password must be at least 8 characters</span>
              }
            </div>

            <div class="form-group">
              <label for="confirmPassword">Confirm Password</label>
              <div class="input-wrapper">
                <input
                  id="confirmPassword"
                  [type]="showConfirmPassword() ? 'text' : 'password'"
                  formControlName="confirmPassword"
                  placeholder="Confirm new password"
                  [class.error]="isFieldInvalid('confirmPassword') || passwordMismatch()"
                />
                <button type="button" class="toggle-password" (click)="toggleConfirmPassword()">
                  <span class="material-symbols-outlined">
                    {{ showConfirmPassword() ? 'visibility_off' : 'visibility' }}
                  </span>
                </button>
              </div>
              @if (passwordMismatch()) {
                <span class="error-message">Passwords do not match</span>
              }
            </div>

            <div class="password-requirements">
              <p class="requirements-title">Password must contain:</p>
              <ul>
                <li [class.valid]="hasMinLength()">
                  <span class="material-symbols-outlined">{{ hasMinLength() ? 'check' : 'close' }}</span>
                  At least 8 characters
                </li>
                <li [class.valid]="hasUppercase()">
                  <span class="material-symbols-outlined">{{ hasUppercase() ? 'check' : 'close' }}</span>
                  One uppercase letter
                </li>
                <li [class.valid]="hasNumber()">
                  <span class="material-symbols-outlined">{{ hasNumber() ? 'check' : 'close' }}</span>
                  One number
                </li>
              </ul>
            </div>

            <div class="form-actions">
              <button type="submit" class="btn-submit" [disabled]="isLoading()">
                @if (isLoading()) {
                  <span class="spinner"></span>
                  <span>Resetting...</span>
                } @else {
                  <span>Reset Password</span>
                }
              </button>
            </div>
          </form>
        } @else {
          <div class="success-content">
            <div class="form-actions">
              <a routerLink="/auth/login" class="btn-submit">
                Go to Login
              </a>
            </div>
          </div>
        }

        <div class="auth-footer">
          <div class="trust-badge">
            <span class="material-symbols-outlined">lock</span>
            <span>Secure Reset</span>
          </div>
          <p class="trust-text">Your password is encrypted and secure</p>
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

    .toggle-password {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 1rem;
      background-color: #1A2B3C;
      border: 1px solid #2A3F55;
      border-left: none;
      border-radius: 0 0.5rem 0.5rem 0;
      color: #6b7280;
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

    .password-requirements {
      background-color: rgba(0, 102, 70, 0.1);
      border-radius: 0.5rem;
      padding: 1rem;

      .requirements-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: #8dceb9;
        margin-bottom: 0.5rem;
      }

      ul {
        list-style: none;
        padding: 0;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
      }

      li {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.75rem;
        color: #6b7280;

        .material-symbols-outlined {
          font-size: 1rem;
        }

        &.valid {
          color: var(--primary);
        }
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
      text-decoration: none;

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
export class ResetPasswordComponent implements OnInit {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private authService = inject(AuthService);
  private toastService = inject(ToastService);

  isLoading = signal(false);
  resetSuccess = signal(false);
  showPassword = signal(false);
  showConfirmPassword = signal(false);
  token = signal('');

  resetForm: FormGroup = this.fb.group({
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', [Validators.required]]
  });

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (!token) {
      this.toastService.error('Invalid reset link');
      this.router.navigate(['/auth/forgot-password']);
      return;
    }
    this.token.set(token);
  }

  isFieldInvalid(field: string): boolean {
    const control = this.resetForm.get(field);
    return !!(control?.invalid && (control?.dirty || control?.touched));
  }

  passwordMismatch(): boolean {
    const password = this.resetForm.get('password')?.value;
    const confirmPassword = this.resetForm.get('confirmPassword')?.value;
    return confirmPassword && password !== confirmPassword;
  }

  hasMinLength(): boolean {
    return (this.resetForm.get('password')?.value?.length || 0) >= 8;
  }

  hasUppercase(): boolean {
    return /[A-Z]/.test(this.resetForm.get('password')?.value || '');
  }

  hasNumber(): boolean {
    return /[0-9]/.test(this.resetForm.get('password')?.value || '');
  }

  togglePassword(): void {
    this.showPassword.update(v => !v);
  }

  toggleConfirmPassword(): void {
    this.showConfirmPassword.update(v => !v);
  }

  onSubmit(): void {
    if (this.resetForm.invalid || this.passwordMismatch()) {
      this.resetForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    const { password } = this.resetForm.value;

    this.authService.resetPassword({ token: this.token(), new_password: password }).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.resetSuccess.set(true);
        this.toastService.success('Password reset successfully');
      },
      error: (error) => {
        this.isLoading.set(false);
        this.toastService.error(error.message || 'Failed to reset password');
      }
    });
  }
}
