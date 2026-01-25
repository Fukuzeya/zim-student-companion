import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-engagement-analytics',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>Engagement Analytics</h1>
          <p class="subtitle">User engagement and retention metrics</p>
        </div>
        <div class="header-actions">
          <select [(value)]="selectedPeriod">
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
          <button class="btn-secondary">
            <span class="material-symbols-outlined">download</span>
            Export
          </button>
        </div>
      </div>

      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon blue">
            <span class="material-symbols-outlined">schedule</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">Avg. Session Duration</span>
            <span class="metric-value">24m 35s</span>
            <span class="metric-change positive">+12% vs last period</span>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon green">
            <span class="material-symbols-outlined">repeat</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">Retention Rate</span>
            <span class="metric-value">78.5%</span>
            <span class="metric-change positive">+5.2% vs last period</span>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon purple">
            <span class="material-symbols-outlined">quiz</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">Questions per User</span>
            <span class="metric-value">7.2</span>
            <span class="metric-change positive">+18% vs last period</span>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon orange">
            <span class="material-symbols-outlined">trending_up</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">Daily Active Users</span>
            <span class="metric-value">3,456</span>
            <span class="metric-change positive">+8.3% vs last period</span>
          </div>
        </div>
      </div>

      <div class="content-row">
        <div class="card">
          <div class="card-header">
            <h3>User Activity Heatmap</h3>
          </div>
          <div class="card-body">
            <div class="heatmap">
              <div class="heatmap-row">
                <span class="hour-label">6AM</span>
                @for (day of days; track day) {
                  <div class="heatmap-cell" [style.opacity]="getHeatmapValue(0, $index)"></div>
                }
              </div>
              <div class="heatmap-row">
                <span class="hour-label">9AM</span>
                @for (day of days; track day) {
                  <div class="heatmap-cell" [style.opacity]="getHeatmapValue(1, $index)"></div>
                }
              </div>
              <div class="heatmap-row">
                <span class="hour-label">12PM</span>
                @for (day of days; track day) {
                  <div class="heatmap-cell" [style.opacity]="getHeatmapValue(2, $index)"></div>
                }
              </div>
              <div class="heatmap-row">
                <span class="hour-label">3PM</span>
                @for (day of days; track day) {
                  <div class="heatmap-cell" [style.opacity]="getHeatmapValue(3, $index)"></div>
                }
              </div>
              <div class="heatmap-row">
                <span class="hour-label">6PM</span>
                @for (day of days; track day) {
                  <div class="heatmap-cell" [style.opacity]="getHeatmapValue(4, $index)"></div>
                }
              </div>
              <div class="heatmap-row">
                <span class="hour-label">9PM</span>
                @for (day of days; track day) {
                  <div class="heatmap-cell" [style.opacity]="getHeatmapValue(5, $index)"></div>
                }
              </div>
              <div class="heatmap-labels">
                <span></span>
                @for (day of days; track day) {
                  <span>{{ day }}</span>
                }
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Top Engaged Users</h3>
          </div>
          <div class="card-body">
            <div class="users-list">
              @for (user of topUsers; track user.id) {
                <div class="user-item">
                  <div class="user-avatar">{{ user.initials }}</div>
                  <div class="user-info">
                    <span class="user-name">{{ user.name }}</span>
                    <span class="user-stats">{{ user.sessions }} sessions · {{ user.questions }} questions</span>
                  </div>
                  <div class="user-score">
                    <span class="score">{{ user.score }}</span>
                    <span class="label">pts</span>
                  </div>
                </div>
              }
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>Engagement by Feature</h3>
        </div>
        <div class="card-body">
          <div class="features-list">
            @for (feature of features; track feature.name) {
              <div class="feature-item">
                <div class="feature-info">
                  <span class="material-symbols-outlined">{{ feature.icon }}</span>
                  <span class="feature-name">{{ feature.name }}</span>
                </div>
                <div class="feature-bar">
                  <div class="bar-fill" [style.width.%]="feature.percentage" [style.background-color]="feature.color"></div>
                </div>
                <span class="feature-value">{{ feature.value }}</span>
              </div>
            }
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .page-container { padding: 1.5rem; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .header-info h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
    .header-info .subtitle { font-size: 0.875rem; color: var(--text-secondary); }
    .header-actions { display: flex; gap: 0.75rem; }
    .header-actions select { padding: 0.5rem 1rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem; color: var(--text-primary); font-size: 0.875rem; }
    .btn-secondary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; font-size: 0.875rem; font-weight: 500; background-color: var(--surface); color: var(--text-primary); border: 1px solid var(--border); border-radius: 0.5rem; cursor: pointer; &:hover { background-color: var(--hover); } }

    .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
    @media (max-width: 1200px) { .metrics-grid { grid-template-columns: repeat(2, 1fr); } }

    .metric-card { display: flex; align-items: center; gap: 1rem; padding: 1.25rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; }
    .metric-icon { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 0.75rem; &.blue { background-color: rgba(59, 130, 246, 0.1); .material-symbols-outlined { color: #3b82f6; } } &.green { background-color: rgba(16, 185, 129, 0.1); .material-symbols-outlined { color: #10b981; } } &.purple { background-color: rgba(139, 92, 246, 0.1); .material-symbols-outlined { color: #8b5cf6; } } &.orange { background-color: rgba(245, 158, 11, 0.1); .material-symbols-outlined { color: #f59e0b; } } }
    .metric-info { display: flex; flex-direction: column; }
    .metric-label { font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.25rem; }
    .metric-value { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
    .metric-change { font-size: 0.75rem; &.positive { color: #10b981; } &.negative { color: #ef4444; } }

    .content-row { display: grid; grid-template-columns: 1.5fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
    @media (max-width: 1024px) { .content-row { grid-template-columns: 1fr; } }

    .card { background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; overflow: hidden; }
    .card-header { padding: 1rem 1.25rem; border-bottom: 1px solid var(--border); h3 { font-size: 1rem; font-weight: 600; color: var(--text-primary); } }
    .card-body { padding: 1.25rem; }

    .heatmap { display: flex; flex-direction: column; gap: 4px; }
    .heatmap-row { display: flex; align-items: center; gap: 4px; }
    .hour-label { width: 40px; font-size: 0.625rem; color: var(--text-tertiary); text-align: right; padding-right: 8px; }
    .heatmap-cell { flex: 1; height: 24px; background-color: var(--primary); border-radius: 4px; min-width: 24px; }
    .heatmap-labels { display: flex; gap: 4px; margin-top: 4px; span { flex: 1; font-size: 0.625rem; color: var(--text-tertiary); text-align: center; &:first-child { width: 40px; } } }

    .users-list { display: flex; flex-direction: column; gap: 0.75rem; }
    .user-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; background-color: var(--background); border-radius: 0.5rem; }
    .user-avatar { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background-color: var(--primary); color: white; font-size: 0.75rem; font-weight: 600; border-radius: 50%; }
    .user-info { flex: 1; }
    .user-name { display: block; font-size: 0.875rem; font-weight: 500; color: var(--text-primary); }
    .user-stats { font-size: 0.75rem; color: var(--text-secondary); }
    .user-score { text-align: right; .score { font-size: 1.25rem; font-weight: 700; color: var(--primary); } .label { display: block; font-size: 0.625rem; color: var(--text-tertiary); } }

    .features-list { display: flex; flex-direction: column; gap: 1rem; }
    .feature-item { display: flex; align-items: center; gap: 1rem; }
    .feature-info { display: flex; align-items: center; gap: 0.5rem; width: 150px; .material-symbols-outlined { font-size: 1.25rem; color: var(--text-secondary); } .feature-name { font-size: 0.875rem; color: var(--text-primary); } }
    .feature-bar { flex: 1; height: 8px; background-color: var(--background); border-radius: 4px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 4px; }
    .feature-value { width: 60px; text-align: right; font-size: 0.875rem; font-weight: 600; color: var(--text-primary); }
  `]
})
export class EngagementAnalyticsComponent implements OnInit {
  selectedPeriod = '30d';
  days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  topUsers = [
    { id: 1, name: 'John Doe', initials: 'JD', sessions: 45, questions: 234, score: 1250 },
    { id: 2, name: 'Jane Smith', initials: 'JS', sessions: 38, questions: 198, score: 1120 },
    { id: 3, name: 'Bob Wilson', initials: 'BW', sessions: 32, questions: 176, score: 980 },
    { id: 4, name: 'Alice Brown', initials: 'AB', sessions: 28, questions: 145, score: 870 },
    { id: 5, name: 'Charlie Davis', initials: 'CD', sessions: 25, questions: 132, score: 750 },
  ];

  features = [
    { name: 'AI Tutor', icon: 'smart_toy', value: '45K', percentage: 90, color: '#3b82f6' },
    { name: 'Past Papers', icon: 'history_edu', value: '32K', percentage: 75, color: '#10b981' },
    { name: 'Competitions', icon: 'emoji_events', value: '18K', percentage: 55, color: '#f59e0b' },
    { name: 'Study Materials', icon: 'menu_book', value: '12K', percentage: 40, color: '#8b5cf6' },
    { name: 'Progress Tracking', icon: 'trending_up', value: '8K', percentage: 25, color: '#ef4444' },
  ];

  heatmapData = [
    [0.2, 0.3, 0.4, 0.3, 0.4, 0.2, 0.1],
    [0.5, 0.7, 0.8, 0.7, 0.8, 0.4, 0.3],
    [0.6, 0.8, 0.9, 0.8, 0.7, 0.5, 0.4],
    [0.7, 0.9, 1.0, 0.9, 0.8, 0.6, 0.5],
    [0.8, 0.9, 0.8, 0.9, 0.7, 0.8, 0.6],
    [0.5, 0.6, 0.5, 0.6, 0.5, 0.7, 0.4],
  ];

  ngOnInit(): void {}

  getHeatmapValue(row: number, col: number): number {
    return this.heatmapData[row][col];
  }
}
