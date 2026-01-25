import { Component, inject, OnInit, signal, computed, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AdminService } from '../../../core/services/admin.service';
import { ToastService } from '../../../core/services/toast.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { AdminUser, CreateAdminRequest, UserRole } from '../../../core/models';

@Component({
  selector: 'app-admins-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    PageHeaderComponent,
    LoadingSpinnerComponent,
    ConfirmDialogComponent,
    ModalComponent
  ],
  template: `
    <div class="admins-page">
      <app-page-header
        title="Administrators"
        description="Manage admin users and their permissions for the EduBot platform."
        [breadcrumbs]="[
          { label: 'Home', link: '/dashboard' },
          { label: 'Users', link: '/users' },
          { label: 'Administrators' }
        ]"
      >
        <div headerActions>
          <button class="btn btn-primary" (click)="openAddAdminModal()">
            <span class="material-symbols-outlined">add</span>
            Add Administrator
          </button>
        </div>
      </app-page-header>

      <!-- Stats -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon blue">
            <span class="material-symbols-outlined">admin_panel_settings</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ admins().length }}</span>
            <span class="stat-label">Total Admins</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon green">
            <span class="material-symbols-outlined">verified_user</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ getActiveCount() }}</span>
            <span class="stat-label">Active</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon red">
            <span class="material-symbols-outlined">person_off</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ getInactiveCount() }}</span>
            <span class="stat-label">Inactive</span>
          </div>
        </div>
      </div>

      <!-- Filters -->
      <div class="filters-card">
        <div class="search-input">
          <span class="material-symbols-outlined">search</span>
          <input
            type="text"
            placeholder="Search by name or email..."
            [(ngModel)]="searchQuery"
            (input)="applyFilters()"
          />
        </div>
        <div class="select-wrapper">
          <select [(ngModel)]="statusFilter" (change)="applyFilters()">
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <span class="material-symbols-outlined">expand_more</span>
        </div>
      </div>

      <!-- Admins Table -->
      <div class="table-card">
        @if (loading()) {
          <app-loading-spinner message="Loading administrators..." />
        } @else {
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Administrator</th>
                  <th>Phone</th>
                  <th>Created</th>
                  <th>Last Active</th>
                  <th>Status</th>
                  <th class="actions-col">Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (admin of filteredAdmins(); track admin.id) {
                  <tr>
                    <td>
                      <div class="admin-info">
                        <div class="admin-avatar">
                          {{ getInitials(admin.name || admin.email || 'U') }}
                        </div>
                        <div class="admin-details">
                          <span class="admin-name">{{ admin.name || admin.email.split('@')[0] }}</span>
                          <span class="admin-email">{{ admin.email }}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span class="phone-number">{{ admin.phone_number || '-' }}</span>
                    </td>
                    <td>
                      <span class="date-text">{{ formatDate(admin.created_at) }}</span>
                    </td>
                    <td>
                      <span class="last-login">{{ formatDate(admin.last_login || admin.last_active || '') }}</span>
                    </td>
                    <td>
                      <span class="status-badge" [class.active]="admin.is_active" [class.inactive]="!admin.is_active">
                        <span class="status-dot"></span>
                        {{ admin.is_active ? 'Active' : 'Inactive' }}
                      </span>
                    </td>
                    <td class="actions-col">
                      <div class="action-buttons">
                        <button
                          class="action-btn"
                          title="Edit"
                          (click)="openEditAdminModal(admin)"
                        >
                          <span class="material-symbols-outlined">edit</span>
                        </button>
                        @if (admin.is_active) {
                          <button
                            class="action-btn danger"
                            title="Deactivate"
                            (click)="confirmDeleteAdmin(admin)"
                          >
                            <span class="material-symbols-outlined">person_off</span>
                          </button>
                        } @else {
                          <button
                            class="action-btn success"
                            title="Reactivate"
                            (click)="reactivateAdmin(admin)"
                          >
                            <span class="material-symbols-outlined">person_add</span>
                          </button>
                        }
                      </div>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="6">
                      <div class="empty-state">
                        <span class="material-symbols-outlined">admin_panel_settings</span>
                        <p class="empty-title">No administrators found</p>
                        <p class="empty-desc">Add a new administrator to get started</p>
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>

      <!-- Deactivate Confirm Dialog -->
      <app-confirm-dialog
        [isOpen]="showDeleteDialog()"
        title="Deactivate Administrator"
        [message]="'Are you sure you want to deactivate ' + (adminToDelete()?.name || adminToDelete()?.email || '') + '? They will no longer be able to log in.'"
        type="warning"
        confirmText="Deactivate"
        (confirm)="deleteAdmin()"
        (cancel)="closeDeleteDialog()"
      />

      <!-- Add/Edit Admin Modal -->
      <app-modal #adminModal [title]="isEditMode ? 'Edit Administrator' : 'Add New Administrator'" size="md">
        <form (ngSubmit)="saveAdmin()">
          <div class="form-grid">
            <div class="form-group full-width">
              <label for="email">Email Address *</label>
              <input
                type="email"
                id="email"
                [(ngModel)]="adminForm.email"
                name="email"
                placeholder="admin@edubot.co.zw"
                required
              />
            </div>
            <div class="form-group">
              <label for="phone">Phone Number</label>
              <input
                type="tel"
                id="phone"
                [(ngModel)]="adminForm.phone_number"
                name="phone_number"
                placeholder="+263771234567"
              />
            </div>
            @if (!isEditMode) {
              <div class="form-group">
                <label for="password">Password *</label>
                <div class="password-field">
                  <input
                    [type]="showPassword() ? 'text' : 'password'"
                    id="password"
                    [(ngModel)]="adminForm.password"
                    name="password"
                    placeholder="Min. 8 characters"
                    minlength="8"
                    required
                  />
                  <button type="button" class="toggle-password" (click)="showPassword.set(!showPassword())">
                    <span class="material-symbols-outlined">
                      {{ showPassword() ? 'visibility_off' : 'visibility' }}
                    </span>
                  </button>
                </div>
              </div>
            } @else {
              <div class="form-group">
                <label for="password">New Password</label>
                <div class="password-field">
                  <input
                    [type]="showPassword() ? 'text' : 'password'"
                    id="password"
                    [(ngModel)]="adminForm.password"
                    name="password"
                    placeholder="Leave blank to keep current"
                    minlength="8"
                  />
                  <button type="button" class="toggle-password" (click)="showPassword.set(!showPassword())">
                    <span class="material-symbols-outlined">
                      {{ showPassword() ? 'visibility_off' : 'visibility' }}
                    </span>
                  </button>
                </div>
              </div>
            }
            @if (isEditMode) {
              <div class="form-group full-width">
                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    [(ngModel)]="editingIsActive"
                    name="is_active"
                  />
                  <span>Active Account</span>
                </label>
                <p class="form-hint">Inactive admins cannot log in to the system.</p>
              </div>
            }
          </div>
        </form>
        <div modal-footer>
          <button type="button" class="btn btn-secondary" (click)="adminModal.close()">Cancel</button>
          <button type="button" class="btn btn-primary" (click)="saveAdmin()" [disabled]="isSaving()">
            @if (isSaving()) {
              <span class="spinner-sm"></span>
            }
            {{ isEditMode ? 'Update Admin' : 'Create Admin' }}
          </button>
        </div>
      </app-modal>
    </div>
  `,
  styles: [`
    .admins-page {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .stats-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
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
      border-radius: 0.75rem;

      &.blue {
        background-color: rgba(59, 130, 246, 0.1);
        .material-symbols-outlined { color: #3b82f6; }
      }

      &.green {
        background-color: rgba(16, 185, 129, 0.1);
        .material-symbols-outlined { color: #10b981; }
      }

      &.purple {
        background-color: rgba(168, 85, 247, 0.1);
        .material-symbols-outlined { color: #a855f7; }
      }

      &.red {
        background-color: rgba(239, 68, 68, 0.1);
        .material-symbols-outlined { color: #ef4444; }
      }
    }

    .stat-info {
      display: flex;
      flex-direction: column;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text-primary);
    }

    .stat-label {
      font-size: 0.75rem;
      color: var(--text-secondary);
    }

    .filters-card {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
      padding: 1rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
    }

    .search-input {
      position: relative;
      flex: 1;
      min-width: 280px;

      .material-symbols-outlined {
        position: absolute;
        left: 0.75rem;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text-muted);
        font-size: 1.25rem;
      }

      input {
        width: 100%;
        padding: 0.625rem 1rem 0.625rem 2.5rem;
        background-color: var(--background);
        border: 1px solid transparent;
        border-radius: 0.5rem;
        font-size: 0.875rem;
        transition: border-color 0.15s ease;

        &:focus {
          border-color: var(--primary);
        }
      }
    }

    .select-wrapper {
      position: relative;
      min-width: 160px;

      select {
        width: 100%;
        padding: 0.625rem 2rem 0.625rem 0.75rem;
        background-color: var(--background);
        border: 1px solid transparent;
        border-radius: 0.5rem;
        font-size: 0.875rem;
        appearance: none;
        cursor: pointer;

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

    .table-card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }

    .table-container {
      overflow-x: auto;
    }

    table {
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
        background-color: var(--background);
        white-space: nowrap;
      }

      td {
        font-size: 0.875rem;
      }

      tbody tr {
        transition: background-color 0.15s ease;

        &:hover {
          background-color: var(--background);
        }
      }
    }

    .admin-info {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .admin-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background-color: var(--primary);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.875rem;
      font-weight: 600;
      flex-shrink: 0;
    }

    .admin-details {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .admin-name {
      font-weight: 600;
      color: var(--text-primary);
    }

    .admin-email {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .role-badge {
      display: inline-flex;
      padding: 0.25rem 0.75rem;
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 9999px;
      border: 1px solid;

      &.super_admin, &.superadmin {
        background-color: rgba(168, 85, 247, 0.1);
        color: #a855f7;
        border-color: rgba(168, 85, 247, 0.2);
      }

      &.admin {
        background-color: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
        border-color: rgba(59, 130, 246, 0.2);
      }

      &.moderator {
        background-color: rgba(245, 158, 11, 0.1);
        color: #f59e0b;
        border-color: rgba(245, 158, 11, 0.2);
      }
    }

    .permissions-list {
      display: flex;
      flex-wrap: wrap;
      gap: 0.25rem;
    }

    .perm-badge {
      padding: 0.125rem 0.5rem;
      font-size: 0.6875rem;
      background-color: var(--background);
      color: var(--text-secondary);
      border-radius: 0.25rem;
    }

    .perm-more {
      padding: 0.125rem 0.5rem;
      font-size: 0.6875rem;
      background-color: var(--primary);
      color: white;
      border-radius: 0.25rem;
    }

    .last-login {
      font-family: monospace;
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.25rem 0.625rem;
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 9999px;
      border: 1px solid;

      .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
      }

      &.active {
        background-color: rgba(16, 185, 129, 0.1);
        color: #10b981;
        border-color: rgba(16, 185, 129, 0.2);

        .status-dot { background-color: #10b981; }
      }

      &.inactive {
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
        border-color: rgba(239, 68, 68, 0.2);

        .status-dot { background-color: #ef4444; }
      }
    }

    .actions-col {
      width: 100px;
      text-align: right;
    }

    .action-buttons {
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
        color: #ef4444;
      }

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 3rem;
      text-align: center;

      .material-symbols-outlined {
        font-size: 3rem;
        color: var(--text-muted);
        margin-bottom: 1rem;
      }

      .empty-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
      }

      .empty-desc {
        font-size: 0.875rem;
        color: var(--text-muted);
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

      &.full-width {
        grid-column: 1 / -1;
      }

      label {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-secondary);
      }

      input, select {
        padding: 0.625rem 0.75rem;
        background-color: var(--background);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        font-size: 0.875rem;
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

    .permissions-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 0.5rem;
      padding: 0.75rem;
      background-color: var(--background);
      border-radius: 0.5rem;

      @media (max-width: 640px) {
        grid-template-columns: 1fr;
      }
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      font-size: 0.875rem;
      color: var(--text-secondary);

      input[type="checkbox"] {
        width: 1rem;
        height: 1rem;
        accent-color: var(--primary);
      }
    }

    .password-field {
      position: relative;
      display: flex;
      align-items: center;

      input {
        padding-right: 2.5rem;
      }

      .toggle-password {
        position: absolute;
        right: 0.5rem;
        padding: 0.25rem;
        background: transparent;
        border: none;
        color: var(--text-muted);
        cursor: pointer;
        border-radius: 0.25rem;

        &:hover {
          color: var(--text-primary);
          background-color: var(--background);
        }

        .material-symbols-outlined {
          font-size: 1.25rem;
        }
      }
    }

    .form-hint {
      margin-top: 0.25rem;
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .phone-number {
      font-family: monospace;
      font-size: 0.8125rem;
      color: var(--text-secondary);
    }

    .date-text {
      font-size: 0.8125rem;
      color: var(--text-secondary);
    }

    .action-btn.success:hover {
      background-color: rgba(16, 185, 129, 0.1);
      color: #10b981;
    }

    .spinner-sm {
      display: inline-block;
      width: 1rem;
      height: 1rem;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-right: 0.5rem;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class AdminsListComponent implements OnInit {
  @ViewChild('adminModal') adminModal!: ModalComponent;
  private adminService = inject(AdminService);
  private toastService = inject(ToastService);

  // State
  loading = signal(true);
  admins = signal<AdminUser[]>([]);
  filteredAdmins = signal<AdminUser[]>([]);

  // Filters
  searchQuery = '';
  statusFilter = '';

  // Dialog state
  showDeleteDialog = signal(false);
  adminToDelete = signal<AdminUser | null>(null);

  // Form state
  isEditMode = false;
  isSaving = signal(false);
  showPassword = signal(false);
  editingAdminId: string | null = null;
  editingIsActive = true;
  adminForm: CreateAdminRequest = {
    email: '',
    password: '',
    phone_number: ''
  };


  ngOnInit(): void {
    this.loadAdmins();
  }

  loadAdmins(): void {
    this.loading.set(true);

    this.adminService.getAdmins().subscribe({
      next: (admins) => {
        this.admins.set(Array.isArray(admins) ? admins : []);
        this.applyFilters();
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load admins:', err);
        // Fallback to mock data for development
        this.admins.set([
          {
            id: '1',
            email: 'superadmin@edubot.co.zw',
            name: 'John Moyo',
            phone_number: '+263771234567',
            role: 'admin' as UserRole,
            permissions: [],
            created_at: '2024-01-01T00:00:00Z',
            last_login: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
            is_active: true,
            is_verified: true
          },
          {
            id: '2',
            email: 'admin@edubot.co.zw',
            name: 'Sarah Ndlovu',
            phone_number: '+263772345678',
            role: 'admin' as UserRole,
            permissions: [],
            created_at: '2024-02-15T00:00:00Z',
            last_login: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
            is_active: true,
            is_verified: true
          },
          {
            id: '3',
            email: 'support@edubot.co.zw',
            name: 'Grace Mutasa',
            phone_number: '+263773456789',
            role: 'admin' as UserRole,
            permissions: [],
            created_at: '2024-04-01T00:00:00Z',
            last_login: '',
            is_active: false,
            is_verified: true
          }
        ]);
        this.applyFilters();
        this.loading.set(false);
      }
    });
  }

  applyFilters(): void {
    let result = this.admins();

    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      result = result.filter(a =>
        (a.name || '').toLowerCase().includes(q) ||
        a.email.toLowerCase().includes(q) ||
        (a.phone_number || '').toLowerCase().includes(q)
      );
    }

    if (this.statusFilter) {
      if (this.statusFilter === 'active') {
        result = result.filter(a => a.is_active);
      } else if (this.statusFilter === 'inactive') {
        result = result.filter(a => !a.is_active);
      }
    }

    this.filteredAdmins.set(result);
  }

  getInitials(name: string): string {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .substring(0, 2);
  }

  formatRole(role: string): string {
    return role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getActiveCount(): number {
    return this.admins().filter(a => a.is_active).length;
  }

  getInactiveCount(): number {
    return this.admins().filter(a => !a.is_active).length;
  }

  openAddAdminModal(): void {
    this.isEditMode = false;
    this.editingAdminId = null;
    this.resetAdminForm();
    this.adminModal.open();
  }

  openEditAdminModal(admin: AdminUser): void {
    this.isEditMode = true;
    this.editingAdminId = admin.id;
    this.editingIsActive = admin.is_active;
    this.adminForm = {
      email: admin.email,
      password: '',
      phone_number: admin.phone_number || ''
    };
    this.showPassword.set(false);
    this.adminModal.open();
  }

  resetAdminForm(): void {
    this.adminForm = {
      email: '',
      password: '',
      phone_number: ''
    };
    this.editingIsActive = true;
    this.showPassword.set(false);
  }

  saveAdmin(): void {
    if (!this.adminForm.email) {
      this.toastService.error('Validation Error', 'Email is required');
      return;
    }

    if (!this.isEditMode && !this.adminForm.password) {
      this.toastService.error('Validation Error', 'Password is required for new administrators');
      return;
    }

    if (!this.isEditMode && this.adminForm.password && this.adminForm.password.length < 8) {
      this.toastService.error('Validation Error', 'Password must be at least 8 characters');
      return;
    }

    this.isSaving.set(true);

    if (this.isEditMode && this.editingAdminId) {
      const updateData: any = {
        email: this.adminForm.email,
        is_active: this.editingIsActive
      };
      if (this.adminForm.password) {
        updateData.password = this.adminForm.password;
      }

      this.adminService.updateAdmin(this.editingAdminId, updateData).subscribe({
        next: (response) => {
          this.toastService.success('Admin Updated', response.message || 'Administrator has been updated successfully');
          this.adminModal.close();
          this.loadAdmins();
          this.isSaving.set(false);
        },
        error: (err) => {
          console.error('Failed to update admin:', err);
          this.toastService.error('Update Failed', err?.error?.detail || 'Failed to update administrator');
          this.isSaving.set(false);
        }
      });
    } else {
      this.adminService.createAdmin({
        email: this.adminForm.email,
        password: this.adminForm.password || '',
        phone_number: this.adminForm.phone_number
      }).subscribe({
        next: (response) => {
          if (response.success) {
            this.toastService.success('Admin Created', response.message || 'New administrator has been created');
            this.adminModal.close();
            this.loadAdmins();
          } else {
            this.toastService.error('Creation Failed', response.error || 'Failed to create administrator');
          }
          this.isSaving.set(false);
        },
        error: (err) => {
          console.error('Failed to create admin:', err);
          this.toastService.error('Creation Failed', err?.error?.detail || 'Failed to create administrator');
          this.isSaving.set(false);
        }
      });
    }
  }

  confirmDeleteAdmin(admin: AdminUser): void {
    this.adminToDelete.set(admin);
    this.showDeleteDialog.set(true);
  }

  deleteAdmin(): void {
    const admin = this.adminToDelete();
    if (!admin) return;

    this.adminService.deleteAdmin(admin.id).subscribe({
      next: (response) => {
        if (response.success) {
          this.toastService.success('Admin Deactivated', `${admin.name || admin.email} has been deactivated`);
          this.loadAdmins();
        } else {
          this.toastService.error('Deactivation Failed', response.error || 'Failed to deactivate administrator');
        }
        this.closeDeleteDialog();
      },
      error: (err) => {
        console.error('Failed to deactivate admin:', err);
        this.toastService.error('Deactivation Failed', err?.error?.detail || 'Failed to deactivate administrator');
        this.closeDeleteDialog();
      }
    });
  }

  closeDeleteDialog(): void {
    this.showDeleteDialog.set(false);
    this.adminToDelete.set(null);
  }

  reactivateAdmin(admin: AdminUser): void {
    this.adminService.reactivateAdmin(admin.id).subscribe({
      next: () => {
        this.toastService.success('Admin Reactivated', `${admin.name || admin.email} has been reactivated`);
        this.loadAdmins();
      },
      error: (err) => {
        console.error('Failed to reactivate admin:', err);
        this.toastService.error('Reactivation Failed', err?.error?.detail || 'Failed to reactivate administrator');
      }
    });
  }
}
