import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Subject, SubjectCreate, SubjectUpdate } from '../../../core/models';

@Component({
  selector: 'app-subject-form-modal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()" class="subject-form">
      <div class="form-grid">
        <div class="form-group">
          <label for="name">Subject Name <span class="required">*</span></label>
          <input
            id="name"
            type="text"
            formControlName="name"
            class="form-control"
            placeholder="e.g., Mathematics"
            [class.error]="form.get('name')?.invalid && form.get('name')?.touched"
          />
          @if (form.get('name')?.invalid && form.get('name')?.touched) {
            <span class="error-text">
              @if (form.get('name')?.errors?.['required']) {
                Name is required
              } @else if (form.get('name')?.errors?.['minlength']) {
                Name must be at least 2 characters
              } @else if (form.get('name')?.errors?.['maxlength']) {
                Name cannot exceed 100 characters
              }
            </span>
          }
        </div>

        <div class="form-group">
          <label for="code">Subject Code <span class="required">*</span></label>
          <input
            id="code"
            type="text"
            formControlName="code"
            class="form-control"
            placeholder="e.g., MATH-O-001"
            [class.error]="form.get('code')?.invalid && form.get('code')?.touched"
          />
          @if (form.get('code')?.invalid && form.get('code')?.touched) {
            <span class="error-text">
              @if (form.get('code')?.errors?.['required']) {
                Code is required
              } @else if (form.get('code')?.errors?.['pattern']) {
                Code must be uppercase letters, numbers, and hyphens only
              }
            </span>
          }
        </div>
      </div>

      <div class="form-group">
        <label for="education_level">Education Level <span class="required">*</span></label>
        <select
          id="education_level"
          formControlName="education_level"
          class="form-control"
          [class.error]="form.get('education_level')?.invalid && form.get('education_level')?.touched"
        >
          <option value="">Select level...</option>
          <option value="primary">Primary</option>
          <option value="secondary">Secondary</option>
          <option value="o_level">O Level</option>
          <option value="a_level">A Level</option>
        </select>
        @if (form.get('education_level')?.invalid && form.get('education_level')?.touched) {
          <span class="error-text">Education level is required</span>
        }
      </div>

      <div class="form-group">
        <label for="description">Description</label>
        <textarea
          id="description"
          formControlName="description"
          class="form-control"
          rows="3"
          placeholder="Brief description of the subject..."
        ></textarea>
      </div>

      <div class="form-grid">
        <div class="form-group">
          <label for="icon">Icon</label>
          <div class="icon-input-wrapper">
            <span class="material-symbols-outlined icon-preview">{{ form.get('icon')?.value || 'menu_book' }}</span>
            <input
              id="icon"
              type="text"
              formControlName="icon"
              class="form-control"
              placeholder="e.g., calculate"
            />
          </div>
          <span class="hint-text">Material Symbols icon name</span>
        </div>

        <div class="form-group">
          <label for="color">Color</label>
          <div class="color-input-wrapper">
            <input
              id="color"
              type="color"
              formControlName="color"
              class="color-picker"
            />
            <input
              type="text"
              [value]="form.get('color')?.value"
              (input)="onColorTextChange($event)"
              class="form-control color-text"
              placeholder="#3b82f6"
            />
          </div>
        </div>
      </div>

      @if (subject) {
        <div class="form-group">
          <label class="checkbox-wrapper">
            <input type="checkbox" formControlName="is_active" />
            <span class="checkbox-label">Active</span>
          </label>
          <span class="hint-text">Inactive subjects won't be visible to students</span>
        </div>
      }

      <div class="form-actions">
        <button type="button" class="btn btn-secondary" (click)="onCancel()">
          Cancel
        </button>
        <button type="submit" class="btn btn-primary" [disabled]="form.invalid || isSubmitting">
          @if (isSubmitting) {
            <span class="spinner"></span>
          }
          {{ subject ? 'Update' : 'Create' }} Subject
        </button>
      </div>
    </form>
  `,
  styles: [`
    .subject-form {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;

      @media (max-width: 640px) {
        grid-template-columns: 1fr;
      }
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
    }

    label {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-primary);
    }

    .required {
      color: var(--error);
    }

    .form-control {
      width: 100%;
      padding: 0.625rem 0.875rem;
      font-size: 0.875rem;
      color: var(--text-primary);
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;

      &:focus {
        outline: none;
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(0, 102, 70, 0.1);
      }

      &.error {
        border-color: var(--error);

        &:focus {
          box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
        }
      }

      &::placeholder {
        color: var(--text-muted);
      }
    }

    textarea.form-control {
      resize: vertical;
      min-height: 80px;
    }

    select.form-control {
      cursor: pointer;
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 0.75rem center;
      padding-right: 2.5rem;
    }

    .error-text {
      font-size: 0.75rem;
      color: var(--error);
    }

    .hint-text {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .icon-input-wrapper {
      display: flex;
      align-items: center;
      gap: 0.5rem;

      .icon-preview {
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--background);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        font-size: 1.25rem;
        color: var(--primary);
      }

      .form-control {
        flex: 1;
      }
    }

    .color-input-wrapper {
      display: flex;
      align-items: center;
      gap: 0.5rem;

      .color-picker {
        width: 40px;
        height: 40px;
        padding: 0;
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        cursor: pointer;
        overflow: hidden;

        &::-webkit-color-swatch-wrapper {
          padding: 0;
        }

        &::-webkit-color-swatch {
          border: none;
          border-radius: 0.375rem;
        }
      }

      .color-text {
        flex: 1;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
      }
    }

    .checkbox-wrapper {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;

      input[type="checkbox"] {
        width: 1.125rem;
        height: 1.125rem;
        accent-color: var(--primary);
        cursor: pointer;
      }

      .checkbox-label {
        font-weight: 400;
      }
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
      margin-top: 0.5rem;
      padding-top: 1.25rem;
      border-top: 1px solid var(--border);
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 0.625rem 1.25rem;
      font-size: 0.875rem;
      font-weight: 600;
      border-radius: 0.5rem;
      cursor: pointer;
      transition: all 0.15s ease;

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }

    .btn-primary {
      background-color: var(--primary);
      color: white;
      border: none;

      &:hover:not(:disabled) {
        background-color: var(--primary-dark);
      }
    }

    .btn-secondary {
      background-color: var(--surface);
      color: var(--text-primary);
      border: 1px solid var(--border);

      &:hover:not(:disabled) {
        background-color: var(--background);
      }
    }

    .spinner {
      width: 1rem;
      height: 1rem;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class SubjectFormModalComponent implements OnChanges {
  private fb = inject(FormBuilder);

  @Input() subject: Subject | null = null;
  @Input() isSubmitting = false;
  @Output() submitForm = new EventEmitter<SubjectCreate | SubjectUpdate>();
  @Output() cancel = new EventEmitter<void>();

  form: FormGroup = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    code: ['', [Validators.required, Validators.pattern(/^[A-Z0-9\-]+$/)]],
    education_level: ['', Validators.required],
    description: [''],
    icon: ['menu_book'],
    color: ['#3b82f6'],
    is_active: [true]
  });

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['subject']) {
      if (this.subject) {
        this.form.patchValue({
          name: this.subject.name,
          code: this.subject.code,
          education_level: this.subject.education_level || '',
          description: this.subject.description || '',
          icon: this.subject.icon || 'menu_book',
          color: this.subject.color || '#3b82f6',
          is_active: this.subject.is_active
        });
      } else {
        this.form.reset({
          name: '',
          code: '',
          education_level: '',
          description: '',
          icon: 'menu_book',
          color: '#3b82f6',
          is_active: true
        });
      }
    }
  }

  onColorTextChange(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
      this.form.patchValue({ color: value });
    }
  }

  onSubmit(): void {
    if (this.form.valid) {
      const value = { ...this.form.value };
      // Transform code to uppercase
      value.code = value.code.toUpperCase();

      // Remove is_active for create (it defaults to true on backend)
      if (!this.subject) {
        delete value.is_active;
      }

      this.submitForm.emit(value);
    } else {
      // Mark all fields as touched to show errors
      Object.keys(this.form.controls).forEach(key => {
        this.form.get(key)?.markAsTouched();
      });
    }
  }

  onCancel(): void {
    this.cancel.emit();
  }
}
