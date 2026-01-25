import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { AdminService } from '../../../core/services/admin.service';
import { ToastService } from '../../../core/services/toast.service';
import {
  StudentDetailResponse,
  StudentActivity,
  SubjectAnalytics,
  StudentSession
} from '../../../core/models/user.models';

@Component({
  selector: 'app-student-detail',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-left">
          <button class="btn-back" routerLink="/students">
            <span class="material-symbols-outlined">arrow_back</span>
          </button>
          <div class="header-info">
            <h1>Student Profile</h1>
            <p class="subtitle">View student information and learning progress</p>
          </div>
        </div>
        <div class="header-actions">
          <button class="btn-secondary" (click)="downloadReport()">
            <span class="material-symbols-outlined">download</span>
            Report
          </button>
          <button class="btn-secondary">
            <span class="material-symbols-outlined">chat</span>
            Message
          </button>
          <button class="btn-primary">
            <span class="material-symbols-outlined">edit</span>
            Edit
          </button>
        </div>
      </div>

      @if (isLoading()) {
        <div class="loading-state">
          <div class="spinner-large"></div>
          <p>Loading student profile...</p>
        </div>
      } @else if (student()) {
        <div class="content-grid">
          <div class="main-content">
            <div class="card profile-card">
              <div class="profile-header">
                <div class="avatar-large">{{ getInitials() }}</div>
                <div class="profile-info">
                  <h2>{{ student()!.full_name }}</h2>
                  <p class="email">{{ student()!.email }}</p>
                  <div class="badges">
                    <span class="badge grade">{{ student()!.grade || 'N/A' }}</span>
                    <span class="badge level">Level {{ student()!.level }}</span>
                    <span class="badge" [class]="student()!.subscription_tier">
                      {{ student()!.subscription_tier }} Plan
                    </span>
                    <span class="badge" [class]="student()!.is_active ? 'active' : 'inactive'">
                      {{ student()!.is_active ? 'Active' : 'Inactive' }}
                    </span>
                  </div>
                </div>
                <div class="xp-display">
                  <span class="xp-value">{{ student()!.total_xp | number }}</span>
                  <span class="xp-label">Total XP</span>
                </div>
              </div>
            </div>

            <div class="card">
              <div class="card-header">
                <h3>Learning Progress</h3>
                <span class="trend-badge" [class]="trendDirection()">
                  <span class="material-symbols-outlined">{{ trendIcon() }}</span>
                  {{ trendDirection() }}
                </span>
              </div>
              <div class="card-body">
                <div class="progress-overview">
                  <div class="progress-circle">
                    <svg viewBox="0 0 36 36">
                      <path class="circle-bg"
                        d="M18 2.0845
                          a 15.9155 15.9155 0 0 1 0 31.831
                          a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      <path class="circle-progress"
                        [attr.stroke-dasharray]="overallAccuracy() + ', 100'"
                        d="M18 2.0845
                          a 15.9155 15.9155 0 0 1 0 31.831
                          a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                    </svg>
                    <span class="progress-value">{{ overallAccuracy() }}%</span>
                  </div>
                  <div class="progress-details">
                    <h4>Overall Accuracy</h4>
                    <p>{{ student()!.statistics.total_questions }} questions answered</p>
                    <p>{{ student()!.statistics.correct_answers }} correct</p>
                  </div>
                </div>

                <div class="subjects-progress">
                  @for (subject of subjectProgress(); track subject.subject) {
                    <div class="subject-item">
                      <div class="subject-header">
                        <span class="subject-name">{{ subject.subject }}</span>
                        <span class="subject-percent">{{ subject.accuracy }}%</span>
                      </div>
                      <div class="subject-bar">
                        <div class="subject-fill" [style.width.%]="subject.accuracy"></div>
                      </div>
                      <div class="subject-meta">
                        <span>{{ subject.questions_attempted }} questions</span>
                        <span>{{ subject.correct }} correct</span>
                      </div>
                    </div>
                  } @empty {
                    <div class="empty-subjects">
                      <span class="material-symbols-outlined">school</span>
                      <p>No subject data available yet</p>
                    </div>
                  }
                </div>
              </div>
            </div>

            <div class="card">
              <div class="card-header">
                <h3>Recent Activity</h3>
                <button class="btn-text" (click)="loadMoreActivities()">View All</button>
              </div>
              <div class="card-body">
                @if (activitiesLoading()) {
                  <div class="loading-inline">
                    <div class="spinner-small"></div>
                    <span>Loading activities...</span>
                  </div>
                } @else {
                  <div class="activity-list">
                    @for (activity of recentActivities(); track activity.id) {
                      <div class="activity-item">
                        <div class="activity-icon" [class]="activity.type">
                          <span class="material-symbols-outlined">{{ activity.icon }}</span>
                        </div>
                        <div class="activity-content">
                          <p class="activity-text">{{ activity.title }}</p>
                          <p class="activity-desc">{{ activity.description }}</p>
                          <span class="activity-time">{{ activity.timestamp | date:'short' }}</span>
                        </div>
                      </div>
                    } @empty {
                      <div class="empty-activities">
                        <span class="material-symbols-outlined">history</span>
                        <p>No recent activity</p>
                      </div>
                    }
                  </div>
                }
              </div>
            </div>

            <div class="card">
              <div class="card-header">
                <h3>Recent Sessions</h3>
              </div>
              <div class="card-body">
                @if (sessionsLoading()) {
                  <div class="loading-inline">
                    <div class="spinner-small"></div>
                    <span>Loading sessions...</span>
                  </div>
                } @else {
                  <div class="sessions-list">
                    @for (session of recentSessions(); track session.id) {
                      <div class="session-item">
                        <div class="session-icon" [class]="session.status">
                          <span class="material-symbols-outlined">
                            {{ session.status === 'completed' ? 'check_circle' : session.status === 'in_progress' ? 'pending' : 'cancel' }}
                          </span>
                        </div>
                        <div class="session-info">
                          <div class="session-header">
                            <span class="session-type">{{ formatSessionType(session.session_type) }}</span>
                            @if (session.subject_name) {
                              <span class="session-subject">{{ session.subject_name }}</span>
                            }
                          </div>
                          <div class="session-stats">
                            <span>{{ session.total_questions }} questions</span>
                            <span>{{ session.correct_answers }} correct</span>
                            @if (session.score_percentage) {
                              <span class="score">{{ session.score_percentage }}%</span>
                            }
                            <span class="xp">+{{ session.xp_earned }} XP</span>
                          </div>
                          <span class="session-time">{{ session.started_at | date:'short' }}</span>
                        </div>
                      </div>
                    } @empty {
                      <div class="empty-sessions">
                        <span class="material-symbols-outlined">quiz</span>
                        <p>No practice sessions yet</p>
                      </div>
                    }
                  </div>
                }
              </div>
            </div>
          </div>

          <div class="sidebar-content">
            <div class="card">
              <div class="card-header">
                <h3>Statistics</h3>
              </div>
              <div class="card-body">
                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="material-symbols-outlined">quiz</span>
                    <div class="stat-info">
                      <span class="stat-value">{{ student()!.statistics.total_questions }}</span>
                      <span class="stat-label">Questions</span>
                    </div>
                  </div>
                  <div class="stat-item">
                    <span class="material-symbols-outlined">schedule</span>
                    <div class="stat-info">
                      <span class="stat-value">{{ student()!.statistics.total_study_hours }}h</span>
                      <span class="stat-label">Study Time</span>
                    </div>
                  </div>
                  <div class="stat-item">
                    <span class="material-symbols-outlined">local_fire_department</span>
                    <div class="stat-info">
                      <span class="stat-value">{{ student()!.statistics.current_streak }}</span>
                      <span class="stat-label">Day Streak</span>
                    </div>
                  </div>
                  <div class="stat-item">
                    <span class="material-symbols-outlined">military_tech</span>
                    <div class="stat-info">
                      <span class="stat-value">{{ student()!.statistics.achievements_count }}</span>
                      <span class="stat-label">Badges</span>
                    </div>
                  </div>
                  <div class="stat-item">
                    <span class="material-symbols-outlined">event_available</span>
                    <div class="stat-info">
                      <span class="stat-value">{{ student()!.statistics.total_sessions }}</span>
                      <span class="stat-label">Sessions</span>
                    </div>
                  </div>
                  <div class="stat-item">
                    <span class="material-symbols-outlined">calendar_month</span>
                    <div class="stat-info">
                      <span class="stat-value">{{ student()!.statistics.total_active_days }}</span>
                      <span class="stat-label">Active Days</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="card">
              <div class="card-header">
                <h3>Enrolled Subjects</h3>
              </div>
              <div class="card-body">
                <div class="subjects-list">
                  @for (subject of student()!.subjects; track subject) {
                    <div class="subject-tag">
                      <span class="material-symbols-outlined">book</span>
                      {{ subject }}
                    </div>
                  } @empty {
                    <p class="no-subjects">No subjects enrolled</p>
                  }
                </div>
              </div>
            </div>

            <div class="card">
              <div class="card-header">
                <h3>Performance by Difficulty</h3>
              </div>
              <div class="card-body">
                <div class="difficulty-stats">
                  @for (diff of difficultyStats(); track diff.level) {
                    <div class="difficulty-item">
                      <div class="diff-header">
                        <span class="diff-label" [class]="diff.level">{{ diff.level }}</span>
                        <span class="diff-accuracy">{{ diff.accuracy }}%</span>
                      </div>
                      <div class="diff-bar">
                        <div class="diff-fill" [class]="diff.level" [style.width.%]="diff.accuracy"></div>
                      </div>
                      <span class="diff-count">{{ diff.correct }}/{{ diff.attempted }}</span>
                    </div>
                  } @empty {
                    <p class="no-data">No performance data</p>
                  }
                </div>
              </div>
            </div>

            <div class="card">
              <div class="card-header">
                <h3>Account Info</h3>
              </div>
              <div class="card-body">
                <div class="info-list">
                  <div class="info-item">
                    <span class="info-label">Joined</span>
                    <span class="info-value">{{ student()!.created_at | date:'mediumDate' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Last Active</span>
                    <span class="info-value">{{ student()!.last_active | date:'short' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Phone</span>
                    <span class="info-value">{{ student()!.phone_number || 'Not set' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">School</span>
                    <span class="info-value">{{ student()!.school_name || 'Not set' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Location</span>
                    <span class="info-value">{{ student()!.district || 'N/A' }}, {{ student()!.province || 'N/A' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Daily Goal</span>
                    <span class="info-value">{{ student()!.daily_goal_minutes }} minutes</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      } @else {
        <div class="empty-state">
          <span class="material-symbols-outlined">person_off</span>
          <h3>Student Not Found</h3>
          <p>The requested student could not be found.</p>
          <button class="btn-primary" routerLink="/students">Back to Students</button>
        </div>
      }
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

    .header-left {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .btn-back {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover {
        background-color: var(--hover);
        color: var(--text-primary);
      }
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

    .header-actions {
      display: flex;
      gap: 0.75rem;
    }

    .btn-primary, .btn-secondary, .btn-text {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      font-size: 0.875rem;
      font-weight: 500;
      border-radius: 0.5rem;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .btn-primary {
      background-color: var(--primary);
      color: white;
      border: none;

      &:hover {
        background-color: #005238;
      }
    }

    .btn-secondary {
      background-color: var(--surface);
      color: var(--text-primary);
      border: 1px solid var(--border);

      &:hover {
        background-color: var(--hover);
      }
    }

    .btn-text {
      background: none;
      border: none;
      color: var(--primary);
      padding: 0.25rem 0.5rem;

      &:hover {
        text-decoration: underline;
      }
    }

    .loading-state, .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;
      text-align: center;

      .material-symbols-outlined {
        font-size: 4rem;
        color: var(--text-tertiary);
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

    .spinner-large {
      width: 3rem;
      height: 3rem;
      border: 3px solid var(--border);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-bottom: 1rem;
    }

    .spinner-small {
      width: 1.25rem;
      height: 1.25rem;
      border: 2px solid var(--border);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    .loading-inline {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem;
      color: var(--text-secondary);
    }

    .content-grid {
      display: grid;
      grid-template-columns: 1fr 380px;
      gap: 1.5rem;

      @media (max-width: 1024px) {
        grid-template-columns: 1fr;
      }
    }

    .main-content, .sidebar-content {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.5rem;
      border-bottom: 1px solid var(--border);

      h3 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    .trend-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.25rem 0.5rem;
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 0.25rem;
      text-transform: capitalize;

      .material-symbols-outlined {
        font-size: 1rem;
      }

      &.improving {
        background-color: rgba(16, 185, 129, 0.1);
        color: #10b981;
      }

      &.declining {
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }

      &.stable, &.insufficient_data {
        background-color: rgba(107, 114, 128, 0.1);
        color: #6b7280;
      }
    }

    .card-body {
      padding: 1.5rem;
    }

    .profile-card .profile-header {
      display: flex;
      align-items: center;
      gap: 1.5rem;
      padding: 2rem;
    }

    .avatar-large {
      width: 80px;
      height: 80px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--primary);
      color: white;
      font-size: 1.75rem;
      font-weight: 700;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .profile-info {
      flex: 1;

      h2 {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
      }

      .email {
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-bottom: 0.75rem;
      }

      .badges {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
      }
    }

    .xp-display {
      text-align: center;
      padding: 1rem;
      background: linear-gradient(135deg, var(--primary) 0%, #008855 100%);
      border-radius: 0.75rem;
      color: white;

      .xp-value {
        display: block;
        font-size: 1.75rem;
        font-weight: 700;
      }

      .xp-label {
        font-size: 0.75rem;
        opacity: 0.9;
      }
    }

    .badge {
      display: inline-flex;
      padding: 0.25rem 0.75rem;
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 9999px;
      text-transform: capitalize;

      &.grade {
        background-color: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }

      &.level {
        background-color: rgba(139, 92, 246, 0.1);
        color: #8b5cf6;
      }

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

      &.active {
        background-color: rgba(16, 185, 129, 0.1);
        color: #10b981;
      }

      &.inactive {
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }
    }

    .progress-overview {
      display: flex;
      align-items: center;
      gap: 1.5rem;
      margin-bottom: 2rem;
    }

    .progress-circle {
      position: relative;
      width: 100px;
      height: 100px;
      flex-shrink: 0;

      svg {
        transform: rotate(-90deg);
      }

      .circle-bg {
        fill: none;
        stroke: var(--background);
        stroke-width: 3.8;
      }

      .circle-progress {
        fill: none;
        stroke: var(--primary);
        stroke-width: 3.8;
        stroke-linecap: round;
        transition: stroke-dasharray 0.3s ease;
      }

      .progress-value {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-primary);
      }
    }

    .progress-details {
      h4 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
      }

      p {
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin: 0.125rem 0;
      }
    }

    .subjects-progress {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .subject-item {
      .subject-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.5rem;
      }

      .subject-name {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);
      }

      .subject-percent {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--primary);
      }

      .subject-bar {
        height: 8px;
        background-color: var(--background);
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 0.375rem;
      }

      .subject-fill {
        height: 100%;
        background-color: var(--primary);
        border-radius: 4px;
        transition: width 0.3s ease;
      }

      .subject-meta {
        display: flex;
        gap: 1rem;
        font-size: 0.75rem;
        color: var(--text-tertiary);
      }
    }

    .empty-subjects, .empty-activities, .empty-sessions {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem;
      color: var(--text-tertiary);

      .material-symbols-outlined {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
      }

      p {
        font-size: 0.875rem;
      }
    }

    .activity-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .activity-item {
      display: flex;
      gap: 1rem;
    }

    .activity-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 0.5rem;
      flex-shrink: 0;

      &.session_completed {
        background-color: rgba(16, 185, 129, 0.1);
        .material-symbols-outlined { color: #10b981; }
      }

      &.session_started {
        background-color: rgba(59, 130, 246, 0.1);
        .material-symbols-outlined { color: #3b82f6; }
      }

      &.achievement {
        background-color: rgba(245, 158, 11, 0.1);
        .material-symbols-outlined { color: #f59e0b; }
      }

      &.competition_completed, &.competition_joined {
        background-color: rgba(139, 92, 246, 0.1);
        .material-symbols-outlined { color: #8b5cf6; }
      }
    }

    .activity-content {
      flex: 1;

      .activity-text {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);
        margin-bottom: 0.125rem;
      }

      .activity-desc {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-bottom: 0.25rem;
      }

      .activity-time {
        font-size: 0.75rem;
        color: var(--text-tertiary);
      }
    }

    .sessions-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .session-item {
      display: flex;
      gap: 1rem;
      padding: 0.75rem;
      background-color: var(--background);
      border-radius: 0.5rem;
    }

    .session-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      flex-shrink: 0;

      &.completed {
        background-color: rgba(16, 185, 129, 0.1);
        .material-symbols-outlined { color: #10b981; }
      }

      &.in_progress {
        background-color: rgba(59, 130, 246, 0.1);
        .material-symbols-outlined { color: #3b82f6; }
      }

      &.abandoned {
        background-color: rgba(239, 68, 68, 0.1);
        .material-symbols-outlined { color: #ef4444; }
      }
    }

    .session-info {
      flex: 1;

      .session-header {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        margin-bottom: 0.25rem;
      }

      .session-type {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);
      }

      .session-subject {
        font-size: 0.75rem;
        padding: 0.125rem 0.375rem;
        background-color: var(--surface);
        border-radius: 0.25rem;
        color: var(--text-secondary);
      }

      .session-stats {
        display: flex;
        gap: 0.75rem;
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-bottom: 0.25rem;

        .score {
          font-weight: 600;
          color: var(--primary);
        }

        .xp {
          color: #f59e0b;
          font-weight: 500;
        }
      }

      .session-time {
        font-size: 0.75rem;
        color: var(--text-tertiary);
      }
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 0.75rem;
    }

    .stat-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.875rem;
      background-color: var(--background);
      border-radius: 0.5rem;

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: var(--primary);
      }

      .stat-info {
        display: flex;
        flex-direction: column;

        .stat-value {
          font-size: 1.125rem;
          font-weight: 700;
          color: var(--text-primary);
        }

        .stat-label {
          font-size: 0.625rem;
          color: var(--text-secondary);
        }
      }
    }

    .subjects-list {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .subject-tag {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.5rem 0.75rem;
      background-color: var(--background);
      border-radius: 0.375rem;
      font-size: 0.75rem;
      color: var(--text-primary);

      .material-symbols-outlined {
        font-size: 1rem;
        color: var(--primary);
      }
    }

    .no-subjects, .no-data {
      font-size: 0.875rem;
      color: var(--text-tertiary);
      text-align: center;
      padding: 1rem;
    }

    .difficulty-stats {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .difficulty-item {
      .diff-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.375rem;
      }

      .diff-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: capitalize;
        padding: 0.125rem 0.5rem;
        border-radius: 0.25rem;

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

      .diff-accuracy {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-primary);
      }

      .diff-bar {
        height: 6px;
        background-color: var(--background);
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 0.25rem;
      }

      .diff-fill {
        height: 100%;
        border-radius: 3px;

        &.easy { background-color: #10b981; }
        &.medium { background-color: #f59e0b; }
        &.hard { background-color: #ef4444; }
      }

      .diff-count {
        font-size: 0.75rem;
        color: var(--text-tertiary);
      }
    }

    .info-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .info-item {
      display: flex;
      justify-content: space-between;

      .info-label {
        font-size: 0.875rem;
        color: var(--text-secondary);
      }

      .info-value {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);
      }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class StudentDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private adminService = inject(AdminService);
  private toastService = inject(ToastService);

  student = signal<StudentDetailResponse | null>(null);
  isLoading = signal(true);
  recentActivities = signal<StudentActivity[]>([]);
  activitiesLoading = signal(false);
  recentSessions = signal<StudentSession[]>([]);
  sessionsLoading = signal(false);

  // Computed values
  overallAccuracy = computed(() => {
    const s = this.student();
    return s ? s.statistics.accuracy : 0;
  });

  subjectProgress = computed(() => {
    const s = this.student();
    if (!s?.analytics?.subjects) return [];
    return s.analytics.subjects;
  });

  trendDirection = computed(() => {
    const s = this.student();
    return s?.analytics?.trends?.trend_direction || 'stable';
  });

  trendIcon = computed(() => {
    const direction = this.trendDirection();
    switch (direction) {
      case 'improving': return 'trending_up';
      case 'declining': return 'trending_down';
      default: return 'trending_flat';
    }
  });

  difficultyStats = computed(() => {
    const s = this.student();
    if (!s?.analytics?.performance) return [];

    const performance = s.analytics.performance;
    return Object.entries(performance).map(([level, data]) => ({
      level,
      attempted: data.attempted,
      correct: data.correct,
      accuracy: data.accuracy
    }));
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadStudent(id);
    }
  }

  loadStudent(id: string): void {
    this.isLoading.set(true);
    this.adminService.getStudentById(id).subscribe({
      next: (student) => {
        this.student.set(student);
        this.isLoading.set(false);
        // Load additional data
        this.loadActivities(id);
        this.loadSessions(id);
      },
      error: (err) => {
        console.error('Failed to load student:', err);
        this.toastService.error('Failed to load student profile');
        this.isLoading.set(false);
      }
    });
  }

  loadActivities(studentId: string): void {
    this.activitiesLoading.set(true);
    this.adminService.getStudentActivity(studentId, 10).subscribe({
      next: (response) => {
        this.recentActivities.set(response.activities);
        this.activitiesLoading.set(false);
      },
      error: () => {
        this.activitiesLoading.set(false);
      }
    });
  }

  loadSessions(studentId: string): void {
    this.sessionsLoading.set(true);
    this.adminService.getStudentSessions(studentId, { limit: 5, status: 'completed' }).subscribe({
      next: (response) => {
        this.recentSessions.set(response.sessions);
        this.sessionsLoading.set(false);
      },
      error: () => {
        this.sessionsLoading.set(false);
      }
    });
  }

  loadMoreActivities(): void {
    const s = this.student();
    if (s) {
      this.loadActivities(s.id);
    }
  }

  downloadReport(): void {
    const s = this.student();
    if (!s) return;

    this.adminService.getStudentReport(s.id, 'json').subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `student-report-${s.full_name.replace(/\s+/g, '-')}.json`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.toastService.success('Report downloaded successfully');
      },
      error: () => {
        this.toastService.error('Failed to download report');
      }
    });
  }

  getInitials(): string {
    const s = this.student();
    if (!s) return 'U';
    if (s.full_name) {
      return s.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    if (s.first_name && s.last_name) {
      return (s.first_name[0] + s.last_name[0]).toUpperCase();
    }
    return (s.email || 'U').slice(0, 2).toUpperCase();
  }

  formatSessionType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
}
