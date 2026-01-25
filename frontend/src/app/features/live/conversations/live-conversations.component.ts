import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LiveService } from '../../../core/services/live.service';
import { ToastService } from '../../../core/services/toast.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { Conversation, ConversationStatus, ConversationMessage, MessageRole, LiveStats } from '../../../core/models';

@Component({
  selector: 'app-live-conversations',
  standalone: true,
  imports: [CommonModule, FormsModule, PageHeaderComponent, LoadingSpinnerComponent],
  template: `
    <div class="live-page">
      <app-page-header
        title="Live Conversations"
        description="Monitor active AI tutoring sessions in real-time."
        [breadcrumbs]="[
          { label: 'Home', link: '/dashboard' },
          { label: 'Live Operations' },
          { label: 'Conversations' }
        ]"
      >
        <div headerActions>
          <div class="live-indicator" [class.pulse]="isConnected()">
            <span class="status-dot"></span>
            <span>{{ isConnected() ? 'Live' : 'Connecting...' }}</span>
          </div>
        </div>
      </app-page-header>

      <!-- Live Stats -->
      <div class="stats-bar">
        <div class="stat-pill">
          <span class="material-symbols-outlined">people</span>
          <span class="stat-value">{{ liveStats()?.active_users || 0 }}</span>
          <span class="stat-label">Active Users</span>
        </div>
        <div class="stat-pill">
          <span class="material-symbols-outlined">forum</span>
          <span class="stat-value">{{ liveStats()?.active_conversations || 0 }}</span>
          <span class="stat-label">Conversations</span>
        </div>
        <div class="stat-pill">
          <span class="material-symbols-outlined">speed</span>
          <span class="stat-value">{{ liveStats()?.messages_per_minute || 0 }}/min</span>
          <span class="stat-label">Messages</span>
        </div>
        <div class="stat-pill">
          <span class="material-symbols-outlined">timer</span>
          <span class="stat-value">{{ liveStats()?.avg_response_time || 0 }}s</span>
          <span class="stat-label">Avg Response</span>
        </div>
      </div>

      <div class="live-layout">
        <!-- Conversations List -->
        <div class="conversations-panel">
          <div class="panel-header">
            <h3>Active Sessions</h3>
            <div class="search-box">
              <span class="material-symbols-outlined">search</span>
              <input type="text" placeholder="Search..." [(ngModel)]="searchQuery" />
            </div>
          </div>

          <div class="filter-tabs">
            <button
              class="filter-tab"
              [class.active]="statusFilter() === 'all'"
              (click)="setStatusFilter('all')"
            >
              All
            </button>
            <button
              class="filter-tab"
              [class.active]="statusFilter() === 'active'"
              (click)="setStatusFilter('active')"
            >
              Active
            </button>
            <button
              class="filter-tab"
              [class.active]="statusFilter() === 'flagged'"
              (click)="setStatusFilter('flagged')"
            >
              Flagged
              @if (flaggedCount() > 0) {
                <span class="badge-count">{{ flaggedCount() }}</span>
              }
            </button>
          </div>

          @if (loading()) {
            <div class="panel-loading">
              <span class="spinner"></span>
            </div>
          } @else {
            <div class="conversations-list">
              @for (conv of filteredConversations(); track conv.id) {
                <div
                  class="conversation-item"
                  [class.active]="selectedConversation()?.id === conv.id"
                  [class.flagged]="conv.is_flagged"
                  (click)="selectConversation(conv)"
                >
                  <div class="conv-avatar">
                    <span class="avatar-text">{{ getInitials(conv.user_name) }}</span>
                    <span class="status-indicator" [class]="conv.status"></span>
                  </div>
                  <div class="conv-info">
                    <div class="conv-header">
                      <span class="conv-name">{{ conv.user_name }}</span>
                      <span class="conv-time">{{ formatTime(conv.last_message_at) }}</span>
                    </div>
                    <div class="conv-preview">
                      <span class="conv-subject">{{ conv.subject || 'General' }}</span>
                      <span class="conv-messages">{{ conv.message_count }} msgs</span>
                    </div>
                  </div>
                  @if (conv.is_flagged) {
                    <span class="flag-icon material-symbols-outlined">flag</span>
                  }
                </div>
              } @empty {
                <div class="empty-list">
                  <span class="material-symbols-outlined">chat_bubble_outline</span>
                  <p>No conversations found</p>
                </div>
              }
            </div>
          }
        </div>

        <!-- Conversation Detail -->
        <div class="detail-panel">
          @if (selectedConversation()) {
            <div class="detail-header">
              <div class="user-info">
                <div class="user-avatar">
                  {{ getInitials(selectedConversation()!.user_name) }}
                </div>
                <div class="user-details">
                  <h3>{{ selectedConversation()!.user_name }}</h3>
                  <p>{{ selectedConversation()!.user_email }}</p>
                </div>
              </div>
              <div class="header-actions">
                <button
                  class="action-btn"
                  [class.flagged]="selectedConversation()!.is_flagged"
                  (click)="toggleFlag()"
                >
                  <span class="material-symbols-outlined">
                    {{ selectedConversation()!.is_flagged ? 'flag_off' : 'flag' }}
                  </span>
                </button>
                <button class="action-btn danger" (click)="endConversation()">
                  <span class="material-symbols-outlined">cancel</span>
                </button>
              </div>
            </div>

            <div class="conversation-meta">
              <div class="meta-item">
                <span class="material-symbols-outlined">school</span>
                <span>{{ selectedConversation()!.subject || 'General' }}</span>
              </div>
              <div class="meta-item">
                <span class="material-symbols-outlined">topic</span>
                <span>{{ selectedConversation()!.topic || 'N/A' }}</span>
              </div>
              <div class="meta-item">
                <span class="material-symbols-outlined">schedule</span>
                <span>Started {{ formatTime(selectedConversation()!.started_at) }}</span>
              </div>
            </div>

            <div class="messages-container">
              @for (msg of messages(); track msg.id) {
                <div class="message" [class]="msg.role">
                  <div class="message-bubble">
                    <p>{{ msg.content }}</p>
                    <span class="message-time">{{ formatMessageTime(msg.timestamp) }}</span>
                  </div>
                </div>
              } @empty {
                <div class="no-messages">
                  <span class="material-symbols-outlined">chat</span>
                  <p>No messages yet</p>
                </div>
              }
            </div>

            <!-- Intervention Panel -->
            <div class="intervention-panel">
              <div class="intervention-header">
                <span class="material-symbols-outlined">support_agent</span>
                <span>Admin Intervention</span>
              </div>
              <div class="intervention-form">
                <textarea
                  [(ngModel)]="interventionMessage"
                  placeholder="Type a message to intervene in this conversation..."
                  rows="2"
                ></textarea>
                <button class="btn btn-primary" (click)="sendIntervention()" [disabled]="!interventionMessage.trim()">
                  <span class="material-symbols-outlined">send</span>
                  Send
                </button>
              </div>
            </div>
          } @else {
            <div class="no-selection">
              <span class="material-symbols-outlined">chat_bubble</span>
              <h3>Select a conversation</h3>
              <p>Choose a conversation from the list to view details</p>
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

    .stats-bar {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }

    .stat-pill {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: var(--primary);
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

    .search-box {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.375rem 0.75rem;
      background-color: var(--background);
      border-radius: 0.375rem;

      .material-symbols-outlined {
        font-size: 1.125rem;
        color: var(--text-muted);
      }

      input {
        border: none;
        background: transparent;
        font-size: 0.875rem;
        width: 120px;
        color: var(--text-primary);

        &::placeholder {
          color: var(--text-muted);
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

      .badge-count {
        padding: 0.125rem 0.375rem;
        font-size: 0.625rem;
        background-color: var(--error);
        color: white;
        border-radius: 9999px;
      }
    }

    .conversations-list {
      flex: 1;
      overflow-y: auto;
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

      &.flagged {
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
    }

    .flag-icon {
      color: var(--warning);
      font-size: 1.25rem;
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

    .header-actions {
      display: flex;
      gap: 0.5rem;
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

      &.flagged {
        color: var(--warning);
      }

      &.danger:hover {
        background-color: rgba(239, 68, 68, 0.1);
        color: var(--error);
      }
    }

    .conversation-meta {
      display: flex;
      gap: 1.5rem;
      padding: 0.75rem 1rem;
      background-color: var(--background);
      border-bottom: 1px solid var(--border);
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
    }

    .messages-container {
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .message {
      display: flex;

      &.user {
        justify-content: flex-end;

        .message-bubble {
          background-color: var(--primary);
          color: white;

          .message-time {
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
      }

      .message-time {
        font-size: 0.625rem;
        color: var(--text-muted);
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

    .intervention-form {
      display: flex;
      gap: 0.5rem;

      textarea {
        flex: 1;
        padding: 0.75rem;
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        font-size: 0.875rem;
        resize: none;

        &:focus {
          border-color: var(--primary);
        }
      }

      .btn {
        align-self: flex-end;
      }
    }

    .no-selection {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: var(--text-muted);
      text-align: center;

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
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
  `]
})
export class LiveConversationsComponent implements OnInit, OnDestroy {
  private liveService = inject(LiveService);
  private toastService = inject(ToastService);

  // State
  loading = signal(true);
  isConnected = signal(true);
  conversations = signal<Conversation[]>([]);
  selectedConversation = signal<Conversation | null>(null);
  messages = signal<ConversationMessage[]>([]);
  liveStats = signal<LiveStats | null>(null);

  // Filters
  searchQuery = '';
  statusFilter = signal<'all' | 'active' | 'flagged'>('all');

  // Intervention
  interventionMessage = '';

  // Computed
  flaggedCount = computed(() => this.conversations().filter(c => c.is_flagged).length);

  filteredConversations = computed(() => {
    let convs = this.conversations();
    const filter = this.statusFilter();

    if (filter === 'active') {
      convs = convs.filter(c => c.status === ConversationStatus.ACTIVE);
    } else if (filter === 'flagged') {
      convs = convs.filter(c => c.is_flagged);
    }

    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      convs = convs.filter(c =>
        c.user_name.toLowerCase().includes(query) ||
        c.user_email.toLowerCase().includes(query)
      );
    }

    return convs;
  });

  private refreshInterval: any;

  ngOnInit(): void {
    this.loadConversations();
    this.loadStats();
    this.startPolling();
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  loadConversations(): void {
    this.loading.set(true);

    // Mock data
    setTimeout(() => {
      this.conversations.set([
        {
          id: 'conv_001',
          user_id: 'user_001',
          user_name: 'Tinashe Moyo',
          user_email: 'tinashe@student.zw',
          subject: 'Mathematics',
          topic: 'Algebra',
          status: ConversationStatus.ACTIVE,
          message_count: 12,
          started_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
          last_message_at: new Date(Date.now() - 30 * 1000).toISOString(),
          is_flagged: false
        },
        {
          id: 'conv_002',
          user_id: 'user_002',
          user_name: 'Chipo Ndlovu',
          user_email: 'chipo@student.zw',
          subject: 'Science',
          topic: 'Chemistry',
          status: ConversationStatus.ACTIVE,
          message_count: 8,
          started_at: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
          last_message_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
          is_flagged: true,
          flag_reason: 'Potential inappropriate content'
        },
        {
          id: 'conv_003',
          user_id: 'user_003',
          user_name: 'Farai Gumbo',
          user_email: 'farai@student.zw',
          subject: 'History',
          topic: 'World War II',
          status: ConversationStatus.IDLE,
          message_count: 5,
          started_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
          last_message_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
          is_flagged: false
        }
      ]);
      this.loading.set(false);
    }, 800);
  }

  loadStats(): void {
    this.liveStats.set({
      active_users: 156,
      active_conversations: 89,
      active_competitions: 3,
      messages_per_minute: 42,
      tokens_per_minute: 15600,
      avg_response_time: 1.2
    });
  }

  startPolling(): void {
    this.refreshInterval = setInterval(() => {
      // Simulate live updates
      this.loadStats();
    }, 5000);
  }

  setStatusFilter(filter: 'all' | 'active' | 'flagged'): void {
    this.statusFilter.set(filter);
  }

  selectConversation(conv: Conversation): void {
    this.selectedConversation.set(conv);
    this.loadMessages(conv.id);
  }

  loadMessages(conversationId: string): void {
    // Mock messages
    this.messages.set([
      {
        id: 'msg_001',
        conversation_id: conversationId,
        role: MessageRole.USER,
        content: 'Can you help me understand quadratic equations?',
        timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString()
      },
      {
        id: 'msg_002',
        conversation_id: conversationId,
        role: MessageRole.ASSISTANT,
        content: 'Of course! A quadratic equation is an equation of the form ax² + bx + c = 0, where a, b, and c are constants and a ≠ 0. Would you like me to explain how to solve them?',
        timestamp: new Date(Date.now() - 9 * 60 * 1000).toISOString()
      },
      {
        id: 'msg_003',
        conversation_id: conversationId,
        role: MessageRole.USER,
        content: 'Yes please! How do I use the quadratic formula?',
        timestamp: new Date(Date.now() - 8 * 60 * 1000).toISOString()
      },
      {
        id: 'msg_004',
        conversation_id: conversationId,
        role: MessageRole.ASSISTANT,
        content: 'The quadratic formula is x = (-b ± √(b²-4ac)) / 2a. Let me walk you through an example...',
        timestamp: new Date(Date.now() - 7 * 60 * 1000).toISOString()
      }
    ]);
  }

  toggleFlag(): void {
    const conv = this.selectedConversation();
    if (conv) {
      conv.is_flagged = !conv.is_flagged;
      this.selectedConversation.set({ ...conv });
      this.toastService.success(
        conv.is_flagged ? 'Conversation Flagged' : 'Flag Removed',
        conv.is_flagged ? 'This conversation has been flagged for review' : 'Flag has been removed'
      );
    }
  }

  endConversation(): void {
    const conv = this.selectedConversation();
    if (conv) {
      this.toastService.success('Conversation Ended', `Session with ${conv.user_name} has been terminated`);
      this.selectedConversation.set(null);
      this.messages.set([]);
    }
  }

  sendIntervention(): void {
    if (!this.interventionMessage.trim()) return;

    const conv = this.selectedConversation();
    if (conv) {
      this.toastService.success('Intervention Sent', 'Your message has been sent to the conversation');
      this.interventionMessage = '';
    }
  }

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
}
