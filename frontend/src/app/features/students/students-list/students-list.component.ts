import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../../../core/services/admin.service';
import { StudentDetails } from '../../../core/models/user.models';

@Component({
  selector: 'app-students-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>Students</h1>
          <p class="subtitle">Manage student accounts and track their progress</p>
        </div>
        <div class="header-actions">
          <button class="btn-primary">
            <span class="material-symbols-outlined">person_add</span>
            Add Student
          </button>
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon">
            <span class="material-symbols-outlined">school</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ totalStudents() }}</span>
            <span class="stat-label">Total Students</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon active">
            <span class="material-symbols-outlined">person_check</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ activeStudents() }}</span>
            <span class="stat-label">Active Today</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon premium">
            <span class="material-symbols-outlined">star</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ premiumStudents() }}</span>
            <span class="stat-label">Premium</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon new">
            <span class="material-symbols-outlined">fiber_new</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ newStudents() }}</span>
            <span class="stat-label">New This Week</span>
          </div>
        </div>
      </div>

      <div class="filters-bar">
        <div class="search-box">
          <span class="material-symbols-outlined">search</span>
          <input
            type="text"
            placeholder="Search students..."
            [(ngModel)]="searchQuery"
            (input)="onSearch()"
          />
        </div>
        <div class="filter-group">
          <select [(ngModel)]="selectedGrade" (change)="applyFilters()">
            <option value="">All Grades</option>
            <option value="form1">Form 1</option>
            <option value="form2">Form 2</option>
            <option value="form3">Form 3</option>
            <option value="form4">Form 4</option>
            <option value="form5">Form 5</option>
            <option value="form6">Form 6</option>
          </select>
          <select [(ngModel)]="selectedStatus" (change)="applyFilters()">
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <select [(ngModel)]="selectedSubscription" (change)="applyFilters()">
            <option value="">All Plans</option>
            <option value="free">Free</option>
            <option value="basic">Basic</option>
            <option value="premium">Premium</option>
          </select>
        </div>
      </div>

      <div class="card">
        @if (isLoading()) {
          <div class="loading-state">
            <div class="spinner"></div>
            <p>Loading students...</p>
          </div>
        } @else {
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Grade</th>
                  <th>Subjects</th>
                  <th>Progress</th>
                  <th>Subscription</th>
                  <th>Last Active</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (student of students(); track student.id) {
                  <tr>
                    <td>
                      <div class="student-info">
                        <div class="avatar">{{ getInitials(student) }}</div>
                        <div class="details">
                          <span class="name">{{ student.full_name }}</span>
                          <span class="email">{{ student.email }}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span class="grade-badge">{{ student.grade || 'N/A' }}</span>
                    </td>
                    <td>
                      <div class="subjects-list">
                        @for (subject of student.subjects?.slice(0, 3) || []; track subject) {
                          <span class="subject-tag">{{ subject }}</span>
                        }
                        @if ((student.subjects?.length || 0) > 3) {
                          <span class="more-tag">+{{ (student.subjects?.length || 0) - 3 }}</span>
                        }
                      </div>
                    </td>
                    <td>
                      <div class="progress-cell">
                        <div class="progress-bar">
                          <div class="progress-fill" [style.width.%]="student.accuracy || 0"></div>
                        </div>
                        <span class="progress-text">{{ student.accuracy || 0 }}%</span>
                      </div>
                    </td>
                    <td>
                      <span class="subscription-badge" [class]="student.subscription_tier || 'free'">
                        {{ student.subscription_tier || 'Free' }}
                      </span>
                    </td>
                    <td>
                      <span class="last-active">{{ student.last_active | date:'short' }}</span>
                    </td>
                    <td>
                      <div class="actions">
                        <button class="action-btn" [routerLink]="['/students', student.id]" title="View Details">
                          <span class="material-symbols-outlined">visibility</span>
                        </button>
                        <button class="action-btn" title="Message">
                          <span class="material-symbols-outlined">chat</span>
                        </button>
                        <button class="action-btn" title="More">
                          <span class="material-symbols-outlined">more_vert</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="7">
                      <div class="empty-state">
                        <span class="material-symbols-outlined">school</span>
                        <p>No students found</p>
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          <div class="pagination">
            <span class="page-info">Showing {{ students().length }} of {{ totalStudents() }} students</span>
            <div class="page-controls">
              <button class="page-btn" [disabled]="currentPage() === 1" (click)="previousPage()">
                <span class="material-symbols-outlined">chevron_left</span>
              </button>
              <span class="page-number">{{ currentPage() }}</span>
              <button class="page-btn" [disabled]="!hasMore()" (click)="nextPage()">
                <span class="material-symbols-outlined">chevron_right</span>
              </button>
            </div>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .page-container {
      padding: 1.5rem;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .header-info {
      h1 {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
      }

      .subtitle {
        font-size: 0.875rem;
        color: var(--text-secondary);
      }
    }

    .btn-primary {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: white;
      background-color: var(--primary);
      border: none;
      border-radius: 0.5rem;
      cursor: pointer;
      transition: background-color 0.15s ease;

      &:hover {
        background-color: #005238;
      }
    }

    .stats-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 1.5rem;

      @media (max-width: 1024px) {
        grid-template-columns: repeat(2, 1fr);
      }

      @media (max-width: 640px) {
        grid-template-columns: 1fr;
      }
    }

    .stat-card {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1.25rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: rgba(0, 102, 70, 0.1);
      border-radius: 0.5rem;

      .material-symbols-outlined {
        font-size: 1.5rem;
        color: var(--primary);
      }

      &.active {
        background-color: rgba(16, 185, 129, 0.1);
        .material-symbols-outlined { color: #10b981; }
      }

      &.premium {
        background-color: rgba(245, 158, 11, 0.1);
        .material-symbols-outlined { color: #f59e0b; }
      }

      &.new {
        background-color: rgba(59, 130, 246, 0.1);
        .material-symbols-outlined { color: #3b82f6; }
      }
    }

    .stat-info {
      display: flex;
      flex-direction: column;

      .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
      }

      .stat-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
      }
    }

    .filters-bar {
      display: flex;
      gap: 1rem;
      margin-bottom: 1rem;
      flex-wrap: wrap;
    }

    .search-box {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex: 1;
      min-width: 250px;
      padding: 0.5rem 1rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;

      .material-symbols-outlined {
        color: var(--text-tertiary);
      }

      input {
        flex: 1;
        border: none;
        background: transparent;
        color: var(--text-primary);
        font-size: 0.875rem;

        &::placeholder {
          color: var(--text-tertiary);
        }

        &:focus {
          outline: none;
        }
      }
    }

    .filter-group {
      display: flex;
      gap: 0.5rem;

      select {
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        color: var(--text-primary);
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        cursor: pointer;

        &:focus {
          outline: none;
          border-color: var(--primary);
        }
      }
    }

    .card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;

      .spinner {
        width: 2.5rem;
        height: 2.5rem;
        border: 3px solid var(--border);
        border-top-color: var(--primary);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        margin-bottom: 1rem;
      }

      p {
        color: var(--text-secondary);
      }
    }

    .table-container {
      overflow-x: auto;
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;

      th, td {
        padding: 1rem;
        text-align: left;
        border-bottom: 1px solid var(--border);
      }

      th {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        background-color: var(--background);
      }

      td {
        font-size: 0.875rem;
        color: var(--text-primary);
      }

      tbody tr:hover {
        background-color: var(--hover);
      }
    }

    .student-info {
      display: flex;
      align-items: center;
      gap: 0.75rem;

      .avatar {
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--primary);
        color: white;
        font-size: 0.875rem;
        font-weight: 600;
        border-radius: 50%;
      }

      .details {
        display: flex;
        flex-direction: column;

        .name {
          font-weight: 500;
          color: var(--text-primary);
        }

        .email {
          font-size: 0.75rem;
          color: var(--text-secondary);
        }
      }
    }

    .grade-badge {
      display: inline-flex;
      padding: 0.25rem 0.75rem;
      font-size: 0.75rem;
      font-weight: 500;
      background-color: rgba(59, 130, 246, 0.1);
      color: #3b82f6;
      border-radius: 9999px;
    }

    .subjects-list {
      display: flex;
      flex-wrap: wrap;
      gap: 0.25rem;
    }

    .subject-tag {
      display: inline-flex;
      padding: 0.125rem 0.5rem;
      font-size: 0.625rem;
      font-weight: 500;
      background-color: var(--background);
      color: var(--text-secondary);
      border-radius: 0.25rem;
    }

    .more-tag {
      display: inline-flex;
      padding: 0.125rem 0.5rem;
      font-size: 0.625rem;
      font-weight: 500;
      background-color: var(--primary);
      color: white;
      border-radius: 0.25rem;
    }

    .progress-cell {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .progress-bar {
      flex: 1;
      height: 6px;
      background-color: var(--background);
      border-radius: 3px;
      overflow: hidden;
    }

    .progress-fill {
      height: 100%;
      background-color: var(--primary);
      border-radius: 3px;
      transition: width 0.3s ease;
    }

    .progress-text {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--text-secondary);
      min-width: 35px;
    }

    .subscription-badge {
      display: inline-flex;
      padding: 0.25rem 0.75rem;
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 9999px;
      text-transform: capitalize;

      &.free {
        background-color: var(--background);
        color: var(--text-secondary);
      }

      &.basic {
        background-color: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }

      &.premium {
        background-color: rgba(245, 158, 11, 0.1);
        color: #f59e0b;
      }
    }

    .last-active {
      font-size: 0.75rem;
      color: var(--text-secondary);
    }

    .actions {
      display: flex;
      gap: 0.25rem;
    }

    .action-btn {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      border-radius: 0.375rem;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover {
        background-color: var(--hover);
        color: var(--text-primary);
      }

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 3rem;

      .material-symbols-outlined {
        font-size: 3rem;
        color: var(--text-tertiary);
        margin-bottom: 0.5rem;
      }

      p {
        color: var(--text-secondary);
      }
    }

    .pagination {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      border-top: 1px solid var(--border);
    }

    .page-info {
      font-size: 0.875rem;
      color: var(--text-secondary);
    }

    .page-controls {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .page-btn {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--background);
      border: 1px solid var(--border);
      border-radius: 0.375rem;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover:not(:disabled) {
        background-color: var(--hover);
        color: var(--text-primary);
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }

    .page-number {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-primary);
      padding: 0 0.5rem;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class StudentsListComponent implements OnInit {
  private adminService = inject(AdminService);

  students = signal<StudentDetails[]>([]);
  isLoading = signal(true);
  currentPage = signal(1);
  pageSize = 20;
  hasMore = signal(true);
  totalPages = signal(1);

  totalStudents = signal(0);
  activeStudents = signal(0);
  premiumStudents = signal(0);
  newStudents = signal(0);

  searchQuery = '';
  selectedGrade = '';
  selectedStatus = '';
  selectedSubscription = '';

  ngOnInit(): void {
    this.loadStudents();
    this.loadStats();
  }

  loadStudents(): void {
    this.isLoading.set(true);

    const filters: any = {
      page: this.currentPage(),
      page_size: this.pageSize,
      search: this.searchQuery || undefined,
      grade: this.selectedGrade || undefined,
      subscription_tier: this.selectedSubscription || undefined,
      is_active: this.selectedStatus ? this.selectedStatus === 'active' : undefined
    };

    // Remove undefined values
    Object.keys(filters).forEach(key => filters[key] === undefined && delete filters[key]);

    this.adminService.getStudents(filters).subscribe({
      next: (response) => {
        this.students.set(response.items);
        this.totalStudents.set(response.total);
        this.totalPages.set(response.total_pages || Math.ceil(response.total / this.pageSize));
        this.hasMore.set(this.currentPage() < this.totalPages());
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load students:', err);
        this.students.set([]);
        this.isLoading.set(false);
      }
    });
  }

  loadStats(): void {
    // Load stats from the dedicated students stats endpoint
    this.adminService.getStudentsStats().subscribe({
      next: (stats) => {
        this.totalStudents.set(stats.total_students);
        this.activeStudents.set(stats.active_today);
        this.premiumStudents.set(stats.premium_students);
        this.newStudents.set(stats.new_this_week);
      },
      error: () => {
        // Stats will come from the students list total
        console.warn('Could not load student stats, using list totals');
      }
    });
  }

  getInitials(student: StudentDetails): string {
    if (student.full_name) {
      return student.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    if (student.first_name && student.last_name) {
      return (student.first_name[0] + student.last_name[0]).toUpperCase();
    }
    return (student.email || 'U').slice(0, 2).toUpperCase();
  }

  onSearch(): void {
    this.currentPage.set(1);
    this.applyFilters();
  }

  applyFilters(): void {
    this.currentPage.set(1);
    this.loadStudents();
  }

  previousPage(): void {
    if (this.currentPage() > 1) {
      this.currentPage.update(p => p - 1);
      this.loadStudents();
    }
  }

  nextPage(): void {
    if (this.hasMore()) {
      this.currentPage.update(p => p + 1);
      this.loadStudents();
    }
  }
}
