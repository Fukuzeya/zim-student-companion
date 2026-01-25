import { Component, inject, signal, OnInit, computed, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../../../core/services/admin.service';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { User, UserDetail, UserRole, BulkAction, ZIMBABWE_PROVINCES } from '../../../core/models';
import { SubscriptionTier } from '../../../core/models/auth.models';

interface ActivityItem {
  id: string;
  type: 'login' | 'update' | 'payment' | 'session' | 'achievement' | 'action';
  title: string;
  description: string;
  timestamp: string;
  icon: string;
  color: string;
}

@Component({
  selector: 'app-user-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, ConfirmDialogComponent, ModalComponent],
  template: `
    <div class="user-detail-page">
      <!-- Header -->
      <header class="page-header">
        <div class="header-nav">
          <button class="back-btn" routerLink="/users">
            <span class="material-symbols-outlined">arrow_back</span>
          </button>
          <div class="breadcrumb">
            <a routerLink="/dashboard">Dashboard</a>
            <span class="separator">/</span>
            <a routerLink="/users">Users</a>
            <span class="separator">/</span>
            <span class="current">User Details</span>
          </div>
        </div>
        <div class="header-actions">
          @if (!isEditing()) {
            <button class="btn btn-outline" (click)="refreshData()">
              <span class="material-symbols-outlined">refresh</span>
              Refresh
            </button>
            <button class="btn btn-outline" (click)="startEditing()">
              <span class="material-symbols-outlined">edit</span>
              Edit
            </button>
            @if (user()?.is_active && user()?.role !== 'admin') {
              <button class="btn btn-warning" (click)="openImpersonateDialog()">
                <span class="material-symbols-outlined">supervisor_account</span>
                Impersonate
              </button>
            }
          } @else {
            <button class="btn btn-outline" (click)="cancelEditing()">Cancel</button>
            <button class="btn btn-primary" (click)="saveChanges()" [disabled]="isSaving()">
              @if (isSaving()) {
                <span class="spinner-sm"></span>
              }
              Save Changes
            </button>
          }
        </div>
      </header>

      @if (isLoading()) {
        <div class="loading-container">
          <div class="loading-spinner"></div>
          <p>Loading user details...</p>
        </div>
      } @else if (user()) {
        <div class="content-layout">
          <!-- Main Content -->
          <main class="main-content">
            <!-- Profile Card -->
            <section class="profile-card">
              <div class="profile-header">
                <div class="avatar-section">
                  <div class="avatar-wrapper">
                    <div class="avatar" [class]="user()!.role">
                      @if (user()!.avatar_url) {
                        <img [src]="user()!.avatar_url" [alt]="getUserName()" />
                      } @else {
                        {{ getInitials() }}
                      }
                    </div>
                    @if (user()!.is_verified) {
                      <span class="verified-badge" title="Verified Account">
                        <span class="material-symbols-outlined">verified</span>
                      </span>
                    }
                  </div>
                  <div class="profile-info">
                    <h1 class="user-name">{{ getUserName() }}</h1>
                    <p class="user-email">{{ user()!.email || 'No email' }}</p>
                    <div class="profile-badges">
                      <span class="badge role-badge" [class]="user()!.role">
                        <span class="material-symbols-outlined">{{ getRoleIcon() }}</span>
                        {{ user()!.role | titlecase }}
                      </span>
                      <span class="badge subscription-badge" [class]="user()!.subscription_tier">
                        {{ user()!.subscription_tier | titlecase }}
                      </span>
                      <span class="badge status-badge" [class]="user()!.is_active ? 'active' : 'inactive'">
                        <span class="status-dot"></span>
                        {{ user()!.is_active ? 'Active' : 'Inactive' }}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="profile-stats">
                  <div class="stat-item">
                    <span class="stat-value">{{ userStats().sessions | number }}</span>
                    <span class="stat-label">Sessions</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ userStats().questions | number }}</span>
                    <span class="stat-label">Questions</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ userStats().achievements | number }}</span>
                    <span class="stat-label">Achievements</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">\${{ userStats().payments | number:'1.2-2' }}</span>
                    <span class="stat-label">Total Spent</span>
                  </div>
                </div>
              </div>
            </section>

            <!-- Account Information -->
            <section class="card">
              <div class="card-header">
                <h2>
                  <span class="material-symbols-outlined">person</span>
                  Account Information
                </h2>
              </div>
              <div class="card-body">
                <div class="info-grid">
                  <div class="info-item">
                    <label>User ID</label>
                    <div class="info-value with-copy">
                      <code>{{ user()!.id }}</code>
                      <button class="copy-btn" (click)="copyToClipboard(user()!.id)" title="Copy ID">
                        <span class="material-symbols-outlined">content_copy</span>
                      </button>
                    </div>
                  </div>
                  <div class="info-item">
                    <label>Email Address</label>
                    @if (isEditing()) {
                      <input type="email" [(ngModel)]="editData.email" placeholder="user@example.com" />
                    } @else {
                      <span class="info-value">{{ user()!.email || 'Not set' }}</span>
                    }
                  </div>
                  <div class="info-item">
                    <label>Phone Number</label>
                    @if (isEditing()) {
                      <input type="tel" [(ngModel)]="editData.phone_number" placeholder="+263 7X XXX XXXX" />
                    } @else {
                      <span class="info-value">{{ user()!.phone_number }}</span>
                    }
                  </div>
                  <div class="info-item">
                    <label>WhatsApp ID</label>
                    <span class="info-value mono">{{ user()!.whatsapp_id || 'Not linked' }}</span>
                  </div>
                  <div class="info-item">
                    <label>Role</label>
                    @if (isEditing()) {
                      <select [(ngModel)]="editData.role">
                        <option value="student">Student</option>
                        <option value="parent">Parent</option>
                        <option value="teacher">Teacher</option>
                        <option value="admin">Administrator</option>
                      </select>
                    } @else {
                      <span class="info-value capitalize">{{ user()!.role }}</span>
                    }
                  </div>
                  <div class="info-item">
                    <label>Institution</label>
                    @if (isEditing()) {
                      <input type="text" [(ngModel)]="editData.institution" placeholder="School or organization" />
                    } @else {
                      <span class="info-value">{{ user()!.institution || user()!.school || 'Not specified' }}</span>
                    }
                  </div>
                </div>
              </div>
            </section>

            <!-- Student Details (if applicable) -->
            @if (user()!.student || user()!.role === 'student') {
              <section class="card">
                <div class="card-header">
                  <h2>
                    <span class="material-symbols-outlined">school</span>
                    Student Profile
                  </h2>
                </div>
                <div class="card-body">
                  <div class="info-grid">
                    <div class="info-item">
                      <label>Full Name</label>
                      <span class="info-value">{{ user()!.student?.full_name || getUserName() }}</span>
                    </div>
                    <div class="info-item">
                      <label>Grade / Form</label>
                      <span class="info-value">{{ user()!.student?.grade || user()!.grade || 'Not set' }}</span>
                    </div>
                    <div class="info-item">
                      <label>Education Level</label>
                      <span class="info-value capitalize">{{ formatEducationLevel(user()!.student?.education_level) }}</span>
                    </div>
                    <div class="info-item">
                      <label>School</label>
                      <span class="info-value">{{ user()!.student?.school_name || user()!.school || 'Not specified' }}</span>
                    </div>
                    <div class="info-item">
                      <label>Province</label>
                      <span class="info-value">{{ user()!.student?.province || 'Not specified' }}</span>
                    </div>
                    <div class="info-item">
                      <label>District</label>
                      <span class="info-value">{{ user()!.student?.district || 'Not specified' }}</span>
                    </div>
                    <div class="info-item full-width">
                      <label>Subjects</label>
                      <div class="subjects-list">
                        @if (user()!.student?.subjects?.length || user()!.subjects?.length) {
                          @for (subject of (user()!.student?.subjects || user()!.subjects || []); track subject) {
                            <span class="subject-tag">{{ subject }}</span>
                          }
                        } @else {
                          <span class="info-value muted">No subjects selected</span>
                        }
                      </div>
                    </div>
                    <div class="info-item">
                      <label>Total XP</label>
                      <span class="info-value xp-value">
                        <span class="material-symbols-outlined">star</span>
                        {{ user()!.student?.total_xp || 0 | number }} XP
                      </span>
                    </div>
                    <div class="info-item">
                      <label>Level</label>
                      <span class="info-value level-badge">Level {{ user()!.student?.level || 1 }}</span>
                    </div>
                    <div class="info-item">
                      <label>Daily Goal</label>
                      <span class="info-value">{{ user()!.student?.daily_goal_minutes || 30 }} minutes</span>
                    </div>
                    <div class="info-item">
                      <label>Preferred Language</label>
                      <span class="info-value capitalize">{{ user()!.student?.preferred_language || 'English' }}</span>
                    </div>
                  </div>
                </div>
              </section>
            }

            <!-- Subscription Details -->
            <section class="card">
              <div class="card-header">
                <h2>
                  <span class="material-symbols-outlined">card_membership</span>
                  Subscription
                </h2>
                @if (isEditing()) {
                  <span class="header-hint">Changes will take effect immediately</span>
                }
              </div>
              <div class="card-body">
                <div class="subscription-display">
                  <div class="current-plan">
                    <div class="plan-icon" [class]="user()!.subscription_tier">
                      <span class="material-symbols-outlined">{{ getSubscriptionIcon() }}</span>
                    </div>
                    <div class="plan-info">
                      <h3>{{ user()!.subscription_tier | titlecase }} Plan</h3>
                      <p>{{ getSubscriptionDescription() }}</p>
                    </div>
                  </div>
                  @if (isEditing()) {
                    <div class="subscription-edit">
                      <div class="info-item">
                        <label>Subscription Tier</label>
                        <select [(ngModel)]="editData.subscription_tier">
                          <option value="free">Free</option>
                          <option value="basic">Basic</option>
                          <option value="premium">Premium</option>
                          <option value="family">Family</option>
                          <option value="school">School</option>
                        </select>
                      </div>
                      <div class="info-item">
                        <label>Expiry Date</label>
                        <input type="date" [(ngModel)]="editData.subscription_expires_at" />
                      </div>
                    </div>
                  } @else {
                    <div class="subscription-details">
                      @if (user()!.subscription_expires_at) {
                        <div class="expiry-info" [class.expiring-soon]="isExpiringSoon()">
                          <span class="material-symbols-outlined">schedule</span>
                          <span>
                            @if (isExpired()) {
                              Expired on {{ formatDate(user()!.subscription_expires_at) }}
                            } @else {
                              Expires {{ formatRelativeDate(user()!.subscription_expires_at) }}
                            }
                          </span>
                        </div>
                      }
                    </div>
                  }
                </div>
              </div>
            </section>

            <!-- Activity Timeline -->
            <section class="card">
              <div class="card-header">
                <h2>
                  <span class="material-symbols-outlined">history</span>
                  Recent Activity
                </h2>
                <button class="btn btn-text" (click)="loadMoreActivity()">View All</button>
              </div>
              <div class="card-body no-padding">
                <div class="activity-timeline">
                  @for (activity of recentActivity(); track activity.id) {
                    <div class="activity-item">
                      <div class="activity-icon" [style.background]="activity.color">
                        <span class="material-symbols-outlined">{{ activity.icon }}</span>
                      </div>
                      <div class="activity-content">
                        <h4>{{ activity.title }}</h4>
                        <p>{{ activity.description }}</p>
                        <span class="activity-time">{{ formatRelativeDate(activity.timestamp) }}</span>
                      </div>
                    </div>
                  } @empty {
                    <div class="empty-activity">
                      <span class="material-symbols-outlined">event_busy</span>
                      <p>No recent activity</p>
                    </div>
                  }
                </div>
              </div>
            </section>
          </main>

          <!-- Sidebar -->
          <aside class="sidebar">
            <!-- Quick Actions -->
            <section class="card">
              <div class="card-header">
                <h2>
                  <span class="material-symbols-outlined">bolt</span>
                  Quick Actions
                </h2>
              </div>
              <div class="card-body">
                <div class="quick-actions">
                  <button class="action-btn" (click)="sendPasswordReset()">
                    <span class="material-symbols-outlined">lock_reset</span>
                    Reset Password
                  </button>
                  @if (!user()!.is_verified) {
                    <button class="action-btn" (click)="verifyUser()">
                      <span class="material-symbols-outlined">verified</span>
                      Verify Email
                    </button>
                  }
                  @if (user()!.is_active) {
                    <button class="action-btn warning" (click)="deactivateUser()">
                      <span class="material-symbols-outlined">person_off</span>
                      Deactivate Account
                    </button>
                  } @else {
                    <button class="action-btn success" (click)="activateUser()">
                      <span class="material-symbols-outlined">person</span>
                      Activate Account
                    </button>
                  }
                  <button class="action-btn" (click)="exportUserData()">
                    <span class="material-symbols-outlined">download</span>
                    Export User Data
                  </button>
                  <hr />
                  <button class="action-btn danger" (click)="openDeleteDialog()">
                    <span class="material-symbols-outlined">delete_forever</span>
                    Delete User
                  </button>
                </div>
              </div>
            </section>

            <!-- Account Status -->
            <section class="card">
              <div class="card-header">
                <h2>
                  <span class="material-symbols-outlined">info</span>
                  Account Status
                </h2>
              </div>
              <div class="card-body">
                <div class="status-list">
                  <div class="status-item">
                    <span class="status-label">Account Status</span>
                    <span class="status-value" [class]="user()!.is_active ? 'success' : 'error'">
                      {{ user()!.is_active ? 'Active' : 'Inactive' }}
                    </span>
                  </div>
                  <div class="status-item">
                    <span class="status-label">Email Verified</span>
                    <span class="status-value" [class]="user()!.is_verified ? 'success' : 'warning'">
                      {{ user()!.is_verified ? 'Yes' : 'No' }}
                    </span>
                  </div>
                  <div class="status-item">
                    <span class="status-label">Created</span>
                    <span class="status-value">{{ formatDate(user()!.created_at) }}</span>
                  </div>
                  <div class="status-item">
                    <span class="status-label">Last Active</span>
                    <span class="status-value" [class.warning]="isInactive()">
                      {{ user()!.last_active ? formatRelativeDate(user()!.last_active) : 'Never' }}
                    </span>
                  </div>
                  @if (user()!.updated_at) {
                    <div class="status-item">
                      <span class="status-label">Last Updated</span>
                      <span class="status-value">{{ formatRelativeDate(user()!.updated_at!) }}</span>
                    </div>
                  }
                </div>
              </div>
            </section>

            <!-- Payment History Summary -->
            <section class="card">
              <div class="card-header">
                <h2>
                  <span class="material-symbols-outlined">payments</span>
                  Payments
                </h2>
              </div>
              <div class="card-body">
                <div class="payment-summary">
                  <div class="payment-stat">
                    <span class="payment-value">\${{ userStats().payments | number:'1.2-2' }}</span>
                    <span class="payment-label">Total Spent</span>
                  </div>
                  <div class="payment-stat">
                    <span class="payment-value">{{ userStats().paymentCount }}</span>
                    <span class="payment-label">Transactions</span>
                  </div>
                </div>
                <button class="btn btn-outline full-width" routerLink="/payments" [queryParams]="{user_id: user()!.id}">
                  View Payment History
                </button>
              </div>
            </section>

            <!-- Related Users -->
            @if (user()!.role === 'parent') {
              <section class="card">
                <div class="card-header">
                  <h2>
                    <span class="material-symbols-outlined">family_restroom</span>
                    Linked Students
                  </h2>
                </div>
                <div class="card-body">
                  <div class="linked-users">
                    <p class="muted">No linked students</p>
                  </div>
                </div>
              </section>
            }
          </aside>
        </div>
      } @else {
        <div class="not-found">
          <span class="material-symbols-outlined">person_off</span>
          <h2>User Not Found</h2>
          <p>The requested user could not be found or may have been deleted.</p>
          <button class="btn btn-primary" routerLink="/users">Back to Users</button>
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

      <!-- Impersonate Modal -->
      <app-modal #impersonateModal title="Impersonate User" size="md">
        <div class="impersonate-content">
          <div class="impersonate-warning">
            <span class="material-symbols-outlined">warning</span>
            <div>
              <h4>Security Notice</h4>
              <p>You are about to impersonate this user. This action will be logged and audited for compliance.</p>
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
        <ng-container modal-footer>
          <button type="button" class="btn btn-outline" (click)="impersonateModal.close()">Cancel</button>
          <button type="button" class="btn btn-warning" (click)="confirmImpersonate()">
            <span class="material-symbols-outlined">supervisor_account</span>
            Start Impersonation
          </button>
        </ng-container>
      </app-modal>
    </div>
  `,
  styles: [`
    .user-detail-page {
      min-height: 100vh;
      background: var(--background);
    }

    /* Header */
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.5rem;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .header-nav {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .back-btn {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover {
        background: var(--hover);
        color: var(--text-primary);
      }
    }

    .breadcrumb {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;

      a {
        color: var(--text-secondary);
        text-decoration: none;

        &:hover {
          color: var(--primary);
        }
      }

      .separator {
        color: var(--text-muted);
      }

      .current {
        color: var(--text-primary);
        font-weight: 500;
      }
    }

    .header-actions {
      display: flex;
      gap: 0.75rem;
    }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      font-size: 0.875rem;
      font-weight: 500;
      border-radius: 0.5rem;
      cursor: pointer;
      transition: all 0.15s ease;
      white-space: nowrap;

      .material-symbols-outlined {
        font-size: 1.125rem;
      }

      &.full-width {
        width: 100%;
        justify-content: center;
      }
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--primary), #004d35);
      color: white;
      border: none;
      box-shadow: 0 2px 4px rgba(0, 102, 70, 0.2);

      &:hover:not(:disabled) {
        box-shadow: 0 4px 8px rgba(0, 102, 70, 0.3);
      }

      &:disabled {
        opacity: 0.7;
        cursor: not-allowed;
      }
    }

    .btn-outline {
      background: transparent;
      color: var(--text-primary);
      border: 1px solid var(--border);

      &:hover {
        background: var(--hover);
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

    /* Loading & Error States */
    .loading-container, .not-found {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;
      text-align: center;
    }

    .loading-spinner {
      width: 48px;
      height: 48px;
      border: 3px solid var(--border);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-bottom: 1rem;
    }

    .spinner-sm {
      display: inline-block;
      width: 1rem;
      height: 1rem;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-right: 0.5rem;
    }

    .not-found {
      .material-symbols-outlined {
        font-size: 5rem;
        color: var(--text-muted);
        margin-bottom: 1rem;
      }

      h2 {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
      }

      p {
        color: var(--text-secondary);
        margin-bottom: 1.5rem;
      }
    }

    /* Layout */
    .content-layout {
      display: grid;
      grid-template-columns: 1fr 360px;
      gap: 1.5rem;
      padding: 1.5rem;
      max-width: 1600px;
      margin: 0 auto;

      @media (max-width: 1200px) {
        grid-template-columns: 1fr;
      }
    }

    .main-content {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .sidebar {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;

      @media (max-width: 1200px) {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      }
    }

    /* Card */
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--border);

      h2 {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;

        .material-symbols-outlined {
          font-size: 1.25rem;
          color: var(--text-muted);
        }
      }

      .header-hint {
        font-size: 0.75rem;
        color: var(--text-muted);
      }
    }

    .card-body {
      padding: 1.25rem;

      &.no-padding {
        padding: 0;
      }
    }

    /* Profile Card */
    .profile-card {
      background: linear-gradient(135deg, var(--surface), var(--background));
    }

    .profile-header {
      padding: 2rem;
    }

    .avatar-section {
      display: flex;
      align-items: center;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .avatar-wrapper {
      position: relative;
    }

    .avatar {
      width: 96px;
      height: 96px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 2rem;
      font-weight: 700;
      color: white;
      border-radius: 50%;
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
    }

    .verified-badge {
      position: absolute;
      bottom: 0;
      right: 0;
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: white;
      border-radius: 50%;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: #3b82f6;
      }
    }

    .profile-info {
      flex: 1;
    }

    .user-name {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text-primary);
      margin: 0 0 0.25rem;
    }

    .user-email {
      font-size: 0.9375rem;
      color: var(--text-secondary);
      margin: 0 0 0.75rem;
    }

    .profile-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.25rem 0.75rem;
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 9999px;

      .material-symbols-outlined {
        font-size: 0.875rem;
      }
    }

    .role-badge {
      &.student { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
      &.parent { background: rgba(249, 115, 22, 0.1); color: #f97316; }
      &.teacher { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; }
      &.admin { background: var(--text-primary); color: var(--surface); }
    }

    .subscription-badge {
      &.free { background: var(--hover); color: var(--text-secondary); }
      &.basic { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
      &.premium { background: rgba(245, 158, 11, 0.1); color: #d97706; }
      &.family { background: rgba(16, 185, 129, 0.1); color: #10b981; }
      &.school { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; }
    }

    .status-badge {
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

    .profile-stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border);

      @media (max-width: 640px) {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    .stat-item {
      text-align: center;
    }

    .stat-value {
      display: block;
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

    /* Info Grid */
    .info-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1.25rem;

      @media (max-width: 640px) {
        grid-template-columns: 1fr;
      }
    }

    .info-item {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;

      &.full-width {
        grid-column: span 2;

        @media (max-width: 640px) {
          grid-column: span 1;
        }
      }

      label {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }

      .info-value {
        font-size: 0.9375rem;
        color: var(--text-primary);

        &.mono {
          font-family: monospace;
        }

        &.muted {
          color: var(--text-muted);
          font-style: italic;
        }

        &.capitalize {
          text-transform: capitalize;
        }

        &.with-copy {
          display: flex;
          align-items: center;
          gap: 0.5rem;

          code {
            flex: 1;
            padding: 0.375rem 0.5rem;
            background: var(--background);
            border-radius: 0.25rem;
            font-size: 0.8125rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
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
      }
    }

    .copy-btn {
      padding: 0.25rem;
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      border-radius: 0.25rem;

      &:hover {
        background: var(--hover);
        color: var(--primary);
      }

      .material-symbols-outlined {
        font-size: 1rem;
      }
    }

    /* Subjects */
    .subjects-list {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .subject-tag {
      padding: 0.25rem 0.75rem;
      font-size: 0.8125rem;
      background: rgba(0, 102, 70, 0.1);
      color: var(--primary);
      border-radius: 9999px;
    }

    .xp-value {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      color: #f59e0b;
      font-weight: 600;

      .material-symbols-outlined {
        font-size: 1rem;
      }
    }

    .level-badge {
      display: inline-flex;
      padding: 0.25rem 0.75rem;
      background: linear-gradient(135deg, #8b5cf6, #7c3aed);
      color: white;
      font-size: 0.875rem;
      font-weight: 600;
      border-radius: 9999px;
    }

    /* Subscription */
    .subscription-display {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .current-plan {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1rem;
      background: var(--background);
      border-radius: 0.5rem;
    }

    .plan-icon {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 0.75rem;

      .material-symbols-outlined {
        font-size: 1.5rem;
        color: white;
      }

      &.free { background: linear-gradient(135deg, #6b7280, #4b5563); }
      &.basic { background: linear-gradient(135deg, #3b82f6, #2563eb); }
      &.premium { background: linear-gradient(135deg, #f59e0b, #d97706); }
      &.family { background: linear-gradient(135deg, #10b981, #059669); }
      &.school { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }
    }

    .plan-info {
      h3 {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0 0 0.25rem;
      }

      p {
        font-size: 0.8125rem;
        color: var(--text-secondary);
        margin: 0;
      }
    }

    .subscription-edit {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }

    .expiry-info {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      color: var(--text-secondary);

      &.expiring-soon {
        color: #f59e0b;
      }

      .material-symbols-outlined {
        font-size: 1.125rem;
      }
    }

    /* Activity Timeline */
    .activity-timeline {
      display: flex;
      flex-direction: column;
    }

    .activity-item {
      display: flex;
      gap: 1rem;
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--border);

      &:last-child {
        border-bottom: none;
      }
    }

    .activity-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      flex-shrink: 0;

      .material-symbols-outlined {
        font-size: 1.125rem;
        color: white;
      }
    }

    .activity-content {
      flex: 1;
      min-width: 0;

      h4 {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0 0 0.125rem;
      }

      p {
        font-size: 0.8125rem;
        color: var(--text-secondary);
        margin: 0 0 0.25rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .activity-time {
        font-size: 0.75rem;
        color: var(--text-muted);
      }
    }

    .empty-activity {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem;
      color: var(--text-muted);

      .material-symbols-outlined {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
      }

      p {
        margin: 0;
        font-size: 0.875rem;
      }
    }

    /* Quick Actions */
    .quick-actions {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;

      hr {
        border: none;
        border-top: 1px solid var(--border);
        margin: 0.5rem 0;
      }
    }

    .action-btn {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      width: 100%;
      padding: 0.75rem 1rem;
      font-size: 0.875rem;
      font-weight: 500;
      background: var(--background);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      color: var(--text-primary);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover {
        background: var(--hover);
      }

      &.warning {
        color: #f59e0b;
        border-color: rgba(245, 158, 11, 0.3);

        &:hover {
          background: rgba(245, 158, 11, 0.1);
        }
      }

      &.success {
        color: #10b981;
        border-color: rgba(16, 185, 129, 0.3);

        &:hover {
          background: rgba(16, 185, 129, 0.1);
        }
      }

      &.danger {
        color: var(--error);
        border-color: rgba(239, 68, 68, 0.3);

        &:hover {
          background: rgba(239, 68, 68, 0.1);
        }
      }

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    /* Status List */
    .status-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .status-item {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .status-label {
        font-size: 0.8125rem;
        color: var(--text-secondary);
      }

      .status-value {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);

        &.success { color: #10b981; }
        &.warning { color: #f59e0b; }
        &.error { color: #ef4444; }
      }
    }

    /* Payment Summary */
    .payment-summary {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
      margin-bottom: 1rem;
    }

    .payment-stat {
      text-align: center;
      padding: 1rem;
      background: var(--background);
      border-radius: 0.5rem;
    }

    .payment-value {
      display: block;
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--text-primary);
    }

    .payment-label {
      font-size: 0.75rem;
      color: var(--text-muted);
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
        margin: 0 0 0.25rem;
      }

      p {
        font-size: 0.8125rem;
        color: var(--text-secondary);
        margin: 0;
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

    .muted {
      color: var(--text-muted);
      font-size: 0.875rem;
    }

    .capitalize {
      text-transform: capitalize;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class UserDetailComponent implements OnInit {
  @ViewChild('impersonateModal') impersonateModal!: ModalComponent;

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private adminService = inject(AdminService);
  private toastService = inject(ToastService);

  // State
  user = signal<User | null>(null);
  isLoading = signal(true);
  isEditing = signal(false);
  isSaving = signal(false);

  // Edit data
  editData: Partial<User> = {};

  // Stats
  userStats = signal({
    sessions: 0,
    questions: 0,
    achievements: 0,
    payments: 0,
    paymentCount: 0
  });

  // Activity
  recentActivity = signal<ActivityItem[]>([]);

  // Dialog
  showConfirmDialog = signal(false);
  confirmDialogTitle = signal('');
  confirmDialogMessage = signal('');
  confirmDialogType = signal<'danger' | 'warning' | 'info'>('danger');
  pendingAction: (() => void) | null = null;

  // Impersonate
  impersonateReadOnly = true;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadUser(id);
    }
  }

  loadUser(id: string): void {
    this.isLoading.set(true);

    this.adminService.getUserById(id).subscribe({
      next: (user) => {
        this.user.set(user as unknown as User);

        // Set stats from user detail
        this.userStats.set({
          sessions: (user as any).total_sessions || 0,
          questions: (user as any).total_questions_answered || 0,
          achievements: (user as any).achievements_count || 0,
          payments: (user as any).total_payments || 0,
          paymentCount: (user as any).payments_count || 0
        });

        // Generate mock activity for now
        this.generateMockActivity();

        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load user:', err);
        this.toastService.error('Failed to load user details');
        this.isLoading.set(false);
      }
    });
  }

  refreshData(): void {
    const u = this.user();
    if (u) {
      this.loadUser(u.id);
      this.toastService.success('Data refreshed');
    }
  }

  // Editing
  startEditing(): void {
    const u = this.user();
    if (u) {
      this.editData = {
        email: u.email,
        phone_number: u.phone_number,
        role: u.role,
        institution: u.institution,
        subscription_tier: u.subscription_tier,
        subscription_expires_at: u.subscription_expires_at,
        is_active: u.is_active,
        is_verified: u.is_verified
      };
      this.isEditing.set(true);
    }
  }

  cancelEditing(): void {
    this.isEditing.set(false);
    this.editData = {};
  }

  saveChanges(): void {
    const u = this.user();
    if (!u) return;

    this.isSaving.set(true);

    this.adminService.updateUser(u.id, this.editData).subscribe({
      next: (updated) => {
        this.user.set(updated);
        this.isEditing.set(false);
        this.isSaving.set(false);
        this.toastService.success('User updated successfully');
      },
      error: (err) => {
        console.error('Failed to update user:', err);
        this.isSaving.set(false);
        this.toastService.error('Failed to update user');
      }
    });
  }

  // Quick Actions
  sendPasswordReset(): void {
    const u = this.user();
    if (!u) return;

    this.confirmDialogTitle.set('Reset Password');
    this.confirmDialogMessage.set(`Send a password reset email to ${u.email || u.phone_number}?`);
    this.confirmDialogType.set('info');
    this.pendingAction = () => {
      this.adminService.resetUserPassword(u.id).subscribe({
        next: () => this.toastService.success('Password reset email sent'),
        error: () => this.toastService.error('Failed to send reset email')
      });
    };
    this.showConfirmDialog.set(true);
  }

  verifyUser(): void {
    const u = this.user();
    if (!u) return;

    this.adminService.verifyUser(u.id).subscribe({
      next: (updated) => {
        this.user.set(updated);
        this.toastService.success('User verified successfully');
      },
      error: () => this.toastService.error('Failed to verify user')
    });
  }

  activateUser(): void {
    const u = this.user();
    if (!u) return;

    this.adminService.activateUser(u.id).subscribe({
      next: (updated) => {
        this.user.set(updated);
        this.toastService.success('User activated');
      },
      error: () => this.toastService.error('Failed to activate user')
    });
  }

  deactivateUser(): void {
    const u = this.user();
    if (!u) return;

    this.confirmDialogTitle.set('Deactivate Account');
    this.confirmDialogMessage.set(`Deactivate ${this.getUserName()}'s account? They will not be able to log in.`);
    this.confirmDialogType.set('warning');
    this.pendingAction = () => {
      this.adminService.suspendUser(u.id).subscribe({
        next: (updated) => {
          this.user.set(updated);
          this.toastService.success('User deactivated');
        },
        error: () => this.toastService.error('Failed to deactivate user')
      });
    };
    this.showConfirmDialog.set(true);
  }

  exportUserData(): void {
    this.toastService.info('Preparing export...');
    // In a real app, this would call a user-specific export endpoint
    setTimeout(() => {
      this.toastService.success('User data exported');
    }, 1000);
  }

  openDeleteDialog(): void {
    const u = this.user();
    if (!u) return;

    this.confirmDialogTitle.set('Delete User');
    this.confirmDialogMessage.set(`Permanently delete ${this.getUserName()}? This action cannot be undone and will remove all associated data.`);
    this.confirmDialogType.set('danger');
    this.pendingAction = () => {
      this.adminService.deleteUser(u.id).subscribe({
        next: () => {
          this.toastService.success('User deleted');
          this.router.navigate(['/users']);
        },
        error: () => this.toastService.error('Failed to delete user')
      });
    };
    this.showConfirmDialog.set(true);
  }

  // Impersonate
  openImpersonateDialog(): void {
    this.impersonateReadOnly = true;
    this.impersonateModal.open();
  }

  confirmImpersonate(): void {
    const u = this.user();
    if (!u) return;

    this.adminService.impersonateUser(u.id, this.impersonateReadOnly).subscribe({
      next: (response) => {
        const token = response.access_token || response.token;
        if (token) {
          localStorage.setItem('impersonation_token', token);
          localStorage.setItem('original_token', localStorage.getItem('access_token') || '');
          this.toastService.success('Impersonation started', `Now viewing as ${this.getUserName()}`);
        }
        this.impersonateModal.close();
      },
      error: () => {
        this.toastService.error('Failed to impersonate user');
      }
    });
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

  // Activity
  loadMoreActivity(): void {
    this.toastService.info('Loading more activity...');
  }

  private generateMockActivity(): void {
    const u = this.user();
    if (!u) return;

    const activities: ActivityItem[] = [
      {
        id: '1',
        type: 'login',
        title: 'Logged In',
        description: 'User logged in via WhatsApp',
        timestamp: u.last_active || new Date().toISOString(),
        icon: 'login',
        color: '#10b981'
      },
      {
        id: '2',
        type: 'session',
        title: 'Practice Session',
        description: 'Completed 15 Mathematics questions',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        icon: 'school',
        color: '#3b82f6'
      },
      {
        id: '3',
        type: 'achievement',
        title: 'Achievement Unlocked',
        description: 'Earned "Quick Learner" badge',
        timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        icon: 'emoji_events',
        color: '#f59e0b'
      },
      {
        id: '4',
        type: 'update',
        title: 'Profile Updated',
        description: 'Email address was changed',
        timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
        icon: 'edit',
        color: '#8b5cf6'
      }
    ];

    this.recentActivity.set(activities);
  }

  // Utilities
  getUserName(): string {
    const u = this.user();
    if (!u) return 'Unknown';
    return u.full_name || u.name || u.student_name || u.email || 'Unknown User';
  }

  getInitials(): string {
    const name = this.getUserName();
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .substring(0, 2);
  }

  getRoleIcon(): string {
    const u = this.user();
    const icons: Record<string, string> = {
      student: 'school',
      parent: 'family_restroom',
      teacher: 'person',
      admin: 'admin_panel_settings'
    };
    return icons[u?.role || 'student'] || 'person';
  }

  getSubscriptionIcon(): string {
    const u = this.user();
    const icons: Record<string, string> = {
      free: 'redeem',
      basic: 'star_border',
      premium: 'star',
      family: 'family_restroom',
      school: 'school'
    };
    return icons[u?.subscription_tier || 'free'] || 'redeem';
  }

  getSubscriptionDescription(): string {
    const u = this.user();
    const descriptions: Record<string, string> = {
      free: 'Basic access with limited features',
      basic: 'Standard features for individual students',
      premium: 'Full access to all features and content',
      family: 'Shared plan for multiple family members',
      school: 'Institution-wide access for schools'
    };
    return descriptions[u?.subscription_tier || 'free'] || '';
  }

  formatEducationLevel(level: string | undefined): string {
    if (!level) return 'Not specified';
    const labels: Record<string, string> = {
      primary: 'Primary School',
      secondary: 'Secondary (O-Level)',
      a_level: 'Advanced Level'
    };
    return labels[level] || level;
  }

  formatDate(dateStr: string | undefined): string {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  }

  formatRelativeDate(dateStr: string | undefined): string {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 0) return 'in ' + Math.abs(diffDays) + ' days';
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return this.formatDate(dateStr);
  }

  isExpiringSoon(): boolean {
    const u = this.user();
    if (!u?.subscription_expires_at) return false;
    const expiry = new Date(u.subscription_expires_at);
    const now = new Date();
    const daysLeft = Math.floor((expiry.getTime() - now.getTime()) / 86400000);
    return daysLeft > 0 && daysLeft <= 7;
  }

  isExpired(): boolean {
    const u = this.user();
    if (!u?.subscription_expires_at) return false;
    return new Date(u.subscription_expires_at) < new Date();
  }

  isInactive(): boolean {
    const u = this.user();
    if (!u?.last_active) return true;
    const lastActive = new Date(u.last_active);
    const now = new Date();
    const daysSince = Math.floor((now.getTime() - lastActive.getTime()) / 86400000);
    return daysSince > 30;
  }

  copyToClipboard(text: string): void {
    navigator.clipboard.writeText(text).then(() => {
      this.toastService.success('Copied to clipboard');
    });
  }
}
