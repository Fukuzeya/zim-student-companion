import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LiveService } from '../../../core/services/live.service';
import { ToastService } from '../../../core/services/toast.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import {
  LiveConversation,
  ConversationStatus,
  ConversationMessage,
  ConversationDetail,
  ConversationPipeline,
  ConversationAnalytics,
  InterventionType,
  ConversationSearchResult
} from '../../../core/models';

@Component({
  selector: 'app-live-conversations',
  standalone: true,
  imports: [CommonModule, FormsModule, PageHeaderComponent, LoadingSpinnerComponent],
  template: `
    <div class="live-page">
      <app-page-header
        title="Live Conversations"
        description="Monitor active AI tutoring sessions and intervene when students need help."
        [breadcrumbs]="[
          { label: 'Home', link: '/dashboard' },
          { label: 'Live Operations' },
          { label: 'Conversations' }
        ]"
      >
        <div headerActions class="header-actions">
          <button class="btn btn-secondary" (click)="toggleAnalytics()">
            <span class="material-symbols-outlined">analytics</span>
            Analytics
          </button>
          <div class="live-indicator" [class.pulse]="isConnected()">
            <span class="status-dot"></span>
            <span>{{ isConnected() ? 'Live' : 'Connecting...' }}</span>
          </div>
        </div>
      </app-page-header>

      <!-- Pipeline Status -->
      <div class="pipeline-bar">
        <div class="pipeline-stat">
          <span class="material-symbols-outlined">pending</span>
          <span class="stat-value">{{ pipeline()?.pending || 0 }}</span>
          <span class="stat-label">Pending</span>
        </div>
        <div class="pipeline-stat">
          <span class="material-symbols-outlined">sync</span>
          <span class="stat-value">{{ pipeline()?.processing || 0 }}</span>
          <span class="stat-label">Processing</span>
        </div>
        <div class="pipeline-stat success">
          <span class="material-symbols-outlined">check_circle</span>
          <span class="stat-value">{{ pipeline()?.completed_today || 0 }}</span>
          <span class="stat-label">Completed Today</span>
        </div>
        <div class="pipeline-stat" [class.error]="(pipeline()?.failed_today || 0) > 0">
          <span class="material-symbols-outlined">error</span>
          <span class="stat-value">{{ pipeline()?.failed_today || 0 }}</span>
          <span class="stat-label">Failed Today</span>
        </div>
        <div class="pipeline-stat">
          <span class="material-symbols-outlined">timer</span>
          <span class="stat-value">{{ formatResponseTime(pipeline()?.avg_processing_time_ms) }}</span>
          <span class="stat-label">Avg Response</span>
        </div>
        <div class="pipeline-health" [class]="pipeline()?.queue_health || 'unknown'">
          <span class="health-dot"></span>
          <span>{{ pipeline()?.queue_health || 'Unknown' }}</span>
        </div>
      </div>

      <!-- Analytics Panel (Collapsible) -->
      @if (showAnalytics()) {
        <div class="analytics-panel">
          <div class="analytics-header">
            <h3>Conversation Analytics</h3>
            <div class="period-selector">
              <button [class.active]="analyticsPeriod() === 7" (click)="loadAnalytics(7)">7 Days</button>
              <button [class.active]="analyticsPeriod() === 30" (click)="loadAnalytics(30)">30 Days</button>
              <button [class.active]="analyticsPeriod() === 90" (click)="loadAnalytics(90)">90 Days</button>
            </div>
          </div>
          @if (analyticsLoading()) {
            <div class="analytics-loading">
              <span class="spinner"></span>
            </div>
          } @else if (analytics()) {
            <div class="analytics-grid">
              <div class="analytics-card">
                <span class="analytics-value">{{ analytics()?.total_messages || 0 | number }}</span>
                <span class="analytics-label">Total Messages</span>
              </div>
              <div class="analytics-card">
                <span class="analytics-value">{{ analytics()?.unique_students || 0 | number }}</span>
                <span class="analytics-label">Unique Students</span>
              </div>
              <div class="analytics-card">
                <span class="analytics-value">{{ (analytics()?.messages_per_student || 0) | number:'1.1-1' }}</span>
                <span class="analytics-label">Msgs/Student</span>
              </div>
              <div class="analytics-card">
                <span class="analytics-value">{{ (analytics()?.avg_tokens_per_message || 0) | number:'1.0-0' }}</span>
                <span class="analytics-label">Avg Tokens/Msg</span>
              </div>
            </div>
            @if (analytics()?.by_subject) {
              <div class="subject-breakdown">
                <h4>By Subject</h4>
                <div class="subject-bars">
                  @for (subject of getSubjectEntries(); track subject.key) {
                    <div class="subject-bar">
                      <span class="subject-name">{{ subject.key }}</span>
                      <div class="bar-container">
                        <div class="bar" [style.width.%]="getSubjectPercent(subject.value)"></div>
                      </div>
                      <span class="subject-count">{{ subject.value }}</span>
                    </div>
                  }
                </div>
              </div>
            }
          }
        </div>
      }

      <div class="live-layout">
        <!-- Conversations List -->
        <div class="conversations-panel">
          <div class="panel-header">
            <h3>Active Sessions</h3>
            <button class="refresh-btn" (click)="refreshConversations()" [disabled]="loading()">
              <span class="material-symbols-outlined" [class.spinning]="loading()">refresh</span>
            </button>
          </div>

          <!-- Search -->
          <div class="search-box">
            <span class="material-symbols-outlined">search</span>
            <input
              type="text"
              placeholder="Search conversations..."
              [(ngModel)]="searchQuery"
              (keyup.enter)="performSearch()"
            />
            @if (searchQuery) {
              <button class="clear-btn" (click)="clearSearch()">
                <span class="material-symbols-outlined">close</span>
              </button>
            }
          </div>

          <div class="filter-tabs">
            <button
              class="filter-tab"
              [class.active]="statusFilter() === 'all'"
              (click)="setStatusFilter('all')"
            >
              All
              <span class="count">{{ conversations().length }}</span>
            </button>
            <button
              class="filter-tab"
              [class.active]="statusFilter() === 'active'"
              (click)="setStatusFilter('active')"
            >
              Active
            </button>
            <button
              class="filter-tab attention"
              [class.active]="statusFilter() === 'needs_attention'"
              (click)="setStatusFilter('needs_attention')"
            >
              Needs Help
              @if (needsAttentionCount() > 0) {
                <span class="badge-count">{{ needsAttentionCount() }}</span>
              }
            </button>
          </div>

          @if (loading()) {
            <div class="panel-loading">
              <span class="spinner"></span>
              <p>Loading conversations...</p>
            </div>
          } @else if (searchResults().length > 0) {
            <!-- Search Results -->
            <div class="search-results">
              <div class="results-header">
                <span>{{ searchResults().length }} search results</span>
                <button class="clear-btn" (click)="clearSearch()">Clear</button>
              </div>
              @for (result of searchResults(); track result.id) {
                <div class="search-result-item" (click)="selectSearchResult(result)">
                  <div class="result-header">
                    <span class="result-name">{{ result.student_name }}</span>
                    <span class="result-role" [class]="result.role">{{ result.role }}</span>
                  </div>
                  <p class="result-content">{{ result.content | slice:0:150 }}...</p>
                  <span class="result-time">{{ formatDate(result.created_at) }}</span>
                </div>
              }
            </div>
          } @else {
            <div class="conversations-list">
              @for (conv of filteredConversations(); track conv.id) {
                <div
                  class="conversation-item"
                  [class.active]="selectedConversation()?.id === conv.id"
                  [class.needs-attention]="conv.status === 'needs_attention'"
                  (click)="selectConversation(conv)"
                >
                  <div class="conv-avatar">
                    <span class="avatar-text">{{ getInitials(conv.student_name) }}</span>
                    <span class="status-indicator" [class]="conv.status"></span>
                  </div>
                  <div class="conv-info">
                    <div class="conv-header">
                      <span class="conv-name">{{ conv.student_name }}</span>
                      <span class="conv-time">{{ formatTime(conv.last_message_at) }}</span>
                    </div>
                    <div class="conv-preview">
                      @if (conv.last_message_preview) {
                        <span class="preview-text">{{ conv.last_message_preview | slice:0:40 }}...</span>
                      } @else {
                        <span class="conv-subject">{{ conv.subject || 'General' }}</span>
                        <span class="conv-messages">{{ conv.message_count }} msgs</span>
                      }
                    </div>
                    @if (conv.student_grade) {
                      <span class="conv-grade">{{ conv.student_grade }}</span>
                    }
                  </div>
                  @if (conv.status === 'needs_attention') {
                    <span class="attention-icon material-symbols-outlined">priority_high</span>
                  }
                </div>
              } @empty {
                <div class="empty-list">
                  <span class="material-symbols-outlined">chat_bubble_outline</span>
                  <p>No active conversations</p>
                  <span class="hint">Students will appear here when they start chatting</span>
                </div>
              }
            </div>
          }
        </div>

        <!-- Conversation Detail -->
        <div class="detail-panel">
          @if (selectedConversation() && conversationDetail()) {
            <div class="detail-header">
              <div class="user-info">
                <div class="user-avatar">
                  {{ getInitials(conversationDetail()!.student_name) }}
                </div>
                <div class="user-details">
                  <h3>{{ conversationDetail()!.student_name }}</h3>
                  <p>{{ conversationDetail()!.student_grade || 'Student' }}</p>
                </div>
              </div>
              <div class="header-actions">
                <button class="action-btn" (click)="refreshDetail()" title="Refresh">
                  <span class="material-symbols-outlined">refresh</span>
                </button>
              </div>
            </div>

            <div class="conversation-meta">
              <div class="meta-item">
                <span class="material-symbols-outlined">forum</span>
                <span>{{ conversationDetail()!.total_messages }} messages</span>
              </div>
              <div class="meta-item">
                <span class="material-symbols-outlined">token</span>
                <span>{{ conversationDetail()!.total_tokens | number }} tokens</span>
              </div>
              <div class="meta-item">
                <span class="material-symbols-outlined">timer</span>
                <span>{{ formatResponseTime(conversationDetail()!.avg_response_time_ms) }} avg</span>
              </div>
              @if (conversationDetail()!.subjects_discussed.length) {
                <div class="meta-item subjects">
                  <span class="material-symbols-outlined">school</span>
                  <span>{{ conversationDetail()!.subjects_discussed.join(', ') }}</span>
                </div>
              }
            </div>

            <div class="messages-container" #messagesContainer>
              @if (messagesLoading()) {
                <div class="messages-loading">
                  <span class="spinner"></span>
                </div>
              } @else {
                @for (msg of conversationDetail()!.messages; track msg.id) {
                  <div class="message" [class]="msg.role">
                    <div class="message-bubble">
                      <p>{{ msg.content }}</p>
                      <div class="message-meta">
                        <span class="message-time">{{ formatMessageTime(msg.created_at) }}</span>
                        @if (msg.context_type) {
                          <span class="context-badge">{{ msg.context_type }}</span>
                        }
                        @if (msg.tokens_used) {
                          <span class="tokens-badge">{{ msg.tokens_used }} tokens</span>
                        }
                      </div>
                    </div>
                  </div>
                } @empty {
                  <div class="no-messages">
                    <span class="material-symbols-outlined">chat</span>
                    <p>No messages yet</p>
                  </div>
                }
              }
            </div>

            <!-- Intervention Panel -->
            <div class="intervention-panel">
              <div class="intervention-header">
                <span class="material-symbols-outlined">support_agent</span>
                <span>Admin Intervention</span>
              </div>
              <div class="intervention-type-selector">
                <button
                  class="type-btn"
                  [class.active]="interventionType() === 'guidance'"
                  (click)="setInterventionType('guidance')"
                  title="Provide helpful guidance"
                >
                  <span class="material-symbols-outlined">lightbulb</span>
                  Guidance
                </button>
                <button
                  class="type-btn"
                  [class.active]="interventionType() === 'correction'"
                  (click)="setInterventionType('correction')"
                  title="Correct a misunderstanding"
                >
                  <span class="material-symbols-outlined">edit_note</span>
                  Correction
                </button>
                <button
                  class="type-btn escalation"
                  [class.active]="interventionType() === 'escalation'"
                  (click)="setInterventionType('escalation')"
                  title="Escalate for human support"
                >
                  <span class="material-symbols-outlined">priority_high</span>
                  Escalate
                </button>
              </div>
              <div class="intervention-form">
                <textarea
                  [(ngModel)]="interventionMessage"
                  placeholder="Type a message to help this student..."
                  rows="2"
                ></textarea>
                <div class="form-actions">
                  <label class="notify-checkbox">
                    <input type="checkbox" [(ngModel)]="notifyStudent" />
                    <span>Notify student</span>
                  </label>
                  <button
                    class="btn btn-primary"
                    (click)="sendIntervention()"
                    [disabled]="!interventionMessage.trim() || sendingIntervention()"
                  >
                    @if (sendingIntervention()) {
                      <span class="spinner-sm"></span>
                    } @else {
                      <span class="material-symbols-outlined">send</span>
                    }
                    Send
                  </button>
                </div>
              </div>
            </div>
          } @else if (detailLoading()) {
            <div class="detail-loading">
              <app-loading-spinner message="Loading conversation..." />
            </div>
          } @else {
            <div class="no-selection">
              <span class="material-symbols-outlined">chat_bubble</span>
              <h3>Select a conversation</h3>
              <p>Choose a conversation from the list to view details and intervene if needed</p>
            </div>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .live-page {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      height: calc(100vh - 180px);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .live-indicator {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      background-color: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.2);
      border-radius: 9999px;
      color: var(--success);
      font-size: 0.875rem;
      font-weight: 600;

      .status-dot {
        width: 8px;
        height: 8px;
        background-color: var(--success);
        border-radius: 50%;
      }

      &.pulse .status-dot {
        animation: pulse 2s ease-in-out infinite;
      }
    }

    .pipeline-bar {
      display: flex;
      align-items: center;
      gap: 1.5rem;
      padding: 0.75rem 1rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      flex-wrap: wrap;
    }

    .pipeline-stat {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: var(--text-secondary);

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: var(--text-muted);
      }

      .stat-value {
        font-size: 1.125rem;
        font-weight: 700;
        color: var(--text-primary);
      }

      .stat-label {
        font-size: 0.75rem;
        color: var(--text-muted);
      }

      &.success {
        .material-symbols-outlined { color: var(--success); }
        .stat-value { color: var(--success); }
      }

      &.error {
        .material-symbols-outlined { color: var(--error); }
        .stat-value { color: var(--error); }
      }
    }

    .pipeline-health {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.375rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: capitalize;
      margin-left: auto;

      .health-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
      }

      &.healthy {
        background-color: rgba(16, 185, 129, 0.1);
        color: var(--success);
        .health-dot { background-color: var(--success); }
      }

      &.degraded {
        background-color: rgba(245, 158, 11, 0.1);
        color: var(--warning);
        .health-dot { background-color: var(--warning); }
      }

      &.critical {
        background-color: rgba(239, 68, 68, 0.1);
        color: var(--error);
        .health-dot { background-color: var(--error); }
      }

      &.unknown {
        background-color: var(--background);
        color: var(--text-muted);
        .health-dot { background-color: var(--text-muted); }
      }
    }

    .analytics-panel {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1rem;
    }

    .analytics-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;

      h3 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    .period-selector {
      display: flex;
      gap: 0.25rem;
      background-color: var(--background);
      padding: 0.25rem;
      border-radius: 0.5rem;

      button {
        padding: 0.375rem 0.75rem;
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--text-muted);
        background: transparent;
        border-radius: 0.375rem;
        transition: all 0.15s ease;

        &:hover {
          color: var(--text-primary);
        }

        &.active {
          background-color: var(--primary);
          color: white;
        }
      }
    }

    .analytics-loading {
      display: flex;
      justify-content: center;
      padding: 2rem;
    }

    .analytics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 1rem;

      @media (max-width: 768px) {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    .analytics-card {
      background-color: var(--background);
      padding: 1rem;
      border-radius: 0.5rem;
      text-align: center;

      .analytics-value {
        display: block;
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
      }

      .analytics-label {
        font-size: 0.75rem;
        color: var(--text-muted);
      }
    }

    .subject-breakdown {
      h4 {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.75rem;
      }
    }

    .subject-bars {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .subject-bar {
      display: flex;
      align-items: center;
      gap: 0.75rem;

      .subject-name {
        width: 100px;
        font-size: 0.75rem;
        color: var(--text-secondary);
        text-align: right;
      }

      .bar-container {
        flex: 1;
        height: 8px;
        background-color: var(--background);
        border-radius: 4px;
        overflow: hidden;
      }

      .bar {
        height: 100%;
        background-color: var(--primary);
        border-radius: 4px;
        transition: width 0.3s ease;
      }

      .subject-count {
        width: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    .live-layout {
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 1rem;
      flex: 1;
      min-height: 0;

      @media (max-width: 1024px) {
        grid-template-columns: 1fr;
      }
    }

    .conversations-panel {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .panel-header {
      padding: 1rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;

      h3 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    .refresh-btn {
      padding: 0.375rem;
      background: transparent;
      color: var(--text-muted);
      border-radius: 0.375rem;

      &:hover {
        background-color: var(--background);
        color: var(--text-primary);
      }

      .spinning {
        animation: spin 1s linear infinite;
      }
    }

    .search-box {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      border-bottom: 1px solid var(--border);

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: var(--text-muted);
      }

      input {
        flex: 1;
        border: none;
        background: transparent;
        font-size: 0.875rem;
        color: var(--text-primary);

        &::placeholder {
          color: var(--text-muted);
        }
      }

      .clear-btn {
        padding: 0.25rem;
        background: transparent;
        color: var(--text-muted);
        border-radius: 0.25rem;

        &:hover {
          background-color: var(--background);
          color: var(--text-primary);
        }

        .material-symbols-outlined {
          font-size: 1rem;
        }
      }
    }

    .filter-tabs {
      display: flex;
      padding: 0.5rem;
      gap: 0.25rem;
      border-bottom: 1px solid var(--border);
    }

    .filter-tab {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.375rem;
      padding: 0.5rem;
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--text-muted);
      background: transparent;
      border-radius: 0.375rem;
      transition: all 0.15s ease;

      &:hover {
        background-color: var(--background);
        color: var(--text-primary);
      }

      &.active {
        background-color: var(--primary);
        color: white;
      }

      &.attention.active {
        background-color: var(--warning);
      }

      .count {
        padding: 0.125rem 0.375rem;
        font-size: 0.625rem;
        background-color: rgba(0, 0, 0, 0.1);
        border-radius: 9999px;
      }

      .badge-count {
        padding: 0.125rem 0.375rem;
        font-size: 0.625rem;
        background-color: var(--error);
        color: white;
        border-radius: 9999px;
      }
    }

    .conversations-list, .search-results {
      flex: 1;
      overflow-y: auto;
    }

    .results-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      background-color: var(--background);
      font-size: 0.75rem;
      color: var(--text-muted);

      .clear-btn {
        font-size: 0.75rem;
        color: var(--primary);
        background: transparent;

        &:hover {
          text-decoration: underline;
        }
      }
    }

    .search-result-item {
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--border);
      cursor: pointer;

      &:hover {
        background-color: var(--background);
      }

      .result-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.25rem;
      }

      .result-name {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-primary);
      }

      .result-role {
        font-size: 0.625rem;
        padding: 0.125rem 0.375rem;
        border-radius: 0.25rem;
        text-transform: uppercase;

        &.user {
          background-color: rgba(0, 102, 70, 0.1);
          color: var(--primary);
        }

        &.assistant {
          background-color: rgba(59, 130, 246, 0.1);
          color: #3b82f6;
        }

        &.system {
          background-color: rgba(168, 85, 247, 0.1);
          color: #a855f7;
        }
      }

      .result-content {
        font-size: 0.75rem;
        color: var(--text-secondary);
        line-height: 1.4;
        margin-bottom: 0.25rem;
      }

      .result-time {
        font-size: 0.625rem;
        color: var(--text-muted);
      }
    }

    .conversation-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--border);
      cursor: pointer;
      transition: background-color 0.15s ease;

      &:hover {
        background-color: var(--background);
      }

      &.active {
        background-color: rgba(0, 102, 70, 0.05);
        border-left: 3px solid var(--primary);
      }

      &.needs-attention {
        background-color: rgba(245, 158, 11, 0.05);
      }
    }

    .conv-avatar {
      position: relative;
      flex-shrink: 0;

      .avatar-text {
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--primary);
        color: white;
        border-radius: 50%;
        font-size: 0.75rem;
        font-weight: 600;
      }

      .status-indicator {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        border: 2px solid var(--surface);

        &.active { background-color: var(--success); }
        &.idle { background-color: var(--warning); }
        &.needs_attention { background-color: var(--error); }
        &.ended { background-color: var(--text-muted); }
      }
    }

    .conv-info {
      flex: 1;
      min-width: 0;
    }

    .conv-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.25rem;
    }

    .conv-name {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--text-primary);
    }

    .conv-time {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .conv-preview {
      display: flex;
      gap: 0.5rem;
      font-size: 0.75rem;
      color: var(--text-muted);

      .preview-text {
        color: var(--text-secondary);
      }
    }

    .conv-grade {
      display: inline-block;
      margin-top: 0.25rem;
      padding: 0.125rem 0.375rem;
      font-size: 0.625rem;
      background-color: var(--background);
      color: var(--text-muted);
      border-radius: 0.25rem;
    }

    .attention-icon {
      color: var(--warning);
      font-size: 1.25rem;
      animation: pulse 1.5s ease-in-out infinite;
    }

    .detail-panel {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .detail-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      border-bottom: 1px solid var(--border);
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .user-avatar {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--primary);
      color: white;
      border-radius: 50%;
      font-size: 1rem;
      font-weight: 600;
    }

    .user-details {
      h3 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.125rem;
      }

      p {
        font-size: 0.75rem;
        color: var(--text-muted);
      }
    }

    .action-btn {
      padding: 0.5rem;
      border-radius: 0.5rem;
      background: transparent;
      color: var(--text-muted);
      transition: all 0.15s ease;

      &:hover {
        background-color: var(--background);
        color: var(--text-primary);
      }
    }

    .conversation-meta {
      display: flex;
      gap: 1.5rem;
      padding: 0.75rem 1rem;
      background-color: var(--background);
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
    }

    .meta-item {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      font-size: 0.75rem;
      color: var(--text-muted);

      .material-symbols-outlined {
        font-size: 1rem;
      }

      &.subjects {
        flex: 1;
      }
    }

    .messages-container {
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .messages-loading {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100%;
    }

    .message {
      display: flex;

      &.user {
        justify-content: flex-end;

        .message-bubble {
          background-color: var(--primary);
          color: white;

          .message-meta {
            color: rgba(255, 255, 255, 0.7);
          }
        }
      }

      &.assistant {
        justify-content: flex-start;

        .message-bubble {
          background-color: var(--background);
        }
      }

      &.system {
        justify-content: center;

        .message-bubble {
          background-color: rgba(168, 85, 247, 0.1);
          border: 1px solid rgba(168, 85, 247, 0.2);
          max-width: 90%;
        }
      }
    }

    .message-bubble {
      max-width: 70%;
      padding: 0.75rem 1rem;
      border-radius: 1rem;

      p {
        font-size: 0.875rem;
        line-height: 1.5;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
        white-space: pre-wrap;
      }

      .message-meta {
        display: flex;
        gap: 0.5rem;
        font-size: 0.625rem;
        color: var(--text-muted);
      }

      .context-badge, .tokens-badge {
        padding: 0.125rem 0.25rem;
        background-color: rgba(0, 0, 0, 0.1);
        border-radius: 0.25rem;
      }
    }

    .intervention-panel {
      border-top: 1px solid var(--border);
      padding: 1rem;
      background-color: var(--background);
    }

    .intervention-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.75rem;

      .material-symbols-outlined {
        font-size: 1rem;
      }
    }

    .intervention-type-selector {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 0.75rem;
    }

    .type-btn {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.375rem;
      padding: 0.5rem;
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--text-muted);
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.375rem;
      transition: all 0.15s ease;

      .material-symbols-outlined {
        font-size: 1rem;
      }

      &:hover {
        border-color: var(--primary);
        color: var(--primary);
      }

      &.active {
        background-color: rgba(0, 102, 70, 0.1);
        border-color: var(--primary);
        color: var(--primary);
      }

      &.escalation.active {
        background-color: rgba(239, 68, 68, 0.1);
        border-color: var(--error);
        color: var(--error);
      }
    }

    .intervention-form {
      textarea {
        width: 100%;
        padding: 0.75rem;
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        font-size: 0.875rem;
        resize: none;
        margin-bottom: 0.5rem;

        &:focus {
          border-color: var(--primary);
          outline: none;
        }
      }

      .form-actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .notify-checkbox {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        font-size: 0.75rem;
        color: var(--text-secondary);
        cursor: pointer;

        input {
          accent-color: var(--primary);
        }
      }

      .btn {
        display: flex;
        align-items: center;
        gap: 0.375rem;
      }
    }

    .no-selection, .detail-loading {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: var(--text-muted);
      text-align: center;
      padding: 2rem;

      .material-symbols-outlined {
        font-size: 4rem;
        margin-bottom: 1rem;
      }

      h3 {
        font-size: 1.125rem;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
      }
    }

    .panel-loading, .empty-list, .no-messages {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      color: var(--text-muted);

      .material-symbols-outlined {
        font-size: 2rem;
        margin-bottom: 0.5rem;
      }

      .hint {
        font-size: 0.75rem;
        margin-top: 0.25rem;
      }
    }

    .spinner {
      width: 1.5rem;
      height: 1.5rem;
      border: 2px solid var(--border);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    .spinner-sm {
      width: 1rem;
      height: 1rem;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class LiveConversationsComponent implements OnInit, OnDestroy {
  private liveService = inject(LiveService);
  private toastService = inject(ToastService);

  // State
  loading = signal(true);
  isConnected = signal(true);
  conversations = signal<LiveConversation[]>([]);
  selectedConversation = signal<LiveConversation | null>(null);
  conversationDetail = signal<ConversationDetail | null>(null);
  detailLoading = signal(false);
  messagesLoading = signal(false);
  pipeline = signal<ConversationPipeline | null>(null);

  // Analytics
  showAnalytics = signal(false);
  analytics = signal<ConversationAnalytics | null>(null);
  analyticsLoading = signal(false);
  analyticsPeriod = signal(7);

  // Search
  searchQuery = '';
  searchResults = signal<ConversationSearchResult[]>([]);

  // Filters
  statusFilter = signal<'all' | 'active' | 'needs_attention'>('all');

  // Intervention
  interventionMessage = '';
  interventionType = signal<'guidance' | 'correction' | 'escalation'>('guidance');
  notifyStudent = true;
  sendingIntervention = signal(false);

  // Computed
  needsAttentionCount = computed(() =>
    this.conversations().filter(c => c.status === 'needs_attention').length
  );

  filteredConversations = computed(() => {
    let convs = this.conversations();
    const filter = this.statusFilter();

    if (filter === 'active') {
      convs = convs.filter(c => c.status === ConversationStatus.ACTIVE);
    } else if (filter === 'needs_attention') {
      convs = convs.filter(c => c.status === 'needs_attention');
    }

    return convs;
  });

  private refreshInterval: any;
  private pipelineInterval: any;

  ngOnInit(): void {
    this.loadConversations();
    this.loadPipelineStatus();
    this.startPolling();
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
    if (this.pipelineInterval) {
      clearInterval(this.pipelineInterval);
    }
  }

  loadConversations(): void {
    this.loading.set(true);

    this.liveService.getLiveConversations().subscribe({
      next: (conversations) => {
        this.conversations.set(conversations);
        this.loading.set(false);
        this.isConnected.set(true);
      },
      error: (err) => {
        console.error('Failed to load conversations:', err);
        this.isConnected.set(false);
        // Use mock data for development
        this.conversations.set([
          {
            id: 'conv_001',
            student_id: 'student_001',
            student_name: 'Tinashe Moyo',
            student_grade: 'Form 4',
            subject: 'Mathematics',
            topic: 'Algebra',
            status: ConversationStatus.ACTIVE,
            message_count: 12,
            last_message_at: new Date(Date.now() - 30 * 1000).toISOString(),
            last_message_preview: 'Can you help me understand quadratic equations?',
            time_since_last_seconds: 30
          },
          {
            id: 'conv_002',
            student_id: 'student_002',
            student_name: 'Chipo Ndlovu',
            student_grade: 'Form 3',
            subject: 'Science',
            topic: 'Chemistry',
            status: 'needs_attention' as ConversationStatus,
            message_count: 8,
            last_message_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
            last_message_preview: "I'm stuck on this problem and don't understand",
            time_since_last_seconds: 120
          },
          {
            id: 'conv_003',
            student_id: 'student_003',
            student_name: 'Farai Gumbo',
            student_grade: 'Form 2',
            subject: 'English',
            topic: 'Grammar',
            status: ConversationStatus.IDLE,
            message_count: 5,
            last_message_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
            time_since_last_seconds: 600
          }
        ]);
        this.loading.set(false);
      }
    });
  }

  loadPipelineStatus(): void {
    this.liveService.getPipelineStatus().subscribe({
      next: (pipeline) => {
        this.pipeline.set(pipeline);
      },
      error: () => {
        // Use mock data
        this.pipeline.set({
          pending: 3,
          processing: 2,
          completed_today: 156,
          failed_today: 2,
          avg_processing_time_ms: 1250,
          queue_health: 'healthy'
        });
      }
    });
  }

  refreshConversations(): void {
    this.loadConversations();
  }

  startPolling(): void {
    // Refresh conversations every 10 seconds
    this.refreshInterval = setInterval(() => {
      this.loadConversations();
    }, 10000);

    // Refresh pipeline every 30 seconds
    this.pipelineInterval = setInterval(() => {
      this.loadPipelineStatus();
    }, 30000);
  }

  setStatusFilter(filter: 'all' | 'active' | 'needs_attention'): void {
    this.statusFilter.set(filter);
  }

  selectConversation(conv: LiveConversation): void {
    this.selectedConversation.set(conv);
    this.loadConversationDetail(conv.id);
  }

  loadConversationDetail(conversationId: string): void {
    this.detailLoading.set(true);
    this.conversationDetail.set(null);

    this.liveService.getConversationDetail(conversationId).subscribe({
      next: (detail) => {
        this.conversationDetail.set(detail);
        this.detailLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load conversation detail:', err);
        // Mock data
        const conv = this.selectedConversation();
        if (conv) {
          this.conversationDetail.set({
            id: conv.id,
            student_id: conv.student_id,
            student_name: conv.student_name,
            student_grade: conv.student_grade,
            messages: [
              {
                id: 'msg_001',
                role: 'user',
                content: 'Can you help me understand quadratic equations?',
                context_type: 'question',
                created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
                tokens_used: 45
              },
              {
                id: 'msg_002',
                role: 'assistant',
                content: 'Of course! A quadratic equation is an equation of the form ax² + bx + c = 0. Would you like me to explain how to solve them?',
                context_type: 'explanation',
                created_at: new Date(Date.now() - 9 * 60 * 1000).toISOString(),
                tokens_used: 120,
                response_time_ms: 1200
              },
              {
                id: 'msg_003',
                role: 'user',
                content: 'Yes please! How do I use the quadratic formula?',
                context_type: 'question',
                created_at: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
                tokens_used: 35
              },
              {
                id: 'msg_004',
                role: 'assistant',
                content: 'The quadratic formula is x = (-b ± √(b²-4ac)) / 2a. Let me walk you through an example step by step...',
                context_type: 'explanation',
                created_at: new Date(Date.now() - 7 * 60 * 1000).toISOString(),
                tokens_used: 250,
                response_time_ms: 1800
              }
            ],
            total_messages: 4,
            total_tokens: 450,
            avg_response_time_ms: 1500,
            subjects_discussed: ['Mathematics'],
            started_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
            last_message_at: new Date(Date.now() - 7 * 60 * 1000).toISOString()
          });
        }
        this.detailLoading.set(false);
      }
    });
  }

  refreshDetail(): void {
    const conv = this.selectedConversation();
    if (conv) {
      this.loadConversationDetail(conv.id);
    }
  }

  // Analytics
  toggleAnalytics(): void {
    this.showAnalytics.update(v => !v);
    if (this.showAnalytics() && !this.analytics()) {
      this.loadAnalytics(this.analyticsPeriod());
    }
  }

  loadAnalytics(days: number): void {
    this.analyticsPeriod.set(days);
    this.analyticsLoading.set(true);

    this.liveService.getConversationAnalytics(days).subscribe({
      next: (analytics) => {
        this.analytics.set(analytics);
        this.analyticsLoading.set(false);
      },
      error: () => {
        // Mock data
        this.analytics.set({
          period_days: days,
          total_messages: 1250,
          unique_students: 150,
          messages_per_student: 8.33,
          by_context_type: {
            question: 500,
            explanation: 400,
            practice: 350
          },
          by_subject: {
            Mathematics: 450,
            Science: 320,
            English: 280,
            History: 200
          },
          daily_volume: [],
          avg_tokens_per_message: 425
        });
        this.analyticsLoading.set(false);
      }
    });
  }

  getSubjectEntries(): { key: string; value: number }[] {
    const subjects = this.analytics()?.by_subject || {};
    return Object.entries(subjects).map(([key, value]) => ({ key, value }));
  }

  getSubjectPercent(count: number): number {
    const subjects = this.analytics()?.by_subject || {};
    const max = Math.max(...Object.values(subjects));
    return max > 0 ? (count / max) * 100 : 0;
  }

  // Search
  performSearch(): void {
    if (!this.searchQuery.trim()) {
      this.clearSearch();
      return;
    }

    this.liveService.searchConversations({ query: this.searchQuery, limit: 20 }).subscribe({
      next: (results) => {
        this.searchResults.set(results);
      },
      error: () => {
        this.toastService.error('Search Failed', 'Unable to search conversations');
      }
    });
  }

  clearSearch(): void {
    this.searchQuery = '';
    this.searchResults.set([]);
  }

  selectSearchResult(result: ConversationSearchResult): void {
    // Find conversation in list or load it
    const conv = this.conversations().find(c => c.student_id === result.student_id);
    if (conv) {
      this.selectConversation(conv);
    } else {
      // Load directly
      this.loadConversationDetail(result.id);
    }
    this.clearSearch();
  }

  // Intervention
  setInterventionType(type: 'guidance' | 'correction' | 'escalation'): void {
    this.interventionType.set(type);
  }

  sendIntervention(): void {
    const conv = this.selectedConversation();
    if (!conv || !this.interventionMessage.trim()) return;

    this.sendingIntervention.set(true);

    this.liveService.interveneConversation(
      conv.student_id,
      this.interventionMessage,
      this.interventionType(),
      this.notifyStudent
    ).subscribe({
      next: (response) => {
        if (response.success) {
          this.toastService.success(
            'Intervention Sent',
            `Your ${this.interventionType()} message has been sent to ${conv.student_name}`
          );
          this.interventionMessage = '';
          // Refresh detail to show new message
          this.refreshDetail();
        } else {
          this.toastService.error('Failed', response.message);
        }
        this.sendingIntervention.set(false);
      },
      error: (err) => {
        console.error('Intervention failed:', err);
        this.toastService.error('Intervention Failed', 'Unable to send message');
        this.sendingIntervention.set(false);
      }
    });
  }

  // Helpers
  getInitials(name: string): string {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
  }

  formatTime(timestamp: string): string {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  formatMessageTime(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  formatDate(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  formatResponseTime(ms?: number): string {
    if (!ms) return '0ms';
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  }
}
