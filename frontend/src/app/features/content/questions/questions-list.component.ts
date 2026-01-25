import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ContentService } from '../../../core/services/content.service';
import { ToastService } from '../../../core/services/toast.service';
import { DifficultyLevel } from '../../../core/models';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';

interface Question {
  id: string;
  content: string;
  subject: string;
  topic: string;
  difficulty: 'easy' | 'medium' | 'hard';
  education_level: string;
  grade: string;
  type: 'multiple_choice' | 'true_false' | 'short_answer' | 'essay';
  options?: string[];
  correct_answer: string;
  explanation?: string;
  is_flagged: boolean;
  flag_reason?: string;
  usage_count: number;
  accuracy_rate: number;
  created_at: string;
  updated_at: string;
}

@Component({
  selector: 'app-questions-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    PageHeaderComponent,
    LoadingSpinnerComponent,
    ConfirmDialogComponent
  ],
  template: `
    <div class="questions-page">
      <app-page-header
        title="Question Bank"
        description="Manage questions for AI tutoring, quizzes, and competitions across all subjects."
        [breadcrumbs]="[
          { label: 'Home', link: '/dashboard' },
          { label: 'Content' },
          { label: 'Questions' }
        ]"
      >
        <div headerActions>
          <button class="btn btn-secondary" (click)="bulkImport()">
            <span class="material-symbols-outlined">upload</span>
            Bulk Import
          </button>
          <button class="btn btn-primary" (click)="openAddQuestion()">
            <span class="material-symbols-outlined">add</span>
            Add Question
          </button>
        </div>
      </app-page-header>

      <!-- Stats Row -->
      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-value">{{ totalQuestions() | number }}</span>
          <span class="stat-label">Total Questions</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ flaggedCount() }}</span>
          <span class="stat-label">Flagged</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ subjects().length }}</span>
          <span class="stat-label">Subjects</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ avgAccuracy() }}%</span>
          <span class="stat-label">Avg. Accuracy</span>
        </div>
      </div>

      <!-- Filters -->
      <div class="filters-card">
        <div class="filters-row">
          <div class="search-input">
            <span class="material-symbols-outlined">search</span>
            <input
              type="text"
              placeholder="Search questions..."
              [(ngModel)]="searchQuery"
              (input)="onSearchChange()"
            />
          </div>

          <div class="select-wrapper">
            <select [(ngModel)]="selectedSubject" (change)="applyFilters()">
              <option value="">All Subjects</option>
              @for (subject of subjects(); track subject) {
                <option [value]="subject">{{ subject }}</option>
              }
            </select>
            <span class="material-symbols-outlined">expand_more</span>
          </div>

          <div class="select-wrapper">
            <select [(ngModel)]="selectedDifficulty" (change)="applyFilters()">
              <option value="">All Difficulties</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
            <span class="material-symbols-outlined">expand_more</span>
          </div>

          <div class="select-wrapper">
            <select [(ngModel)]="selectedType" (change)="applyFilters()">
              <option value="">All Types</option>
              <option value="multiple_choice">Multiple Choice</option>
              <option value="true_false">True/False</option>
              <option value="short_answer">Short Answer</option>
              <option value="essay">Essay</option>
            </select>
            <span class="material-symbols-outlined">expand_more</span>
          </div>

          <label class="checkbox-filter">
            <input type="checkbox" [(ngModel)]="showFlagged" (change)="applyFilters()" />
            <span>Flagged Only</span>
          </label>
        </div>
      </div>

      <!-- Questions Grid -->
      @if (loading()) {
        <app-loading-spinner message="Loading questions..." />
      } @else {
        <div class="questions-grid">
          @for (question of questions(); track question.id) {
            <div class="question-card" [class.flagged]="question.is_flagged">
              <div class="question-header">
                <div class="question-badges">
                  <span class="badge subject">{{ question.subject }}</span>
                  <span class="badge difficulty" [class]="question.difficulty">
                    {{ question.difficulty | titlecase }}
                  </span>
                  <span class="badge type">{{ formatType(question.type) }}</span>
                </div>
                @if (question.is_flagged) {
                  <span class="flag-indicator" [title]="question.flag_reason">
                    <span class="material-symbols-outlined">flag</span>
                  </span>
                }
              </div>

              <div class="question-content">
                <p>{{ question.content }}</p>
              </div>

              @if (question.type === 'multiple_choice' && question.options) {
                <div class="question-options">
                  @for (option of question.options; track $index; let i = $index) {
                    <div class="option" [class.correct]="option === question.correct_answer">
                      <span class="option-letter">{{ getOptionLetter(i) }}</span>
                      <span class="option-text">{{ option }}</span>
                      @if (option === question.correct_answer) {
                        <span class="material-symbols-outlined correct-icon">check_circle</span>
                      }
                    </div>
                  }
                </div>
              }

              <div class="question-meta">
                <div class="meta-item">
                  <span class="material-symbols-outlined">school</span>
                  <span>{{ question.education_level }} - {{ question.grade }}</span>
                </div>
                <div class="meta-item">
                  <span class="material-symbols-outlined">analytics</span>
                  <span>{{ question.accuracy_rate }}% accuracy</span>
                </div>
                <div class="meta-item">
                  <span class="material-symbols-outlined">visibility</span>
                  <span>{{ question.usage_count }} uses</span>
                </div>
              </div>

              <div class="question-actions">
                <button class="action-btn" title="Edit" (click)="editQuestion(question)">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="action-btn" title="Preview" (click)="previewQuestion(question)">
                  <span class="material-symbols-outlined">visibility</span>
                </button>
                <button
                  class="action-btn"
                  [title]="question.is_flagged ? 'Unflag' : 'Flag'"
                  (click)="toggleFlag(question)"
                >
                  <span class="material-symbols-outlined">
                    {{ question.is_flagged ? 'flag_off' : 'flag' }}
                  </span>
                </button>
                <button class="action-btn danger" title="Delete" (click)="confirmDelete(question)">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </div>
            </div>
          } @empty {
            <div class="empty-state">
              <span class="material-symbols-outlined">quiz</span>
              <p class="empty-title">No questions found</p>
              <p class="empty-desc">Try adjusting your filters or add a new question</p>
              <button class="btn btn-primary" (click)="openAddQuestion()">
                <span class="material-symbols-outlined">add</span>
                Add Question
              </button>
            </div>
          }
        </div>

        <!-- Pagination -->
        @if (questions().length > 0) {
          <div class="pagination-bar">
            <span class="pagination-info">
              Showing {{ paginationStart() }}-{{ paginationEnd() }} of {{ totalQuestions() }}
            </span>
            <div class="pagination-controls">
              <button
                class="pagination-btn"
                [disabled]="currentPage() === 1"
                (click)="goToPage(currentPage() - 1)"
              >
                <span class="material-symbols-outlined">chevron_left</span>
              </button>
              @for (page of visiblePages(); track page) {
                <button
                  class="pagination-btn"
                  [class.active]="page === currentPage()"
                  (click)="goToPage(page)"
                >
                  {{ page }}
                </button>
              }
              <button
                class="pagination-btn"
                [disabled]="currentPage() >= totalPages()"
                (click)="goToPage(currentPage() + 1)"
              >
                <span class="material-symbols-outlined">chevron_right</span>
              </button>
            </div>
          </div>
        }
      }

      <!-- Confirm Delete Dialog -->
      <app-confirm-dialog
        [isOpen]="showDeleteDialog()"
        title="Delete Question"
        message="Are you sure you want to delete this question? This action cannot be undone."
        type="danger"
        confirmText="Delete"
        (confirm)="deleteQuestion()"
        (cancel)="closeDeleteDialog()"
      />
    </div>
  `,
  styles: [`
    .questions-page {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .stats-row {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }

    .stat-item {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      padding: 1rem 1.5rem;
      display: flex;
      flex-direction: column;
      min-width: 140px;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text-primary);
    }

    .stat-label {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .filters-card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1rem;
    }

    .filters-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
    }

    .search-input {
      position: relative;
      flex: 1;
      min-width: 250px;

      .material-symbols-outlined {
        position: absolute;
        left: 0.75rem;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text-muted);
      }

      input {
        width: 100%;
        padding: 0.625rem 1rem 0.625rem 2.5rem;
        background-color: var(--background);
        border: 1px solid transparent;
        border-radius: 0.5rem;
        font-size: 0.875rem;

        &:focus {
          border-color: var(--primary);
        }
      }
    }

    .select-wrapper {
      position: relative;

      select {
        padding: 0.625rem 2rem 0.625rem 0.75rem;
        background-color: var(--background);
        border: 1px solid transparent;
        border-radius: 0.5rem;
        font-size: 0.875rem;
        appearance: none;
        cursor: pointer;
        min-width: 140px;

        &:focus {
          border-color: var(--primary);
        }
      }

      .material-symbols-outlined {
        position: absolute;
        right: 0.5rem;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text-muted);
        pointer-events: none;
      }
    }

    .checkbox-filter {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      color: var(--text-secondary);
      cursor: pointer;

      input {
        accent-color: var(--primary);
      }
    }

    .questions-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
      gap: 1rem;
    }

    .question-card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      transition: all 0.2s ease;

      &:hover {
        border-color: var(--primary);
        box-shadow: var(--shadow-md);
      }

      &.flagged {
        border-color: var(--warning);
        background-color: rgba(245, 158, 11, 0.02);
      }
    }

    .question-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .question-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .badge {
      padding: 0.25rem 0.5rem;
      font-size: 0.625rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-radius: 0.25rem;

      &.subject {
        background-color: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }

      &.difficulty {
        &.easy {
          background-color: rgba(16, 185, 129, 0.1);
          color: #10b981;
        }

        &.medium {
          background-color: rgba(245, 158, 11, 0.1);
          color: #f59e0b;
        }

        &.hard {
          background-color: rgba(239, 68, 68, 0.1);
          color: #ef4444;
        }
      }

      &.type {
        background-color: var(--background);
        color: var(--text-secondary);
      }
    }

    .flag-indicator {
      color: var(--warning);

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .question-content {
      p {
        font-size: 0.9375rem;
        color: var(--text-primary);
        line-height: 1.5;
      }
    }

    .question-options {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .option {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 0.75rem;
      background-color: var(--background);
      border-radius: 0.375rem;
      font-size: 0.875rem;

      &.correct {
        background-color: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.2);
      }
    }

    .option-letter {
      width: 1.5rem;
      height: 1.5rem;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--surface);
      border-radius: 50%;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-muted);
    }

    .option-text {
      flex: 1;
      color: var(--text-primary);
    }

    .correct-icon {
      color: var(--success);
      font-size: 1rem;
    }

    .question-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      padding-top: 0.5rem;
      border-top: 1px solid var(--border);
    }

    .meta-item {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      font-size: 0.75rem;
      color: var(--text-muted);

      .material-symbols-outlined {
        font-size: 1rem;
      }
    }

    .question-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.25rem;
      padding-top: 0.5rem;
    }

    .action-btn {
      padding: 0.5rem;
      border-radius: 0.375rem;
      background: transparent;
      color: var(--text-muted);
      transition: all 0.15s ease;

      &:hover {
        background-color: var(--background);
        color: var(--text-primary);
      }

      &.danger:hover {
        background-color: rgba(239, 68, 68, 0.1);
        color: var(--error);
      }

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .empty-state {
      grid-column: 1 / -1;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 4rem 2rem;
      background-color: var(--surface);
      border: 1px dashed var(--border);
      border-radius: 0.75rem;
      text-align: center;

      .material-symbols-outlined {
        font-size: 4rem;
        color: var(--text-muted);
        margin-bottom: 1rem;
      }

      .empty-title {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
      }

      .empty-desc {
        font-size: 0.875rem;
        color: var(--text-muted);
        margin-bottom: 1.5rem;
      }
    }

    .pagination-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
    }

    .pagination-info {
      font-size: 0.875rem;
      color: var(--text-muted);
    }

    .pagination-controls {
      display: flex;
      gap: 0.25rem;
    }

    .pagination-btn {
      min-width: 2rem;
      height: 2rem;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 0.375rem;
      background: transparent;
      color: var(--text-secondary);
      font-size: 0.875rem;
      transition: all 0.15s ease;

      &:hover:not(:disabled) {
        background-color: var(--background);
        color: var(--text-primary);
      }

      &.active {
        background-color: var(--primary);
        color: white;
      }

      &:disabled {
        color: var(--text-muted);
        cursor: not-allowed;
      }
    }
  `]
})
export class QuestionsListComponent implements OnInit {
  private contentService = inject(ContentService);
  private toastService = inject(ToastService);

  // State
  loading = signal(true);
  questions = signal<Question[]>([]);
  totalQuestions = signal(0);
  currentPage = signal(1);
  pageSize = 12;

  // Filters
  searchQuery = '';
  selectedSubject = '';
  selectedDifficulty = '';
  selectedType = '';
  showFlagged = false;

  // Dialog
  showDeleteDialog = signal(false);
  questionToDelete = signal<Question | null>(null);

  // Computed
  subjects = signal(['Mathematics', 'Science', 'English', 'History', 'Geography', 'Commerce']);
  flaggedCount = signal(3);
  avgAccuracy = signal(76);

  totalPages = computed(() => Math.ceil(this.totalQuestions() / this.pageSize));
  paginationStart = computed(() => (this.currentPage() - 1) * this.pageSize + 1);
  paginationEnd = computed(() => Math.min(this.currentPage() * this.pageSize, this.totalQuestions()));

  visiblePages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: number[] = [];

    let start = Math.max(1, current - 2);
    const end = Math.min(total, start + 4);

    if (end - start < 4) {
      start = Math.max(1, end - 4);
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    return pages;
  });

  private searchTimeout: any;

  ngOnInit(): void {
    this.loadQuestions();
  }

  loadQuestions(): void {
    this.loading.set(true);
    const filters = {
      page: this.currentPage(),
      page_size: this.pageSize,
      subject: this.selectedSubject || undefined,
      difficulty: (this.selectedDifficulty || undefined) as DifficultyLevel | undefined,
      is_flagged: this.showFlagged ? true : undefined,
      search: this.searchQuery || undefined
    };

    this.contentService.getQuestions(filters).subscribe({
      next: (response) => {
        if (response && response.items && Array.isArray(response.items)) {
          this.questions.set(response.items as Question[]);
          this.totalQuestions.set(response.total || 0);
        } else {
          this.setMockQuestions();
        }
        this.loading.set(false);
      },
      error: () => {
        this.setMockQuestions();
        this.loading.set(false);
      }
    });
  }

  setMockQuestions(): void {
    this.questions.set([
      { id: 'q_001', content: 'What is the chemical formula for water?', subject: 'Science', topic: 'Chemistry', difficulty: 'easy', education_level: 'Secondary', grade: 'Form 1', type: 'multiple_choice', options: ['H2O', 'CO2', 'NaCl', 'O2'], correct_answer: 'H2O', explanation: 'Water is composed of two hydrogen atoms and one oxygen atom.', is_flagged: false, usage_count: 1250, accuracy_rate: 92, created_at: '2024-01-15', updated_at: '2024-01-15' },
      { id: 'q_002', content: 'Solve for x: 2x + 5 = 15', subject: 'Mathematics', topic: 'Algebra', difficulty: 'medium', education_level: 'Secondary', grade: 'Form 2', type: 'short_answer', correct_answer: '5', explanation: '2x + 5 = 15, 2x = 10, x = 5', is_flagged: true, flag_reason: 'Answer format needs clarification', usage_count: 890, accuracy_rate: 78, created_at: '2024-01-10', updated_at: '2024-01-20' },
      { id: 'q_003', content: 'The Great Zimbabwe was built by which civilization?', subject: 'History', topic: 'African History', difficulty: 'medium', education_level: 'Secondary', grade: 'Form 3', type: 'multiple_choice', options: ['Shona civilization', 'Zulu Kingdom', 'Egyptian Empire', 'Bantu migration'], correct_answer: 'Shona civilization', is_flagged: false, usage_count: 560, accuracy_rate: 65, created_at: '2024-01-08', updated_at: '2024-01-08' },
      { id: 'q_004', content: 'The Earth revolves around the Sun.', subject: 'Science', topic: 'Astronomy', difficulty: 'easy', education_level: 'Primary', grade: 'Grade 6', type: 'true_false', correct_answer: 'True', is_flagged: false, usage_count: 2100, accuracy_rate: 95, created_at: '2024-01-05', updated_at: '2024-01-05' }
    ]);
    this.totalQuestions.set(4);
  }

  onSearchChange(): void {
    clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => this.applyFilters(), 300);
  }

  applyFilters(): void {
    this.currentPage.set(1);
    this.loadQuestions();
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
      this.loadQuestions();
    }
  }

  getOptionLetter(index: number): string {
    return String.fromCharCode(65 + index);
  }

  formatType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  openAddQuestion(): void {
    this.toastService.info('Coming Soon', 'Question editor will be implemented');
  }

  bulkImport(): void {
    this.toastService.info('Coming Soon', 'Bulk import will be implemented');
  }

  editQuestion(question: Question): void {
    this.toastService.info('Edit Question', `Editing question ${question.id}`);
  }

  previewQuestion(question: Question): void {
    this.toastService.info('Preview', `Previewing question ${question.id}`);
  }

  toggleFlag(question: Question): void {
    question.is_flagged = !question.is_flagged;
    this.toastService.success(
      question.is_flagged ? 'Question Flagged' : 'Flag Removed',
      question.is_flagged ? 'Question has been flagged for review' : 'Flag has been removed'
    );
  }

  confirmDelete(question: Question): void {
    this.questionToDelete.set(question);
    this.showDeleteDialog.set(true);
  }

  deleteQuestion(): void {
    const question = this.questionToDelete();
    if (question) {
      this.toastService.success('Question Deleted', 'Question has been permanently removed');
      this.questions.update(qs => qs.filter(q => q.id !== question.id));
    }
    this.closeDeleteDialog();
  }

  closeDeleteDialog(): void {
    this.showDeleteDialog.set(false);
    this.questionToDelete.set(null);
  }
}
