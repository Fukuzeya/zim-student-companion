import { Component, inject, signal, computed, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ContentService } from '../../../core/services/content.service';
import { ToastService } from '../../../core/services/toast.service';
import {
  Subject,
  SubjectListParams,
  SubjectStats,
  SubjectCreate,
  SubjectUpdate
} from '../../../core/models';
import { PageHeaderComponent, Breadcrumb } from '../../../shared/components/page-header/page-header.component';
import { StatCardComponent } from '../../../shared/components/stat-card/stat-card.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { SubjectFormModalComponent } from './subject-form-modal.component';

@Component({
  selector: 'app-subjects-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    PageHeaderComponent,
    StatCardComponent,
    ModalComponent,
    ConfirmDialogComponent,
    SubjectFormModalComponent
  ],
  template: `
    <div class="page-container">
      <!-- Page Header -->
      <app-page-header
        title="Subjects"
        description="Manage curriculum subjects, topics, and educational content"
        [breadcrumbs]="breadcrumbs"
      >
        <div headerActions class="header-actions-wrapper">
          <div class="export-dropdown" [class.open]="showExportMenu()">
            <button class="btn btn-secondary" (click)="toggleExportMenu()">
              <span class="material-symbols-outlined">download</span>
              Export
              <span class="material-symbols-outlined chevron">expand_more</span>
            </button>
            @if (showExportMenu()) {
              <div class="dropdown-menu">
                <button (click)="exportSubjects('csv')">
                  <span class="material-symbols-outlined">description</span>
                  Export as CSV
                </button>
                <button (click)="exportSubjects('json')">
                  <span class="material-symbols-outlined">data_object</span>
                  Export as JSON
                </button>
              </div>
            }
          </div>
          <button class="btn btn-primary" (click)="openCreateModal()">
            <span class="material-symbols-outlined">add</span>
            Add Subject
          </button>
        </div>
      </app-page-header>

      <!-- Statistics Row -->
      @if (stats()) {
        <div class="stats-grid">
          <app-stat-card
            label="Total Subjects"
            [value]="stats()!.total_subjects"
            icon="menu_book"
            iconColor="#006646"
            iconBgColor="rgba(0, 102, 70, 0.1)"
          />
          <app-stat-card
            label="Active Subjects"
            [value]="stats()!.active_subjects"
            icon="check_circle"
            iconColor="#10b981"
            iconBgColor="rgba(16, 185, 129, 0.1)"
          />
          <app-stat-card
            label="Total Topics"
            [value]="stats()!.total_topics"
            icon="topic"
            iconColor="#3b82f6"
            iconBgColor="rgba(59, 130, 246, 0.1)"
          />
          <app-stat-card
            label="Total Questions"
            [value]="stats()!.total_questions"
            icon="quiz"
            iconColor="#8b5cf6"
            iconBgColor="rgba(139, 92, 246, 0.1)"
          />
        </div>
      }

      <!-- Bulk Action Bar -->
      @if (hasSelection()) {
        <div class="bulk-action-bar">
          <div class="selection-info">
            <span class="material-symbols-outlined">check_circle</span>
            <span>{{ selectedSubjects().length }} subject(s) selected</span>
          </div>
          <div class="bulk-actions">
            <button class="btn btn-sm btn-secondary" (click)="bulkActivate()">
              <span class="material-symbols-outlined">visibility</span>
              Activate
            </button>
            <button class="btn btn-sm btn-secondary" (click)="bulkDeactivate()">
              <span class="material-symbols-outlined">visibility_off</span>
              Deactivate
            </button>
            <button class="btn btn-sm btn-danger" (click)="confirmBulkDelete()">
              <span class="material-symbols-outlined">delete</span>
              Delete
            </button>
            <button class="btn btn-sm btn-ghost" (click)="clearSelection()">
              Clear
            </button>
          </div>
        </div>
      }

      <!-- Filters & Search -->
      <div class="toolbar">
        <div class="search-wrapper">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            type="text"
            class="search-input"
            placeholder="Search by name or code..."
            [(ngModel)]="searchQuery"
            (ngModelChange)="onSearchChange($event)"
          />
          @if (searchQuery) {
            <button class="clear-search" (click)="clearSearch()">
              <span class="material-symbols-outlined">close</span>
            </button>
          }
        </div>

        <div class="filters">
          <select [(ngModel)]="selectedLevel" (change)="applyFilters()">
            <option value="">All Levels</option>
            <option value="primary">Primary</option>
            <option value="secondary">Secondary</option>
            <option value="o_level">O Level</option>
            <option value="a_level">A Level</option>
          </select>
          <select [(ngModel)]="selectedStatus" (change)="applyFilters()">
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      <!-- Data Table -->
      <div class="table-container">
        @if (isLoading()) {
          <div class="loading-overlay">
            <div class="spinner"></div>
            <span>Loading subjects...</span>
          </div>
        }

        <table class="data-table">
          <thead>
            <tr>
              <th class="checkbox-col">
                <input
                  type="checkbox"
                  [checked]="isAllSelected()"
                  [indeterminate]="isIndeterminate()"
                  (change)="toggleSelectAll()"
                />
              </th>
              <th class="sortable" (click)="sortBy('name')">
                Name
                @if (sortColumn() === 'name') {
                  <span class="material-symbols-outlined sort-icon">
                    {{ sortDirection() === 'asc' ? 'arrow_upward' : 'arrow_downward' }}
                  </span>
                }
              </th>
              <th class="sortable" (click)="sortBy('code')">
                Code
                @if (sortColumn() === 'code') {
                  <span class="material-symbols-outlined sort-icon">
                    {{ sortDirection() === 'asc' ? 'arrow_upward' : 'arrow_downward' }}
                  </span>
                }
              </th>
              <th class="sortable" (click)="sortBy('education_level')">
                Level
                @if (sortColumn() === 'education_level') {
                  <span class="material-symbols-outlined sort-icon">
                    {{ sortDirection() === 'asc' ? 'arrow_upward' : 'arrow_downward' }}
                  </span>
                }
              </th>
              <th class="sortable center" (click)="sortBy('topic_count')">
                Topics
                @if (sortColumn() === 'topic_count') {
                  <span class="material-symbols-outlined sort-icon">
                    {{ sortDirection() === 'asc' ? 'arrow_upward' : 'arrow_downward' }}
                  </span>
                }
              </th>
              <th class="sortable center" (click)="sortBy('question_count')">
                Questions
                @if (sortColumn() === 'question_count') {
                  <span class="material-symbols-outlined sort-icon">
                    {{ sortDirection() === 'asc' ? 'arrow_upward' : 'arrow_downward' }}
                  </span>
                }
              </th>
              <th class="center">Status</th>
              <th class="actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (subject of subjects(); track subject.id) {
              <tr [class.selected]="isSelected(subject)">
                <td class="checkbox-col">
                  <input
                    type="checkbox"
                    [checked]="isSelected(subject)"
                    (change)="toggleSelect(subject)"
                  />
                </td>
                <td>
                  <div class="subject-name-cell">
                    <div class="subject-icon" [style.background-color]="subject.color || '#3b82f6'">
                      <span class="material-symbols-outlined">{{ subject.icon || 'menu_book' }}</span>
                    </div>
                    <div class="subject-info">
                      <span class="subject-name">{{ subject.name }}</span>
                      @if (subject.description) {
                        <span class="subject-desc">{{ subject.description | slice:0:50 }}{{ subject.description.length > 50 ? '...' : '' }}</span>
                      }
                    </div>
                  </div>
                </td>
                <td>
                  <code class="subject-code">{{ subject.code }}</code>
                </td>
                <td>
                  <span class="level-badge" [class]="subject.education_level">
                    {{ formatLevel(subject.education_level) }}
                  </span>
                </td>
                <td class="center">{{ subject.topic_count }}</td>
                <td class="center">{{ subject.question_count }}</td>
                <td class="center">
                  <span class="status-badge" [class.active]="subject.is_active" [class.inactive]="!subject.is_active">
                    <span class="status-dot"></span>
                    {{ subject.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
                <td class="actions-col">
                  <div class="row-actions">
                    <button class="action-btn" title="Edit" (click)="editSubject(subject)">
                      <span class="material-symbols-outlined">edit</span>
                    </button>
                    <button class="action-btn" title="View Topics" (click)="viewTopics(subject)">
                      <span class="material-symbols-outlined">topic</span>
                    </button>
                    <button class="action-btn danger" title="Delete" (click)="confirmDelete(subject)">
                      <span class="material-symbols-outlined">delete</span>
                    </button>
                  </div>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="8" class="empty-state">
                  <div class="empty-content">
                    <span class="material-symbols-outlined">menu_book</span>
                    <h3>No subjects found</h3>
                    <p>{{ searchQuery || selectedLevel || selectedStatus ? 'Try adjusting your filters' : 'Create your first subject to get started' }}</p>
                    @if (!searchQuery && !selectedLevel && !selectedStatus) {
                      <button class="btn btn-primary" (click)="openCreateModal()">
                        <span class="material-symbols-outlined">add</span>
                        Add Subject
                      </button>
                    }
                  </div>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      @if (totalPages() > 1) {
        <div class="pagination">
          <div class="pagination-info">
            Showing {{ (currentPage() - 1) * pageSize() + 1 }} - {{ Math.min(currentPage() * pageSize(), totalSubjects()) }}
            of {{ totalSubjects() }} subjects
          </div>
          <div class="pagination-controls">
            <button
              class="pagination-btn"
              [disabled]="currentPage() === 1"
              (click)="goToPage(1)"
              title="First page"
            >
              <span class="material-symbols-outlined">first_page</span>
            </button>
            <button
              class="pagination-btn"
              [disabled]="currentPage() === 1"
              (click)="goToPage(currentPage() - 1)"
              title="Previous page"
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
              [disabled]="currentPage() === totalPages()"
              (click)="goToPage(currentPage() + 1)"
              title="Next page"
            >
              <span class="material-symbols-outlined">chevron_right</span>
            </button>
            <button
              class="pagination-btn"
              [disabled]="currentPage() === totalPages()"
              (click)="goToPage(totalPages())"
              title="Last page"
            >
              <span class="material-symbols-outlined">last_page</span>
            </button>
          </div>
        </div>
      }
    </div>

    <!-- Create/Edit Modal -->
    <app-modal #formModal [title]="editingSubject() ? 'Edit Subject' : 'Create Subject'" size="md" [showFooter]="false">
      <app-subject-form-modal
        [subject]="editingSubject()"
        [isSubmitting]="isSubmitting()"
        (submitForm)="onFormSubmit($event)"
        (cancel)="formModal.close()"
      />
    </app-modal>

    <!-- Confirm Delete Dialog -->
    <app-confirm-dialog
      [isOpen]="showDeleteDialog()"
      [title]="deleteDialogTitle()"
      [message]="deleteDialogMessage()"
      [type]="deleteDialogType()"
      [confirmText]="deleteDialogCanConfirm() ? 'Delete' : 'Close'"
      (confirm)="onDeleteConfirm()"
      (cancel)="closeDeleteDialog()"
    />
  `,
  styles: [`
    .page-container {
      padding: 1.5rem 2rem;
    }

    .header-actions-wrapper {
      display: flex;
      gap: 0.75rem;
      align-items: center;
    }

    .export-dropdown {
      position: relative;

      .chevron {
        font-size: 1.125rem;
        transition: transform 0.2s ease;
      }

      &.open .chevron {
        transform: rotate(180deg);
      }
    }

    .dropdown-menu {
      position: absolute;
      top: 100%;
      right: 0;
      margin-top: 0.5rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      box-shadow: var(--shadow-lg);
      min-width: 180px;
      z-index: 100;
      animation: fadeIn 0.15s ease;

      button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        width: 100%;
        padding: 0.625rem 1rem;
        font-size: 0.875rem;
        color: var(--text-primary);
        background: none;
        border: none;
        cursor: pointer;
        transition: background-color 0.15s ease;

        &:hover {
          background-color: var(--background);
        }

        &:first-child {
          border-radius: 0.5rem 0.5rem 0 0;
        }

        &:last-child {
          border-radius: 0 0 0.5rem 0.5rem;
        }

        .material-symbols-outlined {
          font-size: 1.125rem;
          color: var(--text-secondary);
        }
      }
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 1.5rem;

      @media (max-width: 1200px) {
        grid-template-columns: repeat(2, 1fr);
      }

      @media (max-width: 640px) {
        grid-template-columns: 1fr;
      }
    }

    .bulk-action-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1rem;
      background-color: rgba(0, 102, 70, 0.05);
      border: 1px solid rgba(0, 102, 70, 0.1);
      border-radius: 0.5rem;
      margin-bottom: 1rem;
      animation: slideDown 0.2s ease;
    }

    @keyframes slideDown {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .selection-info {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--primary);

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .bulk-actions {
      display: flex;
      gap: 0.5rem;
    }

    .toolbar {
      display: flex;
      gap: 1rem;
      margin-bottom: 1rem;
      flex-wrap: wrap;
    }

    .search-wrapper {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex: 1;
      min-width: 280px;
      padding: 0 1rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      transition: border-color 0.15s ease;

      &:focus-within {
        border-color: var(--primary);
      }

      .search-icon {
        color: var(--text-muted);
        font-size: 1.25rem;
      }

      .search-input {
        flex: 1;
        padding: 0.625rem 0;
        border: none;
        background: transparent;
        font-size: 0.875rem;
        color: var(--text-primary);

        &::placeholder {
          color: var(--text-muted);
        }

        &:focus {
          outline: none;
        }
      }

      .clear-search {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 1.5rem;
        height: 1.5rem;
        background: var(--background);
        border: none;
        border-radius: 50%;
        cursor: pointer;
        color: var(--text-muted);

        &:hover {
          background-color: var(--border);
          color: var(--text-primary);
        }

        .material-symbols-outlined {
          font-size: 1rem;
        }
      }
    }

    .filters {
      display: flex;
      gap: 0.5rem;

      select {
        padding: 0.625rem 2rem 0.625rem 1rem;
        font-size: 0.875rem;
        color: var(--text-primary);
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        cursor: pointer;
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 0.5rem center;

        &:focus {
          outline: none;
          border-color: var(--primary);
        }
      }
    }

    .table-container {
      position: relative;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }

    .loading-overlay {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 1rem;
      background-color: rgba(var(--surface-rgb), 0.9);
      z-index: 10;

      .spinner {
        width: 2rem;
        height: 2rem;
        border: 3px solid var(--border);
        border-top-color: var(--primary);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }

      span {
        font-size: 0.875rem;
        color: var(--text-secondary);
      }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;

      th, td {
        padding: 0.875rem 1rem;
        text-align: left;
      }

      thead {
        background-color: var(--background);
        border-bottom: 1px solid var(--border);

        th {
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--text-secondary);
          white-space: nowrap;

          &.sortable {
            cursor: pointer;
            user-select: none;
            transition: color 0.15s ease;

            &:hover {
              color: var(--text-primary);
            }
          }

          &.center {
            text-align: center;
          }

          .sort-icon {
            font-size: 0.875rem;
            vertical-align: middle;
            margin-left: 0.25rem;
          }
        }
      }

      tbody {
        tr {
          border-bottom: 1px solid var(--border);
          transition: background-color 0.15s ease;

          &:last-child {
            border-bottom: none;
          }

          &:hover {
            background-color: var(--background);
          }

          &.selected {
            background-color: rgba(0, 102, 70, 0.05);
          }
        }

        td {
          font-size: 0.875rem;
          color: var(--text-primary);

          &.center {
            text-align: center;
          }
        }
      }

      .checkbox-col {
        width: 48px;
        padding-left: 1rem;

        input[type="checkbox"] {
          width: 1rem;
          height: 1rem;
          accent-color: var(--primary);
          cursor: pointer;
        }
      }

      .actions-col {
        width: 120px;
      }
    }

    .subject-name-cell {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .subject-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 0.5rem;
      flex-shrink: 0;

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: white;
      }
    }

    .subject-info {
      display: flex;
      flex-direction: column;

      .subject-name {
        font-weight: 500;
      }

      .subject-desc {
        font-size: 0.75rem;
        color: var(--text-muted);
      }
    }

    .subject-code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.8125rem;
      padding: 0.25rem 0.5rem;
      background-color: var(--background);
      border-radius: 0.25rem;
    }

    .level-badge {
      display: inline-flex;
      padding: 0.25rem 0.625rem;
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-radius: 9999px;

      &.primary {
        background-color: rgba(16, 185, 129, 0.1);
        color: #10b981;
      }

      &.secondary {
        background-color: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }

      &.o_level {
        background-color: rgba(139, 92, 246, 0.1);
        color: #8b5cf6;
      }

      &.a_level {
        background-color: rgba(236, 72, 153, 0.1);
        color: #ec4899;
      }
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.25rem 0.625rem;
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 9999px;

      .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
      }

      &.active {
        background-color: rgba(16, 185, 129, 0.1);
        color: #10b981;

        .status-dot {
          background-color: #10b981;
        }
      }

      &.inactive {
        background-color: rgba(107, 114, 128, 0.1);
        color: #6b7280;

        .status-dot {
          background-color: #6b7280;
        }
      }
    }

    .row-actions {
      display: flex;
      gap: 0.25rem;
    }

    .action-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      background: transparent;
      border: none;
      border-radius: 0.375rem;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover {
        background-color: var(--background);
        color: var(--text-primary);
      }

      &.danger:hover {
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }

      .material-symbols-outlined {
        font-size: 1.125rem;
      }
    }

    .empty-state {
      padding: 4rem 2rem !important;
    }

    .empty-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;

      .material-symbols-outlined {
        font-size: 3rem;
        color: var(--text-muted);
        margin-bottom: 1rem;
      }

      h3 {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
      }

      p {
        font-size: 0.875rem;
        color: var(--text-muted);
        margin-bottom: 1.5rem;
      }
    }

    .pagination {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem 0;
      margin-top: 1rem;
    }

    .pagination-info {
      font-size: 0.875rem;
      color: var(--text-secondary);
    }

    .pagination-controls {
      display: flex;
      gap: 0.25rem;
    }

    .pagination-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      min-width: 36px;
      height: 36px;
      padding: 0 0.75rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-primary);
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.375rem;
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover:not(:disabled) {
        background-color: var(--background);
        border-color: var(--primary);
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      &.active {
        background-color: var(--primary);
        border-color: var(--primary);
        color: white;
      }

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.625rem 1rem;
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

    .btn-danger {
      background-color: var(--error);
      color: white;
      border: none;

      &:hover:not(:disabled) {
        background-color: #dc2626;
      }
    }

    .btn-ghost {
      background: transparent;
      color: var(--text-secondary);
      border: none;

      &:hover:not(:disabled) {
        background-color: var(--background);
        color: var(--text-primary);
      }
    }

    .btn-sm {
      padding: 0.375rem 0.75rem;
      font-size: 0.8125rem;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
  `]
})
export class SubjectsListComponent implements OnInit {
  private contentService = inject(ContentService);
  private toastService = inject(ToastService);

  @ViewChild('formModal') formModal!: ModalComponent;

  // Expose Math for template
  Math = Math;

  // Breadcrumbs
  breadcrumbs: Breadcrumb[] = [
    { label: 'Dashboard', link: '/dashboard' },
    { label: 'Content', link: '/content' },
    { label: 'Subjects' }
  ];

  // State
  subjects = signal<Subject[]>([]);
  stats = signal<SubjectStats | null>(null);
  isLoading = signal(true);
  isSubmitting = signal(false);

  // Pagination
  currentPage = signal(1);
  pageSize = signal(20);
  totalSubjects = signal(0);
  totalPages = computed(() => Math.ceil(this.totalSubjects() / this.pageSize()) || 1);

  // Sorting
  sortColumn = signal<string>('name');
  sortDirection = signal<'asc' | 'desc'>('asc');

  // Filters
  searchQuery = '';
  selectedLevel = '';
  selectedStatus = '';
  private searchTimeout: ReturnType<typeof setTimeout> | null = null;

  // Selection
  selectedSubjects = signal<Subject[]>([]);
  hasSelection = computed(() => this.selectedSubjects().length > 0);

  // Modal state
  editingSubject = signal<Subject | null>(null);

  // Delete dialog state
  showDeleteDialog = signal(false);
  deleteDialogTitle = signal('');
  deleteDialogMessage = signal('');
  deleteDialogType = signal<'danger' | 'warning' | 'info'>('danger');
  deleteDialogCanConfirm = signal(true);
  pendingDeleteSubject = signal<Subject | null>(null);
  pendingBulkDelete = signal(false);

  // Export menu
  showExportMenu = signal(false);

  // Computed
  visiblePages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: number[] = [];

    if (total <= 7) {
      for (let i = 1; i <= total; i++) pages.push(i);
    } else {
      if (current <= 3) {
        pages.push(1, 2, 3, 4, 5);
      } else if (current >= total - 2) {
        pages.push(total - 4, total - 3, total - 2, total - 1, total);
      } else {
        pages.push(current - 2, current - 1, current, current + 1, current + 2);
      }
    }

    return pages;
  });

  ngOnInit(): void {
    this.loadSubjects();
    this.loadStats();
  }

  loadSubjects(): void {
    this.isLoading.set(true);

    const params: SubjectListParams = {
      page: this.currentPage(),
      page_size: this.pageSize(),
      sort_by: this.sortColumn() as SubjectListParams['sort_by'],
      sort_order: this.sortDirection(),
      search: this.searchQuery || undefined,
      education_level: this.selectedLevel || undefined,
      is_active: this.selectedStatus === '' ? undefined : this.selectedStatus === 'active'
    };

    this.contentService.getSubjects(params).subscribe({
      next: (response) => {
        this.subjects.set(response.subjects);
        this.totalSubjects.set(response.total);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.toastService.error('Failed to load subjects', err.error?.detail || 'Please try again');
        this.isLoading.set(false);
      }
    });
  }

  loadStats(): void {
    this.contentService.getSubjectStats().subscribe({
      next: (stats) => this.stats.set(stats),
      error: () => {} // Silent fail for stats
    });
  }

  // Search handling
  onSearchChange(query: string): void {
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }

    this.searchTimeout = setTimeout(() => {
      this.currentPage.set(1);
      this.loadSubjects();
    }, 300);
  }

  clearSearch(): void {
    this.searchQuery = '';
    this.currentPage.set(1);
    this.loadSubjects();
  }

  // Filter handling
  applyFilters(): void {
    this.currentPage.set(1);
    this.loadSubjects();
  }

  // Sorting
  sortBy(column: string): void {
    if (this.sortColumn() === column) {
      this.sortDirection.set(this.sortDirection() === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortColumn.set(column);
      this.sortDirection.set('asc');
    }
    this.loadSubjects();
  }

  // Pagination
  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
      this.loadSubjects();
    }
  }

  // Selection
  isSelected(subject: Subject): boolean {
    return this.selectedSubjects().some(s => s.id === subject.id);
  }

  toggleSelect(subject: Subject): void {
    const selected = this.selectedSubjects();
    if (this.isSelected(subject)) {
      this.selectedSubjects.set(selected.filter(s => s.id !== subject.id));
    } else {
      this.selectedSubjects.set([...selected, subject]);
    }
  }

  isAllSelected(): boolean {
    const subjects = this.subjects();
    return subjects.length > 0 && subjects.every(s => this.isSelected(s));
  }

  isIndeterminate(): boolean {
    const selected = this.selectedSubjects();
    const subjects = this.subjects();
    return selected.length > 0 && selected.length < subjects.length;
  }

  toggleSelectAll(): void {
    if (this.isAllSelected()) {
      this.selectedSubjects.set([]);
    } else {
      this.selectedSubjects.set([...this.subjects()]);
    }
  }

  clearSelection(): void {
    this.selectedSubjects.set([]);
  }

  // Bulk actions
  bulkActivate(): void {
    this.performBulkAction('activate');
  }

  bulkDeactivate(): void {
    this.performBulkAction('deactivate');
  }

  confirmBulkDelete(): void {
    this.pendingBulkDelete.set(true);
    this.deleteDialogTitle.set('Delete Selected Subjects');
    this.deleteDialogMessage.set(
      `Are you sure you want to delete ${this.selectedSubjects().length} subject(s)? Subjects with questions cannot be deleted.`
    );
    this.deleteDialogType.set('danger');
    this.deleteDialogCanConfirm.set(true);
    this.showDeleteDialog.set(true);
  }

  private performBulkAction(action: 'activate' | 'deactivate' | 'delete'): void {
    const ids = this.selectedSubjects().map(s => s.id);

    this.contentService.bulkSubjectAction({ subject_ids: ids, action }).subscribe({
      next: (result) => {
        if (result.failed > 0) {
          this.toastService.warning(result.message);
        } else {
          this.toastService.success(result.message);
        }
        this.clearSelection();
        this.loadSubjects();
        this.loadStats();
      },
      error: (err) => {
        this.toastService.error('Bulk action failed', err.error?.detail || 'Please try again');
      }
    });
  }

  // Create/Edit
  openCreateModal(): void {
    this.editingSubject.set(null);
    this.formModal.open();
  }

  editSubject(subject: Subject): void {
    this.editingSubject.set(subject);
    this.formModal.open();
  }

  onFormSubmit(data: SubjectCreate | SubjectUpdate): void {
    this.isSubmitting.set(true);
    const editing = this.editingSubject();

    if (editing) {
      this.contentService.updateSubject(editing.id, data as SubjectUpdate).subscribe({
        next: () => {
          this.toastService.success('Subject updated successfully');
          this.formModal.close();
          this.isSubmitting.set(false);
          this.loadSubjects();
          this.loadStats();
        },
        error: (err) => {
          this.toastService.error('Failed to update subject', err.error?.detail || 'Please try again');
          this.isSubmitting.set(false);
        }
      });
    } else {
      this.contentService.createSubject(data as SubjectCreate).subscribe({
        next: () => {
          this.toastService.success('Subject created successfully');
          this.formModal.close();
          this.isSubmitting.set(false);
          this.loadSubjects();
          this.loadStats();
        },
        error: (err) => {
          this.toastService.error('Failed to create subject', err.error?.detail || 'Please try again');
          this.isSubmitting.set(false);
        }
      });
    }
  }

  // Delete
  confirmDelete(subject: Subject): void {
    this.pendingDeleteSubject.set(subject);
    this.pendingBulkDelete.set(false);

    // Check dependencies first
    this.contentService.checkSubjectDependencies(subject.id).subscribe({
      next: (deps) => {
        this.deleteDialogTitle.set(deps.can_delete ? 'Delete Subject' : 'Cannot Delete Subject');
        this.deleteDialogMessage.set(
          deps.can_delete
            ? `Are you sure you want to delete "${subject.name}"?${deps.warnings.length > 0 ? ' ' + deps.warnings.join('. ') : ''}`
            : `This subject cannot be deleted: ${deps.warnings.join('. ')}`
        );
        this.deleteDialogType.set(deps.can_delete ? 'danger' : 'warning');
        this.deleteDialogCanConfirm.set(deps.can_delete);
        this.showDeleteDialog.set(true);
      },
      error: () => {
        this.toastService.error('Failed to check dependencies');
      }
    });
  }

  onDeleteConfirm(): void {
    if (this.pendingBulkDelete()) {
      this.performBulkAction('delete');
    } else {
      const subject = this.pendingDeleteSubject();
      if (subject && this.deleteDialogCanConfirm()) {
        this.contentService.deleteSubject(subject.id).subscribe({
          next: () => {
            this.toastService.success('Subject deleted successfully');
            this.loadSubjects();
            this.loadStats();
          },
          error: (err) => {
            this.toastService.error('Failed to delete subject', err.error?.detail || 'Please try again');
          }
        });
      }
    }
    this.closeDeleteDialog();
  }

  closeDeleteDialog(): void {
    this.showDeleteDialog.set(false);
    this.pendingDeleteSubject.set(null);
    this.pendingBulkDelete.set(false);
  }

  // Export
  toggleExportMenu(): void {
    this.showExportMenu.set(!this.showExportMenu());
  }

  exportSubjects(format: 'csv' | 'json'): void {
    this.showExportMenu.set(false);

    const selectedIds = this.selectedSubjects().map(s => s.id);

    this.contentService.exportSubjects({
      format,
      subject_ids: selectedIds.length > 0 ? selectedIds : undefined,
      include_topics: true
    }).subscribe({
      next: (response) => {
        this.contentService.downloadExport(response.download_url).subscribe({
          next: (blob) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = response.filename;
            a.click();
            window.URL.revokeObjectURL(url);
            this.toastService.success(`Exported ${response.record_count} subjects`);
          },
          error: () => this.toastService.error('Download failed')
        });
      },
      error: (err) => {
        this.toastService.error('Export failed', err.error?.detail || 'Please try again');
      }
    });
  }

  // View topics
  viewTopics(subject: Subject): void {
    this.toastService.info(`Navigate to topics for ${subject.name}`);
    // TODO: Navigate to topics page with subject filter
  }

  // Helpers
  formatLevel(level: string): string {
    const levels: Record<string, string> = {
      'primary': 'Primary',
      'secondary': 'Secondary',
      'o_level': 'O Level',
      'a_level': 'A Level'
    };
    return levels[level] || level;
  }
}
