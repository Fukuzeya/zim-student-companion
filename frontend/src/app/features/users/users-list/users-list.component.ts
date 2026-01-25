import { Component, inject, OnInit, signal, computed, ViewChild, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AdminService, CreateUserRequest } from '../../../core/services/admin.service';
import { ToastService } from '../../../core/services/toast.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import {
  User,
  UserRole,
  UserFilters,
  BulkAction,
  EducationLevel,
  ZIMBABWE_PROVINCES,
  ExportFormat
} from '../../../core/models';
import { SubscriptionTier } from '../../../core/models/auth.models';
import { Subject, debounceTime, distinctUntilChanged, takeUntil } from 'rxjs';

@Component({
  selector: 'app-users-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    PageHeaderComponent,
    ConfirmDialogComponent,
    LoadingSpinnerComponent,
    ModalComponent
  ],
  template: `
    <div class="users-page">
      <!-- Page Header -->
      <app-page-header
        title="User Management"
        description="Comprehensive user directory with advanced filtering, bulk operations, and audit capabilities."
        [breadcrumbs]="[
          { label: 'Dashboard', link: '/dashboard' },
          { label: 'Administration' },
          { label: 'Users' }
        ]"
      >
        <div headerActions class="header-actions">
          <button class="btn btn-outline" (click)="toggleFilters()">
            <span class="material-symbols-outlined">filter_list</span>
            {{ showAdvancedFilters() ? 'Hide' : 'Show' }} Filters
            @if (activeFilterCount() > 0) {
              <span class="filter-badge">{{ activeFilterCount() }}</span>
            }
          </button>
          <div class="export-dropdown" [class.open]="showExportMenu()">
            <button class="btn btn-outline" (click)="toggleExportMenu()">
              <span class="material-symbols-outlined">download</span>
              Export
              <span class="material-symbols-outlined arrow">expand_more</span>
            </button>
            <div class="dropdown-menu">
              <button (click)="exportUsers(ExportFormat.CSV)">
                <span class="material-symbols-outlined">description</span>
                Export as CSV
              </button>
              <button (click)="exportUsers(ExportFormat.JSON)">
                <span class="material-symbols-outlined">data_object</span>
                Export as JSON
              </button>
              <button (click)="exportUsers(ExportFormat.EXCEL)">
                <span class="material-symbols-outlined">table_chart</span>
                Export as Excel
              </button>
            </div>
          </div>
          <button class="btn btn-primary" (click)="openAddUserModal()">
            <span class="material-symbols-outlined">person_add</span>
            Add User
          </button>
        </div>
      </app-page-header>

      <!-- Statistics Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon total">
            <span class="material-symbols-outlined">group</span>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats().total | number }}</span>
            <span class="stat-label">Total Users</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon active">
            <span class="material-symbols-outlined">verified_user</span>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats().active | number }}</span>
            <span class="stat-label">Active Users</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon students">
            <span class="material-symbols-outlined">school</span>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats().students | number }}</span>
            <span class="stat-label">Students</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon premium">
            <span class="material-symbols-outlined">workspace_premium</span>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats().premium | number }}</span>
            <span class="stat-label">Premium Users</span>
          </div>
        </div>
      </div>

      <!-- Search and Quick Filters -->
      <div class="search-section">
        <div class="search-wrapper">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            type="text"
            class="search-input"
            placeholder="Search by name, email, phone, or school..."
            [(ngModel)]="searchQuery"
            (ngModelChange)="onSearchChange($event)"
          />
          @if (searchQuery) {
            <button class="clear-search" (click)="clearSearch()">
              <span class="material-symbols-outlined">close</span>
            </button>
          }
        </div>
        <div class="quick-filters">
          <button
            class="quick-filter"
            [class.active]="quickFilter() === 'all'"
            (click)="setQuickFilter('all')"
          >
            All Users
          </button>
          <button
            class="quick-filter"
            [class.active]="quickFilter() === 'students'"
            (click)="setQuickFilter('students')"
          >
            Students
          </button>
          <button
            class="quick-filter"
            [class.active]="quickFilter() === 'parents'"
            (click)="setQuickFilter('parents')"
          >
            Parents
          </button>
          <button
            class="quick-filter"
            [class.active]="quickFilter() === 'teachers'"
            (click)="setQuickFilter('teachers')"
          >
            Teachers
          </button>
          <button
            class="quick-filter"
            [class.active]="quickFilter() === 'admins'"
            (click)="setQuickFilter('admins')"
          >
            Admins
          </button>
          <button
            class="quick-filter"
            [class.active]="quickFilter() === 'inactive'"
            (click)="setQuickFilter('inactive')"
          >
            Inactive
          </button>
        </div>
      </div>

      <!-- Advanced Filters Panel -->
      @if (showAdvancedFilters()) {
        <div class="advanced-filters" @slideDown>
          <div class="filters-header">
            <h3>
              <span class="material-symbols-outlined">tune</span>
              Advanced Filters
            </h3>
            <button class="btn btn-text" (click)="resetFilters()">
              <span class="material-symbols-outlined">restart_alt</span>
              Reset All
            </button>
          </div>
          <div class="filters-grid">
            <!-- Role Filter -->
            <div class="filter-group">
              <label>User Role</label>
              <select [(ngModel)]="filters.role" (change)="applyFilters()">
                <option [ngValue]="undefined">All Roles</option>
                <option value="student">Student</option>
                <option value="parent">Parent</option>
                <option value="teacher">Teacher</option>
                <option value="admin">Administrator</option>
              </select>
            </div>

            <!-- Subscription Filter -->
            <div class="filter-group">
              <label>Subscription Tier</label>
              <select [(ngModel)]="filters.subscription_tier" (change)="applyFilters()">
                <option [ngValue]="undefined">All Tiers</option>
                <option value="free">Free</option>
                <option value="basic">Basic</option>
                <option value="premium">Premium</option>
                <option value="family">Family</option>
                <option value="school">School</option>
              </select>
            </div>

            <!-- Status Filter -->
            <div class="filter-group">
              <label>Account Status</label>
              <select [(ngModel)]="statusFilter" (change)="applyStatusFilter()">
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="verified">Verified</option>
                <option value="unverified">Unverified</option>
              </select>
            </div>

            <!-- Education Level -->
            <div class="filter-group">
              <label>Education Level</label>
              <select [(ngModel)]="filters.education_level" (change)="applyFilters()">
                <option [ngValue]="undefined">All Levels</option>
                <option value="primary">Primary</option>
                <option value="secondary">Secondary (O-Level)</option>
                <option value="a_level">Advanced Level</option>
              </select>
            </div>

            <!-- Province Filter -->
            <div class="filter-group">
              <label>Province</label>
              <select [(ngModel)]="filters.province" (change)="applyFilters()">
                <option [ngValue]="undefined">All Provinces</option>
                @for (province of provinces; track province) {
                  <option [value]="province">{{ province }}</option>
                }
              </select>
            </div>

            <!-- District Filter -->
            <div class="filter-group">
              <label>District</label>
              <input
                type="text"
                [(ngModel)]="filters.district"
                (input)="onFilterChange()"
                placeholder="Enter district..."
              />
            </div>

            <!-- School Filter -->
            <div class="filter-group">
              <label>School</label>
              <input
                type="text"
                [(ngModel)]="filters.school"
                (input)="onFilterChange()"
                placeholder="Enter school name..."
              />
            </div>

            <!-- Registration Date Range -->
            <div class="filter-group date-range">
              <label>Registration Date</label>
              <div class="date-inputs">
                <input
                  type="date"
                  [(ngModel)]="filters.registration_date_from"
                  (change)="applyFilters()"
                  placeholder="From"
                />
                <span class="date-separator">to</span>
                <input
                  type="date"
                  [(ngModel)]="filters.registration_date_to"
                  (change)="applyFilters()"
                  placeholder="To"
                />
              </div>
            </div>

            <!-- Last Active Date Range -->
            <div class="filter-group date-range">
              <label>Last Active</label>
              <div class="date-inputs">
                <input
                  type="date"
                  [(ngModel)]="filters.last_active_from"
                  (change)="applyFilters()"
                  placeholder="From"
                />
                <span class="date-separator">to</span>
                <input
                  type="date"
                  [(ngModel)]="filters.last_active_to"
                  (change)="applyFilters()"
                  placeholder="To"
                />
              </div>
            </div>
          </div>
        </div>
      }

      <!-- Active Filters Tags -->
      @if (activeFilterTags().length > 0) {
        <div class="active-filters">
          <span class="active-filters-label">Active Filters:</span>
          @for (tag of activeFilterTags(); track tag.key) {
            <span class="filter-tag">
              {{ tag.label }}
              <button (click)="removeFilter(tag.key)">
                <span class="material-symbols-outlined">close</span>
              </button>
            </span>
          }
          <button class="clear-all-btn" (click)="resetFilters()">Clear All</button>
        </div>
      }

      <!-- Users Table -->
      <div class="table-container">
        @if (loading()) {
          <div class="table-loading">
            <app-loading-spinner message="Loading users..." />
          </div>
        } @else {
          <table class="data-table">
            <thead>
              <tr>
                <th class="checkbox-col">
                  <input
                    type="checkbox"
                    [checked]="allSelected()"
                    [indeterminate]="someSelected()"
                    (change)="toggleSelectAll()"
                  />
                </th>
                <th class="sortable" (click)="sortBy('name')">
                  <div class="th-content">
                    User
                    <span class="sort-indicator" [class.active]="filters.sort_by === 'name'">
                      {{ getSortIcon('name') }}
                    </span>
                  </div>
                </th>
                <th>Contact</th>
                <th class="sortable" (click)="sortBy('role')">
                  <div class="th-content">
                    Role
                    <span class="sort-indicator" [class.active]="filters.sort_by === 'role'">
                      {{ getSortIcon('role') }}
                    </span>
                  </div>
                </th>
                <th>Subscription</th>
                <th>Status</th>
                <th class="hide-md">Institution</th>
                <th class="sortable hide-sm" (click)="sortBy('created_at')">
                  <div class="th-content">
                    Joined
                    <span class="sort-indicator" [class.active]="filters.sort_by === 'created_at'">
                      {{ getSortIcon('created_at') }}
                    </span>
                  </div>
                </th>
                <th class="sortable hide-lg" (click)="sortBy('last_active')">
                  <div class="th-content">
                    Last Active
                    <span class="sort-indicator" [class.active]="filters.sort_by === 'last_active'">
                      {{ getSortIcon('last_active') }}
                    </span>
                  </div>
                </th>
                <th class="actions-col">Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (user of users(); track user.id) {
                <tr [class.selected]="isSelected(user.id)" [class.inactive]="!user.is_active">
                  <td class="checkbox-col">
                    <input
                      type="checkbox"
                      [checked]="isSelected(user.id)"
                      (change)="toggleSelect(user.id)"
                    />
                  </td>
                  <td>
                    <div class="user-cell">
                      <div class="user-avatar" [class]="user.role" [class.inactive]="!user.is_active">
                        @if (user.avatar_url) {
                          <img [src]="user.avatar_url" [alt]="getUserName(user)" />
                        } @else {
                          {{ getInitials(user) }}
                        }
                      </div>
                      <div class="user-info">
                        <span class="user-name">{{ getUserName(user) }}</span>
                        <span class="user-id">ID: {{ user.id.slice(0, 8) }}...</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div class="contact-cell">
                      <span class="contact-email">{{ user.email || '-' }}</span>
                      <span class="contact-phone">{{ user.phone_number }}</span>
                    </div>
                  </td>
                  <td>
                    <span class="role-badge" [class]="user.role">
                      <span class="material-symbols-outlined">{{ getRoleIcon(user.role) }}</span>
                      {{ user.role | titlecase }}
                    </span>
                  </td>
                  <td>
                    <span class="subscription-badge" [class]="user.subscription_tier">
                      {{ user.subscription_tier | titlecase }}
                    </span>
                  </td>
                  <td>
                    <div class="status-cell">
                      <span class="status-badge" [class]="user.is_active ? 'active' : 'inactive'">
                        <span class="status-dot"></span>
                        {{ user.is_active ? 'Active' : 'Inactive' }}
                      </span>
                      @if (user.is_verified) {
                        <span class="verified-badge" title="Verified">
                          <span class="material-symbols-outlined">verified</span>
                        </span>
                      }
                    </div>
                  </td>
                  <td class="hide-md">
                    <span class="institution-text">{{ user.institution || user.school || '-' }}</span>
                  </td>
                  <td class="hide-sm">
                    <span class="date-text">{{ formatDate(user.created_at) }}</span>
                  </td>
                  <td class="hide-lg">
                    <span class="date-text" [class.inactive]="isInactiveRecently(user.last_active)">
                      {{ formatRelativeDate(user.last_active) }}
                    </span>
                  </td>
                  <td class="actions-col">
                    <div class="row-actions">
                      <button
                        class="action-btn"
                        title="View Details"
                        [routerLink]="['/users', user.id]"
                      >
                        <span class="material-symbols-outlined">visibility</span>
                      </button>
                      <button
                        class="action-btn"
                        title="Edit User"
                        (click)="openEditUserModal(user)"
                      >
                        <span class="material-symbols-outlined">edit</span>
                      </button>
                      @if (user.is_active && user.role !== 'admin') {
                        <button
                          class="action-btn"
                          title="Impersonate User"
                          (click)="openImpersonateModal(user)"
                        >
                          <span class="material-symbols-outlined">supervisor_account</span>
                        </button>
                      }
                      <button
                        class="action-btn more"
                        title="More Actions"
                        (click)="openContextMenu(user, $event)"
                      >
                        <span class="material-symbols-outlined">more_vert</span>
                      </button>
                    </div>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="10">
                    <div class="empty-state">
                      <span class="material-symbols-outlined">search_off</span>
                      <h3>No Users Found</h3>
                      <p>Try adjusting your search criteria or filters</p>
                      <button class="btn btn-primary" (click)="resetFilters()">Reset Filters</button>
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>

          <!-- Pagination -->
          <div class="table-footer">
            <div class="pagination-info">
              <span>
                Showing <strong>{{ paginationStart() }}</strong> - <strong>{{ paginationEnd() }}</strong>
                of <strong>{{ totalUsers() | number }}</strong> users
              </span>
            </div>
            <div class="pagination-controls">
              <div class="page-size-select">
                <label>Rows per page:</label>
                <select [(ngModel)]="filters.page_size" (change)="onPageSizeChange()">
                  <option [value]="10">10</option>
                  <option [value]="25">25</option>
                  <option [value]="50">50</option>
                  <option [value]="100">100</option>
                </select>
              </div>
              <div class="page-nav">
                <button
                  class="nav-btn"
                  [disabled]="currentPage() === 1"
                  (click)="goToPage(1)"
                  title="First Page"
                >
                  <span class="material-symbols-outlined">first_page</span>
                </button>
                <button
                  class="nav-btn"
                  [disabled]="currentPage() === 1"
                  (click)="goToPage(currentPage() - 1)"
                  title="Previous Page"
                >
                  <span class="material-symbols-outlined">chevron_left</span>
                </button>
                <div class="page-numbers">
                  @for (page of visiblePages(); track page) {
                    @if (page === '...') {
                      <span class="ellipsis">...</span>
                    } @else {
                      <button
                        class="page-btn"
                        [class.active]="page === currentPage()"
                        (click)="goToPage(+page)"
                      >
                        {{ page }}
                      </button>
                    }
                  }
                </div>
                <button
                  class="nav-btn"
                  [disabled]="currentPage() >= totalPages()"
                  (click)="goToPage(currentPage() + 1)"
                  title="Next Page"
                >
                  <span class="material-symbols-outlined">chevron_right</span>
                </button>
                <button
                  class="nav-btn"
                  [disabled]="currentPage() >= totalPages()"
                  (click)="goToPage(totalPages())"
                  title="Last Page"
                >
                  <span class="material-symbols-outlined">last_page</span>
                </button>
              </div>
            </div>
          </div>
        }
      </div>

      <!-- Bulk Actions Bar -->
      @if (selectedUsers().length > 0) {
        <div class="bulk-actions-bar" @slideUp>
          <div class="selection-info">
            <span class="material-symbols-outlined">check_circle</span>
            <span>{{ selectedUsers().length }} user{{ selectedUsers().length > 1 ? 's' : '' }} selected</span>
            <button class="deselect-btn" (click)="clearSelection()">Deselect All</button>
          </div>
          <div class="bulk-buttons">
            <button class="bulk-btn" (click)="bulkAction('activate')">
              <span class="material-symbols-outlined">check_circle</span>
              Activate
            </button>
            <button class="bulk-btn" (click)="bulkAction('deactivate')">
              <span class="material-symbols-outlined">cancel</span>
              Deactivate
            </button>
            <button class="bulk-btn" (click)="bulkAction('verify')">
              <span class="material-symbols-outlined">verified</span>
              Verify
            </button>
            <div class="bulk-dropdown" [class.open]="showBulkSubscription()">
              <button class="bulk-btn" (click)="toggleBulkSubscription()">
                <span class="material-symbols-outlined">upgrade</span>
                Subscription
                <span class="material-symbols-outlined arrow">expand_more</span>
              </button>
              <div class="dropdown-menu">
                <button (click)="bulkAction('upgrade')">Upgrade to Basic</button>
                <button (click)="bulkAction('downgrade')">Downgrade to Free</button>
              </div>
            </div>
            <button class="bulk-btn danger" (click)="bulkAction('delete')">
              <span class="material-symbols-outlined">delete</span>
              Delete
            </button>
          </div>
        </div>
      }

      <!-- Confirm Dialog -->
      <app-confirm-dialog
        [isOpen]="showConfirmDialog()"
        [title]="confirmDialogTitle()"
        [message]="confirmDialogMessage()"
        [type]="confirmDialogType()"
        (confirm)="onConfirmAction()"
        (cancel)="closeConfirmDialog()"
      />

      <!-- Add/Edit User Modal -->
      <app-modal #userModal [title]="isEditMode ? 'Edit User' : 'Add New User'" size="lg">
        <div class="modal-form">
          <div class="form-section">
            <h4>Account Information</h4>
            <div class="form-grid">
              <div class="form-group">
                <label for="fullName">Full Name</label>
                <input
                  type="text"
                  id="fullName"
                  [(ngModel)]="userForm.full_name"
                  placeholder="Enter full name"
                />
              </div>
              <div class="form-group">
                <label for="email">Email Address <span class="required">*</span></label>
                <input
                  type="email"
                  id="email"
                  [(ngModel)]="userForm.email"
                  placeholder="user@example.com"
                  required
                />
              </div>
              <div class="form-group">
                <label for="phone">Phone Number <span class="required">*</span></label>
                <div class="phone-input">
                  <span class="country-code">+263</span>
                  <input
                    type="tel"
                    id="phone"
                    [(ngModel)]="userForm.phone_number"
                    placeholder="7X XXX XXXX"
                    required
                  />
                </div>
              </div>
              <div class="form-group">
                <label for="role">Role <span class="required">*</span></label>
                <select id="role" [(ngModel)]="userForm.role" required>
                  <option value="">Select Role</option>
                  <option value="student">Student</option>
                  <option value="parent">Parent</option>
                  <option value="teacher">Teacher</option>
                  <option value="admin">Administrator</option>
                </select>
              </div>
              @if (!isEditMode) {
                <div class="form-group">
                  <label for="password">Password <span class="required">*</span></label>
                  <div class="password-input">
                    <input
                      [type]="showPassword() ? 'text' : 'password'"
                      id="password"
                      [(ngModel)]="userForm.password"
                      placeholder="Enter password"
                      required
                    />
                    <button type="button" class="toggle-password" (click)="togglePasswordVisibility()">
                      <span class="material-symbols-outlined">
                        {{ showPassword() ? 'visibility_off' : 'visibility' }}
                      </span>
                    </button>
                  </div>
                </div>
              }
              <div class="form-group">
                <label for="institution">Institution / School</label>
                <input
                  type="text"
                  id="institution"
                  [(ngModel)]="userForm.institution"
                  placeholder="School or organization name"
                />
              </div>
            </div>
          </div>

          @if (isEditMode) {
            <div class="form-section">
              <h4>Subscription & Status</h4>
              <div class="form-grid">
                <div class="form-group">
                  <label for="subscription">Subscription Tier</label>
                  <select id="subscription" [(ngModel)]="editForm.subscription_tier">
                    <option value="free">Free</option>
                    <option value="basic">Basic</option>
                    <option value="premium">Premium</option>
                    <option value="family">Family</option>
                    <option value="school">School</option>
                  </select>
                </div>
                <div class="form-group">
                  <label for="expiry">Subscription Expiry</label>
                  <input
                    type="date"
                    id="expiry"
                    [(ngModel)]="editForm.subscription_expires_at"
                  />
                </div>
                <div class="form-group checkbox-group">
                  <label class="checkbox-label">
                    <input type="checkbox" [(ngModel)]="editForm.is_active" />
                    <span class="checkbox-custom"></span>
                    Account Active
                  </label>
                </div>
                <div class="form-group checkbox-group">
                  <label class="checkbox-label">
                    <input type="checkbox" [(ngModel)]="editForm.is_verified" />
                    <span class="checkbox-custom"></span>
                    Email Verified
                  </label>
                </div>
              </div>
            </div>
          }
        </div>
        <div modal-footer>
          <button type="button" class="btn btn-secondary" (click)="userModal.close()">Cancel</button>
          <button type="button" class="btn btn-primary" (click)="saveUser()" [disabled]="isSaving()">
            @if (isSaving()) {
              <span class="btn-spinner"></span>
            }
            {{ isEditMode ? 'Save Changes' : 'Create User' }}
          </button>
        </div>
      </app-modal>

      <!-- Impersonate Modal -->
      <app-modal #impersonateModal title="Impersonate User" size="md">
        @if (impersonatingUser) {
          <div class="impersonate-content">
            <div class="impersonate-warning">
              <span class="material-symbols-outlined">warning</span>
              <div>
                <h4>Security Notice</h4>
                <p>You are about to impersonate another user. This action will be logged and audited.</p>
              </div>
            </div>
            <div class="impersonate-user-info">
              <div class="user-avatar large" [class]="impersonatingUser.role">
                {{ getInitials(impersonatingUser) }}
              </div>
              <div class="user-details">
                <h3>{{ getUserName(impersonatingUser) }}</h3>
                <p>{{ impersonatingUser.email }}</p>
                <span class="role-badge" [class]="impersonatingUser.role">
                  {{ impersonatingUser.role | titlecase }}
                </span>
              </div>
            </div>
            <div class="impersonate-options">
              <label class="checkbox-label">
                <input type="checkbox" [(ngModel)]="impersonateReadOnly" />
                <span class="checkbox-custom"></span>
                Read-only mode (recommended)
              </label>
              <p class="option-hint">In read-only mode, you can view but not modify the user's data.</p>
            </div>
          </div>
        }
        @if (impersonatingUser) {
          <ng-container modal-footer>
            <button type="button" class="btn btn-secondary" (click)="impersonateModal.close()">Cancel</button>
            <button type="button" class="btn btn-warning" (click)="confirmImpersonate()" [disabled]="isImpersonating()">
              @if (isImpersonating()) {
                <span class="btn-spinner"></span>
              }
              <span class="material-symbols-outlined">supervisor_account</span>
              Start Impersonation
            </button>
          </ng-container>
        }
      </app-modal>

      <!-- Context Menu -->
      @if (contextMenu().show) {
        <div
          class="context-menu"
          [style.left.px]="contextMenu().x"
          [style.top.px]="contextMenu().y"
          (mouseleave)="closeContextMenu()"
        >
          <button (click)="contextAction('view')">
            <span class="material-symbols-outlined">visibility</span>
            View Details
          </button>
          <button (click)="contextAction('edit')">
            <span class="material-symbols-outlined">edit</span>
            Edit User
          </button>
          <hr />
          @if (contextMenu().user?.is_active) {
            <button (click)="contextAction('deactivate')">
              <span class="material-symbols-outlined">person_off</span>
              Deactivate Account
            </button>
          } @else {
            <button (click)="contextAction('activate')">
              <span class="material-symbols-outlined">person</span>
              Activate Account
            </button>
          }
          @if (!contextMenu().user?.is_verified) {
            <button (click)="contextAction('verify')">
              <span class="material-symbols-outlined">verified</span>
              Verify Email
            </button>
          }
          <button (click)="contextAction('reset-password')">
            <span class="material-symbols-outlined">lock_reset</span>
            Reset Password
          </button>
          <hr />
          <button class="danger" (click)="contextAction('delete')">
            <span class="material-symbols-outlined">delete</span>
            Delete User
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .users-page {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    /* Header Actions */
    .header-actions {
      display: flex;
      gap: 0.75rem;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.625rem 1rem;
      font-size: 0.875rem;
      font-weight: 500;
      border-radius: 0.5rem;
      cursor: pointer;
      transition: all 0.15s ease;
      white-space: nowrap;

      .material-symbols-outlined {
        font-size: 1.125rem;
      }
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--primary), #004d35);
      color: white;
      border: none;
      box-shadow: 0 2px 4px rgba(0, 102, 70, 0.2);

      &:hover {
        background: linear-gradient(135deg, #004d35, #003d2a);
        box-shadow: 0 4px 8px rgba(0, 102, 70, 0.3);
      }
    }

    .btn-secondary {
      background: var(--surface);
      color: var(--text-primary);
      border: 1px solid var(--border);

      &:hover {
        background: var(--hover);
      }
    }

    .btn-outline {
      background: transparent;
      color: var(--text-primary);
      border: 1px solid var(--border);

      &:hover {
        background: var(--hover);
        border-color: var(--text-muted);
      }
    }

    .btn-warning {
      background: linear-gradient(135deg, #f59e0b, #d97706);
      color: white;
      border: none;

      &:hover {
        background: linear-gradient(135deg, #d97706, #b45309);
      }
    }

    .btn-text {
      background: transparent;
      border: none;
      color: var(--primary);
      padding: 0.5rem;

      &:hover {
        background: rgba(0, 102, 70, 0.1);
      }
    }

    .filter-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.25rem;
      height: 1.25rem;
      font-size: 0.75rem;
      font-weight: 600;
      background: var(--primary);
      color: white;
      border-radius: 50%;
    }

    /* Export Dropdown */
    .export-dropdown {
      position: relative;

      .arrow {
        transition: transform 0.2s ease;
      }

      &.open .arrow {
        transform: rotate(180deg);
      }

      .dropdown-menu {
        position: absolute;
        top: calc(100% + 0.5rem);
        right: 0;
        min-width: 180px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        box-shadow: var(--shadow-lg);
        padding: 0.5rem;
        opacity: 0;
        visibility: hidden;
        transform: translateY(-10px);
        transition: all 0.2s ease;
        z-index: 100;

        button {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          width: 100%;
          padding: 0.625rem 0.75rem;
          font-size: 0.875rem;
          color: var(--text-primary);
          background: transparent;
          border: none;
          border-radius: 0.375rem;
          cursor: pointer;
          text-align: left;

          &:hover {
            background: var(--hover);
          }

          .material-symbols-outlined {
            font-size: 1.125rem;
            color: var(--text-muted);
          }
        }
      }

      &.open .dropdown-menu {
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
      }
    }

    /* Statistics Cards */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;

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
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      transition: all 0.2s ease;

      &:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
      }
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 0.75rem;

      .material-symbols-outlined {
        font-size: 1.5rem;
      }

      &.total {
        background: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }

      &.active {
        background: rgba(16, 185, 129, 0.1);
        color: #10b981;
      }

      &.students {
        background: rgba(139, 92, 246, 0.1);
        color: #8b5cf6;
      }

      &.premium {
        background: rgba(245, 158, 11, 0.1);
        color: #f59e0b;
      }
    }

    .stat-content {
      display: flex;
      flex-direction: column;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text-primary);
      line-height: 1.2;
    }

    .stat-label {
      font-size: 0.8125rem;
      color: var(--text-muted);
    }

    /* Search Section */
    .search-section {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      padding: 1rem;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
    }

    .search-wrapper {
      position: relative;
      flex: 1;

      .search-icon {
        position: absolute;
        left: 1rem;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text-muted);
        font-size: 1.25rem;
      }

      .search-input {
        width: 100%;
        padding: 0.75rem 2.5rem 0.75rem 3rem;
        font-size: 0.9375rem;
        background: var(--background);
        border: 1px solid transparent;
        border-radius: 0.5rem;
        transition: all 0.2s ease;

        &:focus {
          outline: none;
          border-color: var(--primary);
          background: var(--surface);
        }
      }

      .clear-search {
        position: absolute;
        right: 0.75rem;
        top: 50%;
        transform: translateY(-50%);
        padding: 0.25rem;
        background: transparent;
        border: none;
        color: var(--text-muted);
        cursor: pointer;
        border-radius: 50%;

        &:hover {
          background: var(--hover);
          color: var(--text-primary);
        }

        .material-symbols-outlined {
          font-size: 1.125rem;
        }
      }
    }

    .quick-filters {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .quick-filter {
      padding: 0.5rem 1rem;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--text-secondary);
      background: var(--background);
      border: 1px solid transparent;
      border-radius: 9999px;
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover {
        color: var(--text-primary);
        background: var(--hover);
      }

      &.active {
        color: var(--primary);
        background: rgba(0, 102, 70, 0.1);
        border-color: rgba(0, 102, 70, 0.2);
      }
    }

    /* Advanced Filters */
    .advanced-filters {
      padding: 1.5rem;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
    }

    .filters-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border);

      h3 {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);

        .material-symbols-outlined {
          font-size: 1.25rem;
          color: var(--text-muted);
        }
      }
    }

    .filters-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1.25rem;

      @media (max-width: 1200px) {
        grid-template-columns: repeat(3, 1fr);
      }

      @media (max-width: 900px) {
        grid-template-columns: repeat(2, 1fr);
      }

      @media (max-width: 640px) {
        grid-template-columns: 1fr;
      }
    }

    .filter-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;

      label {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }

      input, select {
        padding: 0.625rem 0.75rem;
        font-size: 0.875rem;
        background: var(--background);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        color: var(--text-primary);
        transition: border-color 0.15s ease;

        &:focus {
          outline: none;
          border-color: var(--primary);
        }
      }

      select {
        cursor: pointer;
      }

      &.date-range {
        grid-column: span 2;

        @media (max-width: 640px) {
          grid-column: span 1;
        }
      }
    }

    .date-inputs {
      display: flex;
      align-items: center;
      gap: 0.75rem;

      input {
        flex: 1;
      }

      .date-separator {
        color: var(--text-muted);
        font-size: 0.875rem;
      }
    }

    /* Active Filter Tags */
    .active-filters {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1rem;
      background: rgba(0, 102, 70, 0.05);
      border: 1px solid rgba(0, 102, 70, 0.1);
      border-radius: 0.5rem;
    }

    .active-filters-label {
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--text-secondary);
      margin-right: 0.25rem;
    }

    .filter-tag {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.25rem 0.5rem 0.25rem 0.75rem;
      font-size: 0.8125rem;
      color: var(--primary);
      background: white;
      border: 1px solid rgba(0, 102, 70, 0.2);
      border-radius: 9999px;

      button {
        display: flex;
        padding: 0.125rem;
        background: transparent;
        border: none;
        color: var(--text-muted);
        cursor: pointer;
        border-radius: 50%;

        &:hover {
          background: rgba(0, 102, 70, 0.1);
          color: var(--primary);
        }

        .material-symbols-outlined {
          font-size: 0.875rem;
        }
      }
    }

    .clear-all-btn {
      margin-left: 0.5rem;
      padding: 0.25rem 0.75rem;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--error);
      background: transparent;
      border: none;
      cursor: pointer;

      &:hover {
        text-decoration: underline;
      }
    }

    /* Data Table */
    .table-container {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }

    .table-loading {
      display: flex;
      justify-content: center;
      padding: 4rem 2rem;
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;

      th, td {
        padding: 0.875rem 1rem;
        text-align: left;
        border-bottom: 1px solid var(--border);
      }

      th {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        background: var(--background);
        white-space: nowrap;
        position: sticky;
        top: 0;
        z-index: 10;

        &.sortable {
          cursor: pointer;
          user-select: none;

          &:hover {
            color: var(--text-primary);
          }
        }
      }

      .th-content {
        display: flex;
        align-items: center;
        gap: 0.375rem;
      }

      .sort-indicator {
        font-size: 1rem;
        opacity: 0.3;
        transition: opacity 0.15s ease;

        &.active {
          opacity: 1;
          color: var(--primary);
        }
      }

      td {
        font-size: 0.875rem;
        color: var(--text-primary);
        vertical-align: middle;
      }

      tbody tr {
        transition: background-color 0.15s ease;

        &:hover {
          background: var(--hover);
        }

        &.selected {
          background: rgba(0, 102, 70, 0.05);
        }

        &.inactive {
          opacity: 0.7;
        }
      }
    }

    .checkbox-col {
      width: 48px;
      text-align: center;

      input[type="checkbox"] {
        width: 1rem;
        height: 1rem;
        cursor: pointer;
        accent-color: var(--primary);
      }
    }

    /* User Cell */
    .user-cell {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .user-avatar {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.875rem;
      font-weight: 600;
      color: white;
      border-radius: 50%;
      flex-shrink: 0;
      overflow: hidden;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      &.student { background: linear-gradient(135deg, #3b82f6, #2563eb); }
      &.parent { background: linear-gradient(135deg, #f97316, #ea580c); }
      &.teacher { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }
      &.admin { background: linear-gradient(135deg, #1f2937, #111827); }
      &.inactive { filter: grayscale(1); opacity: 0.6; }

      &.large {
        width: 64px;
        height: 64px;
        font-size: 1.25rem;
      }
    }

    .user-info {
      display: flex;
      flex-direction: column;
      min-width: 0;

      .user-name {
        font-weight: 600;
        color: var(--text-primary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .user-id {
        font-size: 0.75rem;
        color: var(--text-muted);
        font-family: monospace;
      }
    }

    /* Contact Cell */
    .contact-cell {
      display: flex;
      flex-direction: column;

      .contact-email {
        color: var(--text-primary);
        font-size: 0.875rem;
      }

      .contact-phone {
        color: var(--text-muted);
        font-size: 0.75rem;
      }
    }

    /* Role Badge */
    .role-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.25rem 0.625rem;
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 9999px;
      border: 1px solid;

      .material-symbols-outlined {
        font-size: 0.875rem;
      }

      &.student {
        background: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
        border-color: rgba(59, 130, 246, 0.2);
      }

      &.parent {
        background: rgba(249, 115, 22, 0.1);
        color: #f97316;
        border-color: rgba(249, 115, 22, 0.2);
      }

      &.teacher {
        background: rgba(139, 92, 246, 0.1);
        color: #8b5cf6;
        border-color: rgba(139, 92, 246, 0.2);
      }

      &.admin {
        background: var(--text-primary);
        color: var(--surface);
        border-color: var(--text-primary);
      }
    }

    /* Subscription Badge */
    .subscription-badge {
      display: inline-flex;
      padding: 0.25rem 0.625rem;
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 0.375rem;

      &.free {
        background: var(--background);
        color: var(--text-muted);
      }

      &.basic {
        background: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }

      &.premium {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(234, 88, 12, 0.15));
        color: #d97706;
      }

      &.family {
        background: rgba(16, 185, 129, 0.1);
        color: #10b981;
      }

      &.school {
        background: rgba(139, 92, 246, 0.1);
        color: #8b5cf6;
      }
    }

    /* Status Cell */
    .status-cell {
      display: flex;
      align-items: center;
      gap: 0.5rem;
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
        background: rgba(16, 185, 129, 0.1);
        color: #10b981;
        .status-dot { background: #10b981; }
      }

      &.inactive {
        background: rgba(239, 68, 68, 0.1);
        color: #ef4444;
        .status-dot { background: #ef4444; }
      }
    }

    .verified-badge {
      display: inline-flex;
      color: #3b82f6;

      .material-symbols-outlined {
        font-size: 1rem;
      }
    }

    .institution-text, .date-text {
      font-size: 0.8125rem;
      color: var(--text-secondary);

      &.inactive {
        color: var(--error);
      }
    }

    /* Row Actions */
    .actions-col {
      width: 140px;
    }

    .row-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.25rem;
      opacity: 0;
      transition: opacity 0.15s ease;

      tr:hover & {
        opacity: 1;
      }
    }

    .action-btn {
      padding: 0.375rem;
      background: transparent;
      border: none;
      border-radius: 0.375rem;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover {
        background: var(--hover);
        color: var(--text-primary);
      }

      &.more:hover {
        background: rgba(239, 68, 68, 0.1);
        color: var(--error);
      }

      .material-symbols-outlined {
        font-size: 1.125rem;
      }
    }

    /* Empty State */
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 4rem 2rem;
      text-align: center;

      .material-symbols-outlined {
        font-size: 4rem;
        color: var(--text-muted);
        margin-bottom: 1rem;
      }

      h3 {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
      }

      p {
        color: var(--text-secondary);
        margin-bottom: 1.5rem;
      }
    }

    /* Table Footer / Pagination */
    .table-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.25rem;
      background: var(--background);
      border-top: 1px solid var(--border);

      @media (max-width: 768px) {
        flex-direction: column;
        gap: 1rem;
      }
    }

    .pagination-info {
      font-size: 0.875rem;
      color: var(--text-muted);

      strong {
        color: var(--text-primary);
      }
    }

    .pagination-controls {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }

    .page-size-select {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      color: var(--text-muted);

      select {
        padding: 0.25rem 0.5rem;
        background: transparent;
        border: none;
        font-weight: 600;
        color: var(--text-primary);
        cursor: pointer;
      }
    }

    .page-nav {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .nav-btn {
      padding: 0.375rem;
      background: transparent;
      border: none;
      border-radius: 0.375rem;
      color: var(--text-primary);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover:not(:disabled) {
        background: var(--hover);
      }

      &:disabled {
        color: var(--text-muted);
        cursor: not-allowed;
      }

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .page-numbers {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .page-btn {
      min-width: 2rem;
      height: 2rem;
      padding: 0 0.5rem;
      font-size: 0.875rem;
      font-weight: 500;
      background: transparent;
      border: none;
      border-radius: 0.375rem;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover {
        background: var(--hover);
        color: var(--text-primary);
      }

      &.active {
        background: var(--primary);
        color: white;
      }
    }

    .ellipsis {
      padding: 0 0.5rem;
      color: var(--text-muted);
    }

    /* Bulk Actions Bar */
    .bulk-actions-bar {
      position: fixed;
      bottom: 1.5rem;
      left: 50%;
      transform: translateX(-50%);
      display: flex;
      align-items: center;
      gap: 2rem;
      padding: 0.75rem 1.5rem;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      box-shadow: var(--shadow-lg);
      z-index: 100;
      animation: slideUp 0.2s ease;
    }

    .selection-info {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-primary);

      .material-symbols-outlined {
        color: var(--primary);
      }

      .deselect-btn {
        margin-left: 0.5rem;
        padding: 0.25rem 0.5rem;
        font-size: 0.75rem;
        color: var(--text-muted);
        background: transparent;
        border: 1px solid var(--border);
        border-radius: 0.25rem;
        cursor: pointer;

        &:hover {
          background: var(--hover);
        }
      }
    }

    .bulk-buttons {
      display: flex;
      gap: 0.5rem;
    }

    .bulk-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.5rem 0.875rem;
      font-size: 0.8125rem;
      font-weight: 500;
      background: var(--background);
      border: 1px solid var(--border);
      border-radius: 0.375rem;
      color: var(--text-primary);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover {
        background: var(--hover);
      }

      &.danger {
        color: var(--error);
        border-color: rgba(239, 68, 68, 0.3);

        &:hover {
          background: rgba(239, 68, 68, 0.1);
        }
      }

      .material-symbols-outlined {
        font-size: 1rem;
      }

      .arrow {
        font-size: 1rem;
        margin-left: -0.125rem;
      }
    }

    .bulk-dropdown {
      position: relative;

      .dropdown-menu {
        position: absolute;
        bottom: calc(100% + 0.5rem);
        left: 0;
        min-width: 160px;
        padding: 0.5rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        box-shadow: var(--shadow-lg);
        opacity: 0;
        visibility: hidden;
        transform: translateY(10px);
        transition: all 0.2s ease;

        button {
          display: block;
          width: 100%;
          padding: 0.5rem 0.75rem;
          font-size: 0.8125rem;
          text-align: left;
          background: transparent;
          border: none;
          border-radius: 0.25rem;
          cursor: pointer;

          &:hover {
            background: var(--hover);
          }
        }
      }

      &.open .dropdown-menu {
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
      }
    }

    /* Modal Form */
    .modal-form {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .form-section {
      h4 {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
      }
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;

      @media (max-width: 640px) {
        grid-template-columns: 1fr;
      }
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;

      label {
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--text-secondary);

        .required {
          color: var(--error);
        }
      }

      input, select {
        padding: 0.625rem 0.75rem;
        font-size: 0.875rem;
        background: var(--background);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        color: var(--text-primary);
        transition: border-color 0.15s ease;

        &:focus {
          outline: none;
          border-color: var(--primary);
        }

        &::placeholder {
          color: var(--text-muted);
        }
      }

      select {
        cursor: pointer;
      }
    }

    .phone-input {
      display: flex;
      align-items: stretch;

      .country-code {
        display: flex;
        align-items: center;
        padding: 0 0.75rem;
        background: var(--hover);
        border: 1px solid var(--border);
        border-right: none;
        border-radius: 0.5rem 0 0 0.5rem;
        font-size: 0.875rem;
        color: var(--text-muted);
      }

      input {
        flex: 1;
        border-radius: 0 0.5rem 0.5rem 0;
      }
    }

    .password-input {
      position: relative;

      input {
        width: 100%;
        padding-right: 2.5rem;
      }

      .toggle-password {
        position: absolute;
        right: 0.5rem;
        top: 50%;
        transform: translateY(-50%);
        padding: 0.25rem;
        background: transparent;
        border: none;
        color: var(--text-muted);
        cursor: pointer;

        &:hover {
          color: var(--text-primary);
        }

        .material-symbols-outlined {
          font-size: 1.125rem;
        }
      }
    }

    .checkbox-group {
      display: flex;
      align-items: center;
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      color: var(--text-primary);
      cursor: pointer;

      input[type="checkbox"] {
        display: none;

        &:checked + .checkbox-custom {
          background: var(--primary);
          border-color: var(--primary);

          &::after {
            opacity: 1;
          }
        }
      }

      .checkbox-custom {
        width: 1.125rem;
        height: 1.125rem;
        border: 2px solid var(--border);
        border-radius: 0.25rem;
        position: relative;
        transition: all 0.15s ease;

        &::after {
          content: '';
          position: absolute;
          left: 3px;
          top: 0;
          width: 5px;
          height: 9px;
          border: solid white;
          border-width: 0 2px 2px 0;
          transform: rotate(45deg);
          opacity: 0;
          transition: opacity 0.15s ease;
        }
      }
    }

    .btn-spinner {
      display: inline-block;
      width: 1rem;
      height: 1rem;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-right: 0.5rem;
    }

    /* Impersonate Modal */
    .impersonate-content {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .impersonate-warning {
      display: flex;
      gap: 1rem;
      padding: 1rem;
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.2);
      border-radius: 0.5rem;

      .material-symbols-outlined {
        font-size: 1.5rem;
        color: #f59e0b;
        flex-shrink: 0;
      }

      h4 {
        font-size: 0.9375rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
      }

      p {
        font-size: 0.8125rem;
        color: var(--text-secondary);
      }
    }

    .impersonate-user-info {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1rem;
      background: var(--background);
      border-radius: 0.5rem;

      .user-details {
        h3 {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: 0.125rem;
        }

        p {
          font-size: 0.875rem;
          color: var(--text-secondary);
          margin-bottom: 0.5rem;
        }
      }
    }

    .impersonate-options {
      padding: 1rem;
      background: var(--background);
      border-radius: 0.5rem;

      .option-hint {
        margin-top: 0.5rem;
        font-size: 0.75rem;
        color: var(--text-muted);
        padding-left: 1.625rem;
      }
    }

    /* Context Menu */
    .context-menu {
      position: fixed;
      min-width: 180px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      box-shadow: var(--shadow-lg);
      padding: 0.5rem;
      z-index: 1000;

      button {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        width: 100%;
        padding: 0.625rem 0.75rem;
        font-size: 0.875rem;
        color: var(--text-primary);
        background: transparent;
        border: none;
        border-radius: 0.375rem;
        cursor: pointer;
        text-align: left;

        &:hover {
          background: var(--hover);
        }

        &.danger {
          color: var(--error);

          &:hover {
            background: rgba(239, 68, 68, 0.1);
          }
        }

        .material-symbols-outlined {
          font-size: 1.125rem;
          color: var(--text-muted);
        }

        &.danger .material-symbols-outlined {
          color: var(--error);
        }
      }

      hr {
        border: none;
        border-top: 1px solid var(--border);
        margin: 0.5rem 0;
      }
    }

    /* Responsive */
    .hide-sm {
      @media (max-width: 768px) {
        display: none;
      }
    }

    .hide-md {
      @media (max-width: 1024px) {
        display: none;
      }
    }

    .hide-lg {
      @media (max-width: 1200px) {
        display: none;
      }
    }

    /* Animations */
    @keyframes slideUp {
      from {
        opacity: 0;
        transform: translateX(-50%) translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateX(-50%) translateY(0);
      }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class UsersListComponent implements OnInit, OnDestroy {
  @ViewChild('userModal') userModal!: ModalComponent;
  @ViewChild('impersonateModal') impersonateModal!: ModalComponent;

  // Expose enums to template
  ExportFormat = ExportFormat;

  private adminService = inject(AdminService);
  private toastService = inject(ToastService);
  private destroy$ = new Subject<void>();
  private searchSubject = new Subject<string>();

  // State
  loading = signal(true);
  users = signal<User[]>([]);
  totalUsers = signal(0);
  currentPage = signal(1);

  // Stats
  stats = signal({
    total: 0,
    active: 0,
    students: 0,
    premium: 0
  });

  // Filters
  searchQuery = '';
  statusFilter = '';
  quickFilter = signal<string>('all');
  showAdvancedFilters = signal(false);
  showExportMenu = signal(false);
  showBulkSubscription = signal(false);

  filters: UserFilters = {
    page: 1,
    page_size: 25,
    sort_by: 'created_at',
    sort_order: 'desc'
  };

  provinces = ZIMBABWE_PROVINCES;

  // Selection
  selectedUsers = signal<string[]>([]);

  // Dialog state
  showConfirmDialog = signal(false);
  confirmDialogTitle = signal('');
  confirmDialogMessage = signal('');
  confirmDialogType = signal<'danger' | 'warning' | 'info'>('danger');
  pendingAction: (() => void) | null = null;

  // Form state
  isEditMode = false;
  isSaving = signal(false);
  showPassword = signal(false);
  editingUserId: string | null = null;

  userForm: CreateUserRequest = {
    email: '',
    phone_number: '',
    password: '',
    role: '',
    full_name: '',
    institution: ''
  };

  editForm: Partial<User> = {};

  // Impersonate
  impersonatingUser: User | null = null;
  impersonateReadOnly = true;
  isImpersonating = signal(false);

  // Context Menu
  contextMenu = signal<{ show: boolean; x: number; y: number; user: User | null }>({
    show: false, x: 0, y: 0, user: null
  });

  // Computed
  allSelected = computed(() => {
    const users = this.users();
    const selected = this.selectedUsers();
    return users.length > 0 && users.every(u => selected.includes(u.id));
  });

  someSelected = computed(() => {
    const users = this.users();
    const selected = this.selectedUsers();
    return selected.length > 0 && !users.every(u => selected.includes(u.id));
  });

  totalPages = computed(() => Math.ceil(this.totalUsers() / (this.filters.page_size || 25)));

  paginationStart = computed(() => {
    if (this.totalUsers() === 0) return 0;
    return (this.currentPage() - 1) * (this.filters.page_size || 25) + 1;
  });

  paginationEnd = computed(() => {
    return Math.min(this.currentPage() * (this.filters.page_size || 25), this.totalUsers());
  });

  visiblePages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: (number | string)[] = [];

    if (total <= 7) {
      for (let i = 1; i <= total; i++) pages.push(i);
    } else {
      if (current <= 3) {
        pages.push(1, 2, 3, 4, '...', total);
      } else if (current >= total - 2) {
        pages.push(1, '...', total - 3, total - 2, total - 1, total);
      } else {
        pages.push(1, '...', current - 1, current, current + 1, '...', total);
      }
    }
    return pages;
  });

  activeFilterCount = computed(() => {
    let count = 0;
    if (this.filters.role) count++;
    if (this.filters.subscription_tier) count++;
    if (this.filters.is_active !== undefined) count++;
    if (this.filters.is_verified !== undefined) count++;
    if (this.filters.education_level) count++;
    if (this.filters.province) count++;
    if (this.filters.district) count++;
    if (this.filters.school) count++;
    if (this.filters.registration_date_from || this.filters.registration_date_to) count++;
    if (this.filters.last_active_from || this.filters.last_active_to) count++;
    return count;
  });

  activeFilterTags = computed(() => {
    const tags: { key: string; label: string }[] = [];
    if (this.filters.role) tags.push({ key: 'role', label: `Role: ${this.filters.role}` });
    if (this.filters.subscription_tier) tags.push({ key: 'subscription_tier', label: `Tier: ${this.filters.subscription_tier}` });
    if (this.filters.is_active !== undefined) tags.push({ key: 'is_active', label: this.filters.is_active ? 'Active Only' : 'Inactive Only' });
    if (this.filters.is_verified !== undefined) tags.push({ key: 'is_verified', label: this.filters.is_verified ? 'Verified' : 'Unverified' });
    if (this.filters.education_level) tags.push({ key: 'education_level', label: `Level: ${this.filters.education_level}` });
    if (this.filters.province) tags.push({ key: 'province', label: this.filters.province });
    if (this.filters.district) tags.push({ key: 'district', label: `District: ${this.filters.district}` });
    if (this.filters.school) tags.push({ key: 'school', label: `School: ${this.filters.school}` });
    if (this.filters.registration_date_from || this.filters.registration_date_to) {
      tags.push({ key: 'registration_date', label: `Registered: ${this.filters.registration_date_from || 'Any'} - ${this.filters.registration_date_to || 'Any'}` });
    }
    if (this.filters.last_active_from || this.filters.last_active_to) {
      tags.push({ key: 'last_active', label: `Active: ${this.filters.last_active_from || 'Any'} - ${this.filters.last_active_to || 'Any'}` });
    }
    return tags;
  });

  ngOnInit(): void {
    this.setupSearchDebounce();
    this.loadUsers();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private setupSearchDebounce(): void {
    this.searchSubject.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      takeUntil(this.destroy$)
    ).subscribe(query => {
      this.filters.search = query || undefined;
      this.filters.page = 1;
      this.currentPage.set(1);
      this.loadUsers();
    });
  }

  loadUsers(): void {
    this.loading.set(true);

    this.adminService.getUsers(this.filters).subscribe({
      next: (response) => {
        if (response && response.items) {
          const usersWithStatus = response.items.map(user => ({
            ...user,
            status: (user.is_active ? 'active' : 'inactive') as 'active' | 'inactive' | 'suspended' | 'pending'
          }));
          this.users.set(usersWithStatus as User[]);
          this.totalUsers.set(response.total || 0);

          // Update stats
          this.stats.set({
            total: response.total || 0,
            active: usersWithStatus.filter(u => u.is_active).length,
            students: usersWithStatus.filter(u => u.role === 'student').length,
            premium: usersWithStatus.filter(u => ['premium', 'family', 'school'].includes(u.subscription_tier)).length
          });
        } else {
          this.users.set([]);
          this.totalUsers.set(0);
        }
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load users:', err);
        this.toastService.error('Failed to load users', 'Please try again');
        this.loading.set(false);
      }
    });
  }

  // Search and Filters
  onSearchChange(query: string): void {
    this.searchSubject.next(query);
  }

  clearSearch(): void {
    this.searchQuery = '';
    this.filters.search = undefined;
    this.applyFilters();
  }

  setQuickFilter(filter: string): void {
    this.quickFilter.set(filter);

    // Reset filters
    this.filters.role = undefined;
    this.filters.is_active = undefined;

    switch (filter) {
      case 'students':
        this.filters.role = 'student' as UserRole;
        break;
      case 'parents':
        this.filters.role = 'parent' as UserRole;
        break;
      case 'teachers':
        this.filters.role = 'teacher' as UserRole;
        break;
      case 'admins':
        this.filters.role = 'admin' as UserRole;
        break;
      case 'inactive':
        this.filters.is_active = false;
        break;
    }

    this.applyFilters();
  }

  toggleFilters(): void {
    this.showAdvancedFilters.update(v => !v);
  }

  applyFilters(): void {
    this.filters.page = 1;
    this.currentPage.set(1);
    this.loadUsers();
  }

  onFilterChange(): void {
    // Debounce text input filters
    setTimeout(() => this.applyFilters(), 300);
  }

  applyStatusFilter(): void {
    switch (this.statusFilter) {
      case 'active':
        this.filters.is_active = true;
        this.filters.is_verified = undefined;
        break;
      case 'inactive':
        this.filters.is_active = false;
        this.filters.is_verified = undefined;
        break;
      case 'verified':
        this.filters.is_verified = true;
        this.filters.is_active = undefined;
        break;
      case 'unverified':
        this.filters.is_verified = false;
        this.filters.is_active = undefined;
        break;
      default:
        this.filters.is_active = undefined;
        this.filters.is_verified = undefined;
    }
    this.applyFilters();
  }

  removeFilter(key: string): void {
    switch (key) {
      case 'role':
        this.filters.role = undefined;
        this.quickFilter.set('all');
        break;
      case 'subscription_tier':
        this.filters.subscription_tier = undefined;
        break;
      case 'is_active':
        this.filters.is_active = undefined;
        this.statusFilter = '';
        break;
      case 'is_verified':
        this.filters.is_verified = undefined;
        this.statusFilter = '';
        break;
      case 'education_level':
        this.filters.education_level = undefined;
        break;
      case 'province':
        this.filters.province = undefined;
        break;
      case 'district':
        this.filters.district = undefined;
        break;
      case 'school':
        this.filters.school = undefined;
        break;
      case 'registration_date':
        this.filters.registration_date_from = undefined;
        this.filters.registration_date_to = undefined;
        break;
      case 'last_active':
        this.filters.last_active_from = undefined;
        this.filters.last_active_to = undefined;
        break;
    }
    this.applyFilters();
  }

  resetFilters(): void {
    this.searchQuery = '';
    this.statusFilter = '';
    this.quickFilter.set('all');
    this.filters = {
      page: 1,
      page_size: this.filters.page_size,
      sort_by: 'created_at',
      sort_order: 'desc'
    };
    this.loadUsers();
  }

  // Sorting
  sortBy(field: string): void {
    if (this.filters.sort_by === field) {
      this.filters.sort_order = this.filters.sort_order === 'asc' ? 'desc' : 'asc';
    } else {
      this.filters.sort_by = field;
      this.filters.sort_order = 'asc';
    }
    this.loadUsers();
  }

  getSortIcon(field: string): string {
    if (this.filters.sort_by !== field) return '↕';
    return this.filters.sort_order === 'asc' ? '↑' : '↓';
  }

  // Pagination
  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
      this.filters.page = page;
      this.loadUsers();
    }
  }

  onPageSizeChange(): void {
    this.filters.page = 1;
    this.currentPage.set(1);
    this.loadUsers();
  }

  // Selection
  toggleSelectAll(): void {
    if (this.allSelected()) {
      this.selectedUsers.set([]);
    } else {
      this.selectedUsers.set(this.users().map(u => u.id));
    }
  }

  toggleSelect(userId: string): void {
    const current = this.selectedUsers();
    if (current.includes(userId)) {
      this.selectedUsers.set(current.filter(id => id !== userId));
    } else {
      this.selectedUsers.set([...current, userId]);
    }
  }

  isSelected(userId: string): boolean {
    return this.selectedUsers().includes(userId);
  }

  clearSelection(): void {
    this.selectedUsers.set([]);
  }

  // Export
  toggleExportMenu(): void {
    this.showExportMenu.update(v => !v);
  }

  exportUsers(format: ExportFormat): void {
    this.showExportMenu.set(false);
    this.toastService.info('Preparing Export', `Generating ${format.toUpperCase()} file...`);

    this.adminService.exportUsers(this.filters, format).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `users-export-${new Date().toISOString().split('T')[0]}.${format}`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.toastService.success('Export Complete', `Users exported as ${format.toUpperCase()}`);
      },
      error: (err) => {
        console.error('Export failed:', err);
        this.toastService.error('Export Failed', 'Please try again');
      }
    });
  }

  // Bulk Actions
  toggleBulkSubscription(): void {
    this.showBulkSubscription.update(v => !v);
  }

  bulkAction(action: string): void {
    const count = this.selectedUsers().length;
    const userIds = this.selectedUsers();

    const actionLabels: Record<string, { title: string; message: string; type: 'danger' | 'warning' | 'info' }> = {
      activate: { title: 'Activate Users', message: `Activate ${count} selected users?`, type: 'info' },
      deactivate: { title: 'Deactivate Users', message: `Deactivate ${count} selected users?`, type: 'warning' },
      verify: { title: 'Verify Users', message: `Mark ${count} users as verified?`, type: 'info' },
      upgrade: { title: 'Upgrade Users', message: `Upgrade ${count} users to Basic tier?`, type: 'info' },
      downgrade: { title: 'Downgrade Users', message: `Downgrade ${count} users to Free tier?`, type: 'warning' },
      delete: { title: 'Delete Users', message: `Permanently delete ${count} users? This action cannot be undone.`, type: 'danger' }
    };

    const config = actionLabels[action];
    this.confirmDialogTitle.set(config.title);
    this.confirmDialogMessage.set(config.message);
    this.confirmDialogType.set(config.type);

    this.pendingAction = () => {
      const bulkActionMap: Record<string, BulkAction> = {
        activate: BulkAction.ACTIVATE,
        deactivate: BulkAction.DEACTIVATE,
        verify: BulkAction.VERIFY,
        upgrade: BulkAction.UPGRADE,
        downgrade: BulkAction.DOWNGRADE,
        delete: BulkAction.DELETE
      };

      this.adminService.bulkUserAction({
        user_ids: userIds,
        action: bulkActionMap[action]
      }).subscribe({
        next: (response) => {
          const affected = response.successful || response.affected || count;
          this.toastService.success('Action Completed', `Successfully processed ${affected} users`);
          this.selectedUsers.set([]);
          this.showBulkSubscription.set(false);
          this.loadUsers();
        },
        error: (err) => {
          console.error('Bulk action failed:', err);
          this.toastService.error('Action Failed', 'Some users could not be processed');
        }
      });
    };

    this.showConfirmDialog.set(true);
  }

  // User Modal
  openAddUserModal(): void {
    this.isEditMode = false;
    this.editingUserId = null;
    this.resetUserForm();
    this.userModal.open();
  }

  openEditUserModal(user: User): void {
    this.isEditMode = true;
    this.editingUserId = user.id;
    this.userForm = {
      email: user.email,
      phone_number: user.phone_number,
      password: '',
      role: user.role,
      full_name: user.full_name || user.name || '',
      institution: user.institution || ''
    };
    this.editForm = {
      subscription_tier: user.subscription_tier,
      subscription_expires_at: user.subscription_expires_at,
      is_active: user.is_active,
      is_verified: user.is_verified
    };
    this.userModal.open();
  }

  resetUserForm(): void {
    this.userForm = {
      email: '',
      phone_number: '',
      password: '',
      role: '',
      full_name: '',
      institution: ''
    };
    this.editForm = {};
  }

  togglePasswordVisibility(): void {
    this.showPassword.update(v => !v);
  }

  saveUser(): void {
    if (!this.userForm.email || !this.userForm.phone_number || !this.userForm.role) {
      this.toastService.error('Validation Error', 'Please fill in all required fields');
      return;
    }

    if (!this.isEditMode && !this.userForm.password) {
      this.toastService.error('Validation Error', 'Password is required for new users');
      return;
    }

    this.isSaving.set(true);

    if (this.isEditMode && this.editingUserId) {
      const updateData: Partial<User> = {
        email: this.userForm.email,
        phone_number: this.userForm.phone_number,
        role: this.userForm.role as UserRole,
        full_name: this.userForm.full_name,
        institution: this.userForm.institution,
        ...this.editForm
      };

      this.adminService.updateUser(this.editingUserId, updateData).subscribe({
        next: () => {
          this.toastService.success('User Updated', 'Changes saved successfully');
          this.userModal.close();
          this.loadUsers();
          this.isSaving.set(false);
        },
        error: (err) => {
          console.error('Failed to update user:', err);
          this.toastService.error('Update Failed', 'Please try again');
          this.isSaving.set(false);
        }
      });
    } else {
      this.adminService.createUser(this.userForm).subscribe({
        next: () => {
          this.toastService.success('User Created', 'New user added successfully');
          this.userModal.close();
          this.loadUsers();
          this.isSaving.set(false);
        },
        error: (err) => {
          console.error('Failed to create user:', err);
          this.toastService.error('Creation Failed', 'Please try again');
          this.isSaving.set(false);
        }
      });
    }
  }

  // Impersonate
  openImpersonateModal(user: User): void {
    this.impersonatingUser = user;
    this.impersonateReadOnly = true;
    this.impersonateModal.open();
  }

  confirmImpersonate(): void {
    if (!this.impersonatingUser) return;

    this.isImpersonating.set(true);

    this.adminService.impersonateUser(this.impersonatingUser.id, this.impersonateReadOnly).subscribe({
      next: (response) => {
        const token = response.access_token || response.token;
        if (token) {
          localStorage.setItem('impersonation_token', token);
          localStorage.setItem('original_token', localStorage.getItem('access_token') || '');
          this.toastService.success('Impersonation Started', `Now viewing as ${this.getUserName(this.impersonatingUser!)}`);
        }
        this.impersonateModal.close();
        this.isImpersonating.set(false);
      },
      error: (err) => {
        console.error('Impersonation failed:', err);
        this.toastService.error('Impersonation Failed', 'Unable to impersonate this user');
        this.isImpersonating.set(false);
      }
    });
  }

  // Context Menu
  openContextMenu(user: User, event: MouseEvent): void {
    event.stopPropagation();
    this.contextMenu.set({
      show: true,
      x: event.clientX,
      y: event.clientY,
      user
    });
  }

  closeContextMenu(): void {
    this.contextMenu.set({ show: false, x: 0, y: 0, user: null });
  }

  contextAction(action: string): void {
    const user = this.contextMenu().user;
    if (!user) return;

    this.closeContextMenu();

    switch (action) {
      case 'view':
        window.location.href = `/users/${user.id}`;
        break;
      case 'edit':
        this.openEditUserModal(user);
        break;
      case 'activate':
        this.adminService.activateUser(user.id).subscribe({
          next: () => {
            this.toastService.success('User Activated');
            this.loadUsers();
          },
          error: () => this.toastService.error('Activation Failed')
        });
        break;
      case 'deactivate':
        this.adminService.suspendUser(user.id).subscribe({
          next: () => {
            this.toastService.success('User Deactivated');
            this.loadUsers();
          },
          error: () => this.toastService.error('Deactivation Failed')
        });
        break;
      case 'verify':
        this.adminService.verifyUser(user.id).subscribe({
          next: () => {
            this.toastService.success('User Verified');
            this.loadUsers();
          },
          error: () => this.toastService.error('Verification Failed')
        });
        break;
      case 'reset-password':
        this.confirmDialogTitle.set('Reset Password');
        this.confirmDialogMessage.set(`Send password reset email to ${user.email}?`);
        this.confirmDialogType.set('info');
        this.pendingAction = () => {
          this.adminService.resetUserPassword(user.id).subscribe({
            next: () => this.toastService.success('Password Reset', 'Reset email sent successfully'),
            error: () => this.toastService.error('Failed to send reset email')
          });
        };
        this.showConfirmDialog.set(true);
        break;
      case 'delete':
        this.confirmDialogTitle.set('Delete User');
        this.confirmDialogMessage.set(`Permanently delete ${this.getUserName(user)}? This action cannot be undone.`);
        this.confirmDialogType.set('danger');
        this.pendingAction = () => {
          this.adminService.deleteUser(user.id).subscribe({
            next: () => {
              this.toastService.success('User Deleted');
              this.loadUsers();
            },
            error: () => this.toastService.error('Delete Failed')
          });
        };
        this.showConfirmDialog.set(true);
        break;
    }
  }

  // Dialog
  onConfirmAction(): void {
    if (this.pendingAction) {
      this.pendingAction();
      this.pendingAction = null;
    }
    this.closeConfirmDialog();
  }

  closeConfirmDialog(): void {
    this.showConfirmDialog.set(false);
  }

  // Utilities
  getUserName(user: User): string {
    return user.full_name || user.name || user.student_name || user.email || 'Unknown User';
  }

  getInitials(user: User): string {
    const name = this.getUserName(user);
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .substring(0, 2);
  }

  getRoleIcon(role: string): string {
    const icons: Record<string, string> = {
      student: 'school',
      parent: 'family_restroom',
      teacher: 'person',
      admin: 'admin_panel_settings'
    };
    return icons[role] || 'person';
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  }

  formatRelativeDate(dateStr: string): string {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return this.formatDate(dateStr);
  }

  isInactiveRecently(dateStr: string): boolean {
    if (!dateStr) return true;
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / 86400000);
    return diffDays > 30;
  }
}
