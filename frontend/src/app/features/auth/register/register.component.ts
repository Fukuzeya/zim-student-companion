import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-register',
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
            <h1>Create Admin Account</h1>
            <p>Register to access the admin portal</p>
          </div>
        </div>

        <form class="auth-form" [formGroup]="registerForm" (ngSubmit)="onSubmit()">
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

          <div class="form-group">
            <label for="phone">Phone Number</label>
            <div class="input-wrapper">
              <input
                id="phone"
                type="tel"
                formControlName="phone_number"
                placeholder="+263 77 123 4567"
                [class.error]="isFieldInvalid('phone_number')"
              />
              <span class="material-symbols-outlined input-icon">phone</span>
            </div>
            @if (isFieldInvalid('phone_number')) {
              <span class="error-message">Please enter a valid phone number</span>
            }
          </div>

          <div class="form-group">
            <label for="password">Password</label>
            <div class="input-wrapper">
              <input
                id="password"
                [type]="showPassword() ? 'text' : 'password'"
                formControlName="password"
                placeholder="••••••••••••"
                [class.error]="isFieldInvalid('password')"
              />
              <button type="button" class="toggle-password" (click)="togglePassword()">
                <span class="material-symbols-outlined">
                  {{ showPassword() ? 'visibility' : 'visibility_off' }}
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
                placeholder="••••••••••••"
                [class.error]="isFieldInvalid('confirmPassword') || passwordMismatch()"
              />
              <button type="button" class="toggle-password" (click)="toggleConfirmPassword()">
                <span class="material-symbols-outlined">
                  {{ showConfirmPassword() ? 'visibility' : 'visibility_off' }}
                </span>
              </button>
            </div>
            @if (passwordMismatch()) {
              <span class="error-message">Passwords do not match</span>
            }
          </div>

          <div class="toggle-group">
            <div class="toggle-info">
              <p class="toggle-label">I agree to the Terms of Service</p>
              <p class="toggle-hint">Required to create an account</p>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" formControlName="agreeTerms" />
              <span class="toggle-slider"></span>
            </label>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-submit" [disabled]="isLoading()">
              @if (isLoading()) {
                <span class="spinner"></span>
                <span>Creating Account...</span>
              } @else {
                <span>Create Account</span>
              }
            </button>
          </div>

          <div class="auth-links">
            <span class="text-muted">Already have an account?</span>
            <a routerLink="/auth/login" class="link-primary">Sign In</a>
          </div>
        </form>

        <div class="auth-footer">
          <div class="trust-badge">
            <span class="material-symbols-outlined">lock</span>
            <span>Secure Environment</span>
          </div>
          <p class="trust-text">Your data is protected with bank-grade encryption</p>
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
      padding: 2rem 2rem 1.5rem;
      border-bottom: 1px solid rgba(42, 63, 85, 0.5);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1.5rem;

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
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.25rem;
      }

      p {
        font-size: 0.875rem;
        color: #8dceb9;
      }
    }

    .auth-form {
      padding: 1.5rem 2rem 2rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
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
      &:hover { color: white; }
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
      justify-content: center;
      gap: 0.5rem;
      font-size: 0.875rem;

      .text-muted { color: #6b7280; }
      .link-primary {
        color: var(--primary);
        font-weight: 500;
        &:hover { color: #10b981; }
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

      .material-symbols-outlined { font-size: 1.125rem; }
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
export class RegisterComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private toastService = inject(ToastService);
  private router = inject(Router);

  isLoading = signal(false);
  showPassword = signal(false);
  showConfirmPassword = signal(false);

  registerForm: FormGroup = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    phone_number: ['', [Validators.required]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', [Validators.required]],
    agreeTerms: [false, [Validators.requiredTrue]]
  });

  togglePassword(): void {
    this.showPassword.update(v => !v);
  }

  toggleConfirmPassword(): void {
    this.showConfirmPassword.update(v => !v);
  }

  isFieldInvalid(field: string): boolean {
    const control = this.registerForm.get(field);
    return !!(control?.invalid && (control?.dirty || control?.touched));
  }

  passwordMismatch(): boolean {
    const password = this.registerForm.get('password')?.value;
    const confirmPassword = this.registerForm.get('confirmPassword')?.value;
    return confirmPassword && password !== confirmPassword;
  }

  onSubmit(): void {
    if (this.registerForm.invalid || this.passwordMismatch()) {
      this.registerForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    const { email, phone_number, password } = this.registerForm.value;

    this.authService.register({ email, phone_number, password }).subscribe({
      next: () => {
        this.toastService.success('Account Created!', 'Please check your email to verify your account.');
        this.router.navigate(['/dashboard']);
      },
      error: (error) => {
        this.isLoading.set(false);
        const message = error.error?.detail || 'Registration failed. Please try again.';
        this.toastService.error('Registration Failed', message);
      }
    });
  }
}
