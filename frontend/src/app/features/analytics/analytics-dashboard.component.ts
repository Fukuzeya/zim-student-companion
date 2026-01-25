import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-analytics-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>Analytics Dashboard</h1>
          <p class="subtitle">Platform performance and insights</p>
        </div>
        <div class="header-actions">
          <select [(value)]="selectedPeriod">
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="1y">Last year</option>
          </select>
          <button class="btn-secondary">
            <span class="material-symbols-outlined">download</span>
            Export Report
          </button>
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-header">
            <span class="kpi-label">Total Users</span>
            <span class="kpi-trend positive">
              <span class="material-symbols-outlined">trending_up</span>
              +12.5%
            </span>
          </div>
          <span class="kpi-value">12,458</span>
          <div class="kpi-chart">
            <div class="mini-chart">
              @for (h of [40, 55, 45, 60, 50, 70, 65]; track $index) {
                <div class="bar" [style.height.%]="h"></div>
              }
            </div>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header">
            <span class="kpi-label">Active Sessions</span>
            <span class="kpi-trend positive">
              <span class="material-symbols-outlined">trending_up</span>
              +8.3%
            </span>
          </div>
          <span class="kpi-value">3,247</span>
          <div class="kpi-chart">
            <div class="mini-chart">
              @for (h of [35, 45, 55, 40, 65, 55, 70]; track $index) {
                <div class="bar" [style.height.%]="h"></div>
              }
            </div>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header">
            <span class="kpi-label">Questions Asked</span>
            <span class="kpi-trend positive">
              <span class="material-symbols-outlined">trending_up</span>
              +23.1%
            </span>
          </div>
          <span class="kpi-value">89,542</span>
          <div class="kpi-chart">
            <div class="mini-chart">
              @for (h of [30, 40, 35, 50, 60, 55, 80]; track $index) {
                <div class="bar" [style.height.%]="h"></div>
              }
            </div>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header">
            <span class="kpi-label">Revenue (MRR)</span>
            <span class="kpi-trend positive">
              <span class="material-symbols-outlined">trending_up</span>
              +15.7%
            </span>
          </div>
          <span class="kpi-value">$24,890</span>
          <div class="kpi-chart">
            <div class="mini-chart">
              @for (h of [45, 50, 55, 60, 58, 65, 75]; track $index) {
                <div class="bar" [style.height.%]="h"></div>
              }
            </div>
          </div>
        </div>
      </div>

      <div class="charts-row">
        <div class="card chart-card large">
          <div class="card-header">
            <h3>User Activity Trends</h3>
            <div class="chart-legend">
              <span class="legend-item"><span class="dot active"></span> Active Users</span>
              <span class="legend-item"><span class="dot new"></span> New Users</span>
            </div>
          </div>
          <div class="card-body">
            <div class="chart-placeholder">
              <div class="chart-bars">
                @for (day of weekDays; track day; let i = $index) {
                  <div class="chart-bar-group">
                    <div class="bar active" [style.height.%]="activeData[i]"></div>
                    <div class="bar new" [style.height.%]="newData[i]"></div>
                    <span class="bar-label">{{ day }}</span>
                  </div>
                }
              </div>
            </div>
          </div>
        </div>

        <div class="card chart-card">
          <div class="card-header">
            <h3>Subject Distribution</h3>
          </div>
          <div class="card-body">
            <div class="donut-chart">
              <svg viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="none" stroke="var(--border)" stroke-width="12"/>
                <circle cx="50" cy="50" r="40" fill="none" stroke="#3b82f6" stroke-width="12" stroke-dasharray="75.4 176.9" stroke-dashoffset="0"/>
                <circle cx="50" cy="50" r="40" fill="none" stroke="#10b981" stroke-width="12" stroke-dasharray="50.3 201.9" stroke-dashoffset="-75.4"/>
                <circle cx="50" cy="50" r="40" fill="none" stroke="#f59e0b" stroke-width="12" stroke-dasharray="37.7 214.5" stroke-dashoffset="-125.7"/>
                <circle cx="50" cy="50" r="40" fill="none" stroke="#8b5cf6" stroke-width="12" stroke-dasharray="37.7 214.5" stroke-dashoffset="-163.4"/>
              </svg>
            </div>
            <div class="chart-legend vertical">
              <span class="legend-item"><span class="dot" style="background:#3b82f6"></span> Mathematics (30%)</span>
              <span class="legend-item"><span class="dot" style="background:#10b981"></span> Physics (20%)</span>
              <span class="legend-item"><span class="dot" style="background:#f59e0b"></span> Chemistry (15%)</span>
              <span class="legend-item"><span class="dot" style="background:#8b5cf6"></span> Others (35%)</span>
            </div>
          </div>
        </div>
      </div>

      <div class="quick-links">
        <a routerLink="/analytics/engagement" class="quick-link-card">
          <span class="material-symbols-outlined">groups</span>
          <div class="link-info">
            <h4>Engagement Analytics</h4>
            <p>User engagement and retention metrics</p>
          </div>
          <span class="material-symbols-outlined arrow">arrow_forward</span>
        </a>
        <a routerLink="/analytics/revenue" class="quick-link-card">
          <span class="material-symbols-outlined">payments</span>
          <div class="link-info">
            <h4>Revenue Analytics</h4>
            <p>Financial performance and subscriptions</p>
          </div>
          <span class="material-symbols-outlined arrow">arrow_forward</span>
        </a>
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

    .btn-secondary {
      display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem;
      font-size: 0.875rem; font-weight: 500; background-color: var(--surface);
      color: var(--text-primary); border: 1px solid var(--border); border-radius: 0.5rem; cursor: pointer;
      &:hover { background-color: var(--hover); }
    }

    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
    @media (max-width: 1200px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }

    .kpi-card {
      padding: 1.25rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem;
    }

    .kpi-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
    .kpi-label { font-size: 0.75rem; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; }
    .kpi-trend { display: flex; align-items: center; gap: 0.25rem; font-size: 0.75rem; font-weight: 500; &.positive { color: #10b981; } &.negative { color: #ef4444; } .material-symbols-outlined { font-size: 1rem; } }
    .kpi-value { font-size: 1.75rem; font-weight: 700; color: var(--text-primary); display: block; margin-bottom: 0.75rem; }

    .kpi-chart { height: 40px; }
    .mini-chart { display: flex; align-items: flex-end; gap: 4px; height: 100%; }
    .mini-chart .bar { flex: 1; background-color: var(--primary); border-radius: 2px; min-width: 8px; transition: height 0.3s ease; }

    .charts-row { display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
    @media (max-width: 1024px) { .charts-row { grid-template-columns: 1fr; } }

    .card { background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; overflow: hidden; }
    .card-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem; border-bottom: 1px solid var(--border); h3 { font-size: 1rem; font-weight: 600; color: var(--text-primary); } }
    .card-body { padding: 1.25rem; }

    .chart-legend { display: flex; gap: 1.5rem; &.vertical { flex-direction: column; gap: 0.75rem; margin-top: 1rem; } }
    .legend-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; color: var(--text-secondary); }
    .dot { width: 8px; height: 8px; border-radius: 50%; &.active { background-color: var(--primary); } &.new { background-color: #3b82f6; } }

    .chart-placeholder { height: 200px; }
    .chart-bars { display: flex; align-items: flex-end; justify-content: space-between; height: 100%; padding-bottom: 24px; }
    .chart-bar-group { display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1; height: 100%; }
    .chart-bar-group .bar { width: 20px; border-radius: 4px 4px 0 0; transition: height 0.3s ease; &.active { background-color: var(--primary); } &.new { background-color: #3b82f6; } }
    .bar-label { font-size: 0.625rem; color: var(--text-tertiary); margin-top: auto; }

    .donut-chart { width: 160px; height: 160px; margin: 0 auto; svg { width: 100%; height: 100%; transform: rotate(-90deg); } }

    .quick-links { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
    @media (max-width: 768px) { .quick-links { grid-template-columns: 1fr; } }

    .quick-link-card {
      display: flex; align-items: center; gap: 1rem; padding: 1.25rem;
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem;
      text-decoration: none; transition: all 0.15s ease;
      &:hover { border-color: var(--primary); transform: translateX(4px); }
      > .material-symbols-outlined { font-size: 2rem; color: var(--primary); }
      .arrow { margin-left: auto; color: var(--text-tertiary); }
    }

    .link-info { flex: 1; h4 { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem; } p { font-size: 0.75rem; color: var(--text-secondary); } }
  `]
})
export class AnalyticsDashboardComponent implements OnInit {
  selectedPeriod = '30d';
  weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  activeData = [65, 70, 60, 75, 80, 55, 45];
  newData = [25, 30, 20, 35, 40, 20, 15];

  ngOnInit(): void {}
}
