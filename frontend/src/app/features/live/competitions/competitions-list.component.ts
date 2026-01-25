import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ToastService } from '../../../core/services/toast.service';

interface Competition {
  id: string;
  title: string;
  description: string;
  subject: string;
  status: 'scheduled' | 'live' | 'ended';
  start_time: string;
  end_time: string;
  duration_minutes: number;
  participants_count: number;
  max_participants: number;
  prize_pool: string;
  difficulty: 'easy' | 'medium' | 'hard';
}

@Component({
  selector: 'app-competitions-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>Competitions</h1>
          <p class="subtitle">Manage live academic competitions</p>
        </div>
        <div class="header-actions">
          <button class="btn-primary" (click)="openCreateCompetition()">
            <span class="material-symbols-outlined">add</span>
            Create Competition
          </button>
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-card live">
          <div class="stat-icon">
            <span class="material-symbols-outlined">sensors</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ getLiveCount() }}</span>
            <span class="stat-label">Live Now</span>
          </div>
          @if (getLiveCount() > 0) {
            <div class="pulse-indicator"></div>
          }
        </div>
        <div class="stat-card">
          <div class="stat-icon scheduled">
            <span class="material-symbols-outlined">event</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ getScheduledCount() }}</span>
            <span class="stat-label">Scheduled</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon ended">
            <span class="material-symbols-outlined">flag</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ getEndedCount() }}</span>
            <span class="stat-label">Completed</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon participants">
            <span class="material-symbols-outlined">group</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ getTotalParticipants() }}</span>
            <span class="stat-label">Total Participants</span>
          </div>
        </div>
      </div>

      <div class="tabs">
        <button [class.active]="activeTab === 'all'" (click)="activeTab = 'all'">All</button>
        <button [class.active]="activeTab === 'live'" (click)="activeTab = 'live'">
          Live
          @if (getLiveCount() > 0) {
            <span class="count-badge live">{{ getLiveCount() }}</span>
          }
        </button>
        <button [class.active]="activeTab === 'scheduled'" (click)="activeTab = 'scheduled'">Scheduled</button>
        <button [class.active]="activeTab === 'ended'" (click)="activeTab = 'ended'">Ended</button>
      </div>

      @if (isLoading()) {
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Loading competitions...</p>
        </div>
      } @else {
        <div class="competitions-grid">
          @for (comp of getFilteredCompetitions(); track comp.id) {
            <div class="competition-card" [class]="comp.status">
              <div class="card-header">
                <div class="status-indicator" [class]="comp.status">
                  @if (comp.status === 'live') {
                    <span class="material-symbols-outlined">sensors</span>
                    Live
                  } @else if (comp.status === 'scheduled') {
                    <span class="material-symbols-outlined">schedule</span>
                    Scheduled
                  } @else {
                    <span class="material-symbols-outlined">check_circle</span>
                    Ended
                  }
                </div>
                <span class="difficulty-badge" [class]="comp.difficulty">{{ comp.difficulty }}</span>
              </div>
              <div class="card-body">
                <h3>{{ comp.title }}</h3>
                <p class="description">{{ comp.description }}</p>
                <div class="meta">
                  <span class="subject">
                    <span class="material-symbols-outlined">menu_book</span>
                    {{ comp.subject }}
                  </span>
                  <span class="duration">
                    <span class="material-symbols-outlined">timer</span>
                    {{ comp.duration_minutes }} min
                  </span>
                </div>
                <div class="time-info">
                  @if (comp.status === 'scheduled') {
                    <span class="material-symbols-outlined">event</span>
                    Starts {{ comp.start_time | date:'short' }}
                  } @else if (comp.status === 'live') {
                    <span class="material-symbols-outlined">schedule</span>
                    Ends {{ comp.end_time | date:'shortTime' }}
                  } @else {
                    <span class="material-symbols-outlined">flag</span>
                    Ended {{ comp.end_time | date:'short' }}
                  }
                </div>
              </div>
              <div class="card-footer">
                <div class="participants">
                  <span class="material-symbols-outlined">group</span>
                  {{ comp.participants_count }}/{{ comp.max_participants }}
                </div>
                @if (comp.prize_pool) {
                  <div class="prize">
                    <span class="material-symbols-outlined">emoji_events</span>
                    {{ comp.prize_pool }}
                  </div>
                }
              </div>
              <div class="card-actions">
                @if (comp.status === 'live') {
                  <button class="btn-primary" (click)="viewLive(comp)">
                    <span class="material-symbols-outlined">visibility</span>
                    Monitor
                  </button>
                  <button class="btn-danger" (click)="endCompetition(comp)">
                    <span class="material-symbols-outlined">stop</span>
                    End
                  </button>
                } @else if (comp.status === 'scheduled') {
                  <button class="btn-secondary" (click)="editCompetition(comp)">
                    <span class="material-symbols-outlined">edit</span>
                    Edit
                  </button>
                  <button class="btn-primary" (click)="startCompetition(comp)">
                    <span class="material-symbols-outlined">play_arrow</span>
                    Start
                  </button>
                } @else {
                  <button class="btn-secondary" (click)="viewResults(comp)">
                    <span class="material-symbols-outlined">leaderboard</span>
                    Results
                  </button>
                  <button class="btn-secondary" (click)="duplicateCompetition(comp)">
                    <span class="material-symbols-outlined">content_copy</span>
                    Duplicate
                  </button>
                }
              </div>
            </div>
          } @empty {
            <div class="empty-state">
              <span class="material-symbols-outlined">emoji_events</span>
              <h3>No competitions found</h3>
              <p>Create your first competition to engage students.</p>
              <button class="btn-primary" (click)="openCreateCompetition()">Create Competition</button>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .page-container { padding: 1.5rem; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .header-info h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
    .header-info .subtitle { font-size: 0.875rem; color: var(--text-secondary); }

    .btn-primary, .btn-secondary, .btn-danger {
      display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem;
      font-size: 0.875rem; font-weight: 500; border-radius: 0.5rem; cursor: pointer; transition: all 0.15s ease;
      .material-symbols-outlined { font-size: 1.125rem; }
    }
    .btn-primary { background-color: var(--primary); color: white; border: none; &:hover { background-color: #005238; } }
    .btn-secondary { background-color: var(--surface); color: var(--text-primary); border: 1px solid var(--border); &:hover { background-color: var(--hover); } }
    .btn-danger { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; border: none; &:hover { background-color: rgba(239, 68, 68, 0.2); } }

    .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
    @media (max-width: 1024px) { .stats-row { grid-template-columns: repeat(2, 1fr); } }

    .stat-card {
      position: relative; display: flex; align-items: center; gap: 1rem; padding: 1rem 1.25rem;
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem;
      &.live { border-color: #ef4444; background-color: rgba(239, 68, 68, 0.05); }
    }

    .stat-icon {
      width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 0.75rem;
      background-color: rgba(239, 68, 68, 0.1);
      .material-symbols-outlined { color: #ef4444; font-size: 1.5rem; }
      &.scheduled { background-color: rgba(59, 130, 246, 0.1); .material-symbols-outlined { color: #3b82f6; } }
      &.ended { background-color: rgba(16, 185, 129, 0.1); .material-symbols-outlined { color: #10b981; } }
      &.participants { background-color: rgba(139, 92, 246, 0.1); .material-symbols-outlined { color: #8b5cf6; } }
    }

    .stat-info { display: flex; flex-direction: column; }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
    .stat-label { font-size: 0.75rem; color: var(--text-secondary); }

    .pulse-indicator {
      position: absolute; top: 1rem; right: 1rem; width: 10px; height: 10px;
      background-color: #ef4444; border-radius: 50%; animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
      70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
      100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }

    .tabs {
      display: flex; gap: 0.5rem; margin-bottom: 1.5rem; padding: 0.25rem;
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem; width: fit-content;
      button {
        display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem;
        font-size: 0.875rem; font-weight: 500; background: transparent;
        color: var(--text-secondary); border: none; border-radius: 0.375rem; cursor: pointer;
        &.active { background-color: var(--primary); color: white; }
        &:hover:not(.active) { background-color: var(--hover); }
      }
    }

    .count-badge {
      padding: 0.125rem 0.5rem; font-size: 0.625rem; font-weight: 600; border-radius: 9999px;
      &.live { background-color: #ef4444; color: white; }
    }

    .loading-state { display: flex; flex-direction: column; align-items: center; padding: 4rem; }
    .spinner { width: 2.5rem; height: 2.5rem; border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 1rem; }

    .competitions-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 1.25rem; }

    .competition-card {
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; overflow: hidden; transition: all 0.15s ease;
      &:hover { border-color: var(--primary); transform: translateY(-2px); }
      &.live { border-color: #ef4444; }
    }

    .card-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem; border-bottom: 1px solid var(--border); }

    .status-indicator {
      display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.25rem 0.75rem;
      font-size: 0.75rem; font-weight: 500; border-radius: 9999px;
      .material-symbols-outlined { font-size: 0.875rem; }
      &.live { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; }
      &.scheduled { background-color: rgba(59, 130, 246, 0.1); color: #3b82f6; }
      &.ended { background-color: rgba(16, 185, 129, 0.1); color: #10b981; }
    }

    .difficulty-badge {
      padding: 0.125rem 0.5rem; font-size: 0.625rem; font-weight: 600; border-radius: 0.25rem; text-transform: uppercase;
      &.easy { background-color: rgba(16, 185, 129, 0.1); color: #10b981; }
      &.medium { background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; }
      &.hard { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; }
    }

    .card-body { padding: 1.25rem; }
    .card-body h3 { font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; }
    .description { font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 1rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

    .meta { display: flex; gap: 1rem; margin-bottom: 0.75rem; }
    .meta span { display: flex; align-items: center; gap: 0.375rem; font-size: 0.75rem; color: var(--text-secondary); .material-symbols-outlined { font-size: 1rem; } }

    .time-info { display: flex; align-items: center; gap: 0.375rem; font-size: 0.75rem; color: var(--text-tertiary); .material-symbols-outlined { font-size: 1rem; } }

    .card-footer {
      display: flex; justify-content: space-between; padding: 0.75rem 1.25rem; background-color: var(--background); border-top: 1px solid var(--border);
      .participants, .prize { display: flex; align-items: center; gap: 0.375rem; font-size: 0.75rem; color: var(--text-secondary); .material-symbols-outlined { font-size: 1rem; } }
      .prize { color: #f59e0b; .material-symbols-outlined { color: #f59e0b; } }
    }

    .card-actions { display: flex; gap: 0.75rem; padding: 1rem 1.25rem; border-top: 1px solid var(--border); button { flex: 1; justify-content: center; } }

    .empty-state {
      grid-column: 1 / -1; display: flex; flex-direction: column; align-items: center; padding: 4rem;
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem;
      .material-symbols-outlined { font-size: 4rem; color: var(--text-tertiary); margin-bottom: 1rem; }
      h3 { font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; }
      p { color: var(--text-secondary); margin-bottom: 1.5rem; }
    }

    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class CompetitionsListComponent implements OnInit {
  private toastService = inject(ToastService);

  competitions = signal<Competition[]>([]);
  isLoading = signal(true);
  activeTab: 'all' | 'live' | 'scheduled' | 'ended' = 'all';

  ngOnInit(): void { this.loadCompetitions(); }

  loadCompetitions(): void {
    this.isLoading.set(true);
    const mock: Competition[] = [
      { id: '1', title: 'Math Challenge 2024', description: 'Test your algebra and geometry skills in this exciting competition.', subject: 'Mathematics', status: 'live', start_time: '2024-06-15T10:00:00', end_time: '2024-06-15T11:30:00', duration_minutes: 90, participants_count: 156, max_participants: 200, prize_pool: '50 Points', difficulty: 'medium' },
      { id: '2', title: 'Physics Olympiad', description: 'Advanced physics problems for top students.', subject: 'Physics', status: 'scheduled', start_time: '2024-06-20T14:00:00', end_time: '2024-06-20T16:00:00', duration_minutes: 120, participants_count: 45, max_participants: 100, prize_pool: '100 Points', difficulty: 'hard' },
      { id: '3', title: 'English Essay Contest', description: 'Creative writing competition for all levels.', subject: 'English', status: 'scheduled', start_time: '2024-06-18T09:00:00', end_time: '2024-06-18T10:30:00', duration_minutes: 90, participants_count: 78, max_participants: 150, prize_pool: '75 Points', difficulty: 'easy' },
      { id: '4', title: 'Chemistry Quiz Bowl', description: 'Fast-paced chemistry questions competition.', subject: 'Chemistry', status: 'ended', start_time: '2024-06-10T15:00:00', end_time: '2024-06-10T16:00:00', duration_minutes: 60, participants_count: 120, max_participants: 120, prize_pool: '50 Points', difficulty: 'medium' },
      { id: '5', title: 'Biology Basics', description: 'Test your knowledge of cell biology and genetics.', subject: 'Biology', status: 'ended', start_time: '2024-06-08T11:00:00', end_time: '2024-06-08T12:00:00', duration_minutes: 60, participants_count: 89, max_participants: 100, prize_pool: '30 Points', difficulty: 'easy' },
    ];
    setTimeout(() => { this.competitions.set(mock); this.isLoading.set(false); }, 500);
  }

  getFilteredCompetitions(): Competition[] {
    if (this.activeTab === 'all') return this.competitions();
    return this.competitions().filter(c => c.status === this.activeTab);
  }

  getLiveCount(): number { return this.competitions().filter(c => c.status === 'live').length; }
  getScheduledCount(): number { return this.competitions().filter(c => c.status === 'scheduled').length; }
  getEndedCount(): number { return this.competitions().filter(c => c.status === 'ended').length; }
  getTotalParticipants(): number { return this.competitions().reduce((sum, c) => sum + c.participants_count, 0); }

  openCreateCompetition(): void { this.toastService.info('Create competition modal would open here'); }
  viewLive(comp: Competition): void { this.toastService.info(`Monitoring: ${comp.title}`); }
  endCompetition(comp: Competition): void { this.toastService.warning(`End competition: ${comp.title}`); }
  editCompetition(comp: Competition): void { this.toastService.info(`Edit: ${comp.title}`); }
  startCompetition(comp: Competition): void { this.toastService.success(`Starting: ${comp.title}`); }
  viewResults(comp: Competition): void { this.toastService.info(`View results: ${comp.title}`); }
  duplicateCompetition(comp: Competition): void { this.toastService.info(`Duplicate: ${comp.title}`); }
}
