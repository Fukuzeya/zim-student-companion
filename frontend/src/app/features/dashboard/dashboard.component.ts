import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule, DecimalPipe, CurrencyPipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subject, forkJoin, interval } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { AdminService } from '../../core/services/admin.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';
import {
  DashboardStats,
  DashboardCharts,
  DashboardActivity,
  ActivityItem,
  ActivityType,
  KPICard,
  TimeSeriesPoint,
  ChartDataPoint
} from '../../core/models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    PageHeaderComponent,
    LoadingSpinnerComponent,
    DecimalPipe,
    CurrencyPipe
  ],
  template: `
    <div class="dashboard">
      <app-page-header
        title="Executive Dashboard"
        description="Real-time overview of platform performance and key metrics"
        [breadcrumbs]="[
          { label: 'Portal', link: '/dashboard' },
          { label: 'Dashboard' }
        ]"
      >
        <div headerActions class="header-actions">
          @if (lastUpdated()) {
            <div class="last-updated">
              <span class="material-symbols-outlined">schedule</span>
              Updated {{ formatTimeAgo(lastUpdated()!) }}
            </div>
          }
          <select class="time-range-select" [(value)]="selectedDays" (change)="onDaysChange($event)">
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="60">Last 60 days</option>
            <option value="90">Last 90 days</option>
          </select>
          <button class="btn btn-secondary" (click)="exportReport()">
            <span class="material-symbols-outlined">download</span>
            Export Report
          </button>
          <button class="btn btn-primary" (click)="refreshData()" [disabled]="loading()">
            <span class="material-symbols-outlined" [class.spinning]="loading()">refresh</span>
            {{ loading() ? 'Loading...' : 'Refresh' }}
          </button>
        </div>
      </app-page-header>

      @if (loading() && !stats()) {
        <app-loading-spinner message="Loading dashboard data..." />
      } @else if (error()) {
        <div class="error-state">
          <span class="material-symbols-outlined">error</span>
          <h3>Failed to load dashboard</h3>
          <p>{{ error() }}</p>
          <button class="btn btn-primary" (click)="refreshData()">Try Again</button>
        </div>
      } @else {
        <!-- KPI Cards Grid -->
        <section class="kpi-section">
          <h2 class="section-title">Key Performance Indicators</h2>
          <div class="kpi-grid">
            @for (kpi of kpiCards(); track kpi.key) {
              <div class="kpi-card" [class]="kpi.colorClass">
                <div class="kpi-header">
                  <div class="kpi-icon">
                    <span class="material-symbols-outlined">{{ kpi.icon }}</span>
                  </div>
                  @if (kpi.data.change_percent !== null) {
                    <div class="kpi-trend"
                         [class.up]="kpi.data.change_direction === 'up'"
                         [class.down]="kpi.data.change_direction === 'down'"
                         [class.stable]="kpi.data.change_direction === 'stable'">
                      <span class="material-symbols-outlined">
                        {{ kpi.data.change_direction === 'up' ? 'trending_up' :
                           kpi.data.change_direction === 'down' ? 'trending_down' : 'trending_flat' }}
                      </span>
                      <span>{{ kpi.data.change_percent | number:'1.1-1' }}%</span>
                    </div>
                  }
                </div>
                <div class="kpi-body">
                  <span class="kpi-value">
                    {{ kpi.data.currency ? (kpi.data.value | currency:kpi.data.currency:'symbol':'1.0-0') :
                       formatKpiValue(kpi.data.value) }}{{ kpi.data.suffix || '' }}
                  </span>
                  <span class="kpi-label">{{ kpi.data.label }}</span>
                </div>
                <div class="kpi-footer">
                  <span class="kpi-period">{{ kpi.data.period }}</span>
                </div>
              </div>
            }
          </div>
        </section>

        <!-- Main Charts Row -->
        <section class="charts-section">
          <div class="charts-grid">
            <!-- User Growth Chart -->
            <div class="chart-card">
              <div class="chart-header">
                <div>
                  <h3>User Growth</h3>
                  <p class="chart-subtitle">New user registrations over time</p>
                </div>
                <div class="chart-value-highlight">
                  <span class="highlight-value">{{ getTotalFromSeries(charts()?.user_growth) | number }}</span>
                  <span class="highlight-label">Total New Users</span>
                </div>
              </div>
              <div class="chart-body">
                @if (charts()?.user_growth?.length) {
                  <svg class="line-chart" viewBox="0 0 800 200" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="userGrowthGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="var(--primary)" stop-opacity="0.3"/>
                        <stop offset="100%" stop-color="var(--primary)" stop-opacity="0"/>
                      </linearGradient>
                    </defs>
                    <g class="grid-lines">
                      @for (i of [0, 1, 2, 3, 4]; track i) {
                        <line [attr.x1]="0" [attr.y1]="i * 50" [attr.x2]="800" [attr.y2]="i * 50"/>
                      }
                    </g>
                    <path [attr.d]="getAreaPath(charts()!.user_growth, 800, 200)" fill="url(#userGrowthGradient)"/>
                    <path [attr.d]="getLinePath(charts()!.user_growth, 800, 200)" class="chart-line primary"/>
                    @for (point of getChartPoints(charts()!.user_growth, 800, 200); track point.x) {
                      <circle [attr.cx]="point.x" [attr.cy]="point.y" r="3" class="chart-point primary"/>
                    }
                  </svg>
                  <div class="chart-x-axis">
                    @for (label of getXAxisLabels(charts()!.user_growth); track label) {
                      <span>{{ label }}</span>
                    }
                  </div>
                } @else {
                  <div class="chart-empty">
                    <span class="material-symbols-outlined">show_chart</span>
                    <p>No data available</p>
                  </div>
                }
              </div>
            </div>

            <!-- Revenue Trend Chart -->
            <div class="chart-card">
              <div class="chart-header">
                <div>
                  <h3>Revenue Trend</h3>
                  <p class="chart-subtitle">Daily revenue from completed payments</p>
                </div>
                <div class="chart-value-highlight revenue">
                  <span class="highlight-value">{{ getTotalFromSeries(charts()?.revenue_trend) | currency:'USD':'symbol':'1.0-0' }}</span>
                  <span class="highlight-label">Total Revenue</span>
                </div>
              </div>
              <div class="chart-body">
                @if (charts()?.revenue_trend?.length) {
                  <svg class="line-chart" viewBox="0 0 800 200" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#10b981" stop-opacity="0.3"/>
                        <stop offset="100%" stop-color="#10b981" stop-opacity="0"/>
                      </linearGradient>
                    </defs>
                    <g class="grid-lines">
                      @for (i of [0, 1, 2, 3, 4]; track i) {
                        <line [attr.x1]="0" [attr.y1]="i * 50" [attr.x2]="800" [attr.y2]="i * 50"/>
                      }
                    </g>
                    <path [attr.d]="getAreaPath(charts()!.revenue_trend, 800, 200)" fill="url(#revenueGradient)"/>
                    <path [attr.d]="getLinePath(charts()!.revenue_trend, 800, 200)" class="chart-line success"/>
                    @for (point of getChartPoints(charts()!.revenue_trend, 800, 200); track point.x) {
                      <circle [attr.cx]="point.x" [attr.cy]="point.y" r="3" class="chart-point success"/>
                    }
                  </svg>
                  <div class="chart-x-axis">
                    @for (label of getXAxisLabels(charts()!.revenue_trend); track label) {
                      <span>{{ label }}</span>
                    }
                  </div>
                } @else {
                  <div class="chart-empty">
                    <span class="material-symbols-outlined">show_chart</span>
                    <p>No data available</p>
                  </div>
                }
              </div>
            </div>
          </div>
        </section>

        <!-- Secondary Charts Row -->
        <section class="secondary-charts-section">
          <div class="secondary-charts-grid">
            <!-- Subscription Distribution -->
            <div class="chart-card compact">
              <div class="chart-header">
                <h3>Subscription Distribution</h3>
              </div>
              <div class="chart-body donut-container">
                @if (charts()?.subscription_distribution?.length) {
                  <div class="donut-chart">
                    <svg viewBox="0 0 200 200">
                      @for (segment of getDonutSegments(charts()!.subscription_distribution); track segment.label; let i = $index) {
                        <circle
                          cx="100" cy="100" r="70"
                          fill="none"
                          [attr.stroke]="segment.color"
                          stroke-width="30"
                          [attr.stroke-dasharray]="segment.dashArray"
                          [attr.stroke-dashoffset]="segment.dashOffset"
                          [attr.transform]="'rotate(-90 100 100)'"
                        />
                      }
                    </svg>
                    <div class="donut-center">
                      <span class="donut-total">{{ getTotalSubscriptions() | number }}</span>
                      <span class="donut-label">Total Users</span>
                    </div>
                  </div>
                  <div class="donut-legend">
                    @for (item of charts()!.subscription_distribution; track item.label) {
                      <div class="legend-item">
                        <span class="legend-color" [style.background-color]="getTierColor(item.label)"></span>
                        <span class="legend-label">{{ item.label }}</span>
                        <span class="legend-value">{{ item.value | number }}</span>
                      </div>
                    }
                  </div>
                } @else {
                  <div class="chart-empty">
                    <span class="material-symbols-outlined">donut_large</span>
                    <p>No data available</p>
                  </div>
                }
              </div>
            </div>

            <!-- Subject Popularity -->
            <div class="chart-card compact">
              <div class="chart-header">
                <h3>Subject Popularity</h3>
                <p class="chart-subtitle">Top subjects by question attempts (30 days)</p>
              </div>
              <div class="chart-body">
                @if (charts()?.subject_popularity?.length) {
                  <div class="bar-chart-horizontal">
                    @for (subject of charts()!.subject_popularity; track subject.label; let i = $index) {
                      <div class="bar-item">
                        <div class="bar-label">
                          <span class="bar-rank">{{ i + 1 }}</span>
                          <span class="bar-name">{{ subject.label }}</span>
                        </div>
                        <div class="bar-track">
                          <div class="bar-fill"
                               [style.width.%]="getBarWidth(subject.value, charts()!.subject_popularity)"
                               [style.background-color]="getSubjectColor(i)">
                          </div>
                          <span class="bar-value">{{ subject.value | number }}</span>
                        </div>
                      </div>
                    }
                  </div>
                } @else {
                  <div class="chart-empty">
                    <span class="material-symbols-outlined">bar_chart</span>
                    <p>No data available</p>
                  </div>
                }
              </div>
            </div>

            <!-- Activity Heatmap -->
            <div class="chart-card compact heatmap-card">
              <div class="chart-header">
                <h3>Activity Heatmap</h3>
                <p class="chart-subtitle">Question attempts by day and hour</p>
              </div>
              <div class="chart-body">
                @if (charts()?.active_hours_heatmap) {
                  <div class="heatmap">
                    <div class="heatmap-y-axis">
                      @for (day of heatmapDays; track day) {
                        <span>{{ day }}</span>
                      }
                    </div>
                    <div class="heatmap-grid">
                      @for (day of heatmapDays; track day) {
                        <div class="heatmap-row">
                          @for (hour of [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]; track hour) {
                            <div class="heatmap-cell"
                                 [style.background-color]="getHeatmapColor(charts()!.active_hours_heatmap[day]?.[hour] || 0)"
                                 [title]="day + ' ' + hour + ':00 - ' + (charts()!.active_hours_heatmap[day]?.[hour] || 0) + ' attempts'">
                            </div>
                          }
                        </div>
                      }
                    </div>
                    <div class="heatmap-x-axis">
                      <span>12am</span>
                      <span>6am</span>
                      <span>12pm</span>
                      <span>6pm</span>
                      <span>12am</span>
                    </div>
                    <div class="heatmap-legend">
                      <span>Less</span>
                      <div class="heatmap-scale">
                        @for (level of [0, 1, 2, 3, 4]; track level) {
                          <div class="scale-item" [style.background-color]="getHeatmapScaleColor(level)"></div>
                        }
                      </div>
                      <span>More</span>
                    </div>
                  </div>
                } @else {
                  <div class="chart-empty">
                    <span class="material-symbols-outlined">grid_on</span>
                    <p>No data available</p>
                  </div>
                }
              </div>
            </div>
          </div>
        </section>

        <!-- Bottom Row: Activity Feed & Quick Actions -->
        <section class="bottom-section">
          <div class="bottom-grid">
            <!-- Activity Feed -->
            <div class="card activity-card">
              <div class="card-header">
                <h3>
                  <span class="material-symbols-outlined">history</span>
                  Recent Activity
                </h3>
                <div class="card-actions">
                  @if (activity()) {
                    <span class="activity-count">
                      {{ activity()!.total_count | number }} total events
                    </span>
                  }
                  <button class="btn btn-ghost" routerLink="/system/audit">
                    View All
                    <span class="material-symbols-outlined">arrow_forward</span>
                  </button>
                </div>
              </div>
              <div class="activity-list">
                @for (item of activity()?.items; track item.id) {
                  <div class="activity-item">
                    <div class="activity-icon" [class]="getActivityClass(item.type)">
                      <span class="material-symbols-outlined">{{ getActivityIcon(item.type) }}</span>
                    </div>
                    <div class="activity-content">
                      <div class="activity-header">
                        <span class="activity-title">{{ item.title }}</span>
                        <span class="activity-type-badge" [class]="getActivityClass(item.type)">
                          {{ item.type }}
                        </span>
                      </div>
                      <p class="activity-desc">{{ item.description }}</p>
                      <div class="activity-meta">
                        @if (item.user_name) {
                          <span class="activity-user">
                            <span class="material-symbols-outlined">person</span>
                            {{ item.user_name }}
                          </span>
                        }
                        <span class="activity-time">{{ formatTimeAgo(item.timestamp) }}</span>
                      </div>
                    </div>
                  </div>
                } @empty {
                  <div class="empty-state">
                    <span class="material-symbols-outlined">inbox</span>
                    <p>No recent activity</p>
                  </div>
                }
              </div>
              @if (activity()?.has_more) {
                <div class="load-more">
                  <button class="btn btn-secondary btn-sm" (click)="loadMoreActivity()">
                    Load More
                  </button>
                </div>
              }
            </div>

            <!-- Quick Actions & System Status -->
            <div class="sidebar">
              <!-- Quick Actions -->
              <div class="card quick-actions">
                <h3>
                  <span class="material-symbols-outlined">bolt</span>
                  Quick Actions
                </h3>
                <div class="actions-grid">
                  <button class="action-btn" routerLink="/users">
                    <span class="material-symbols-outlined">person_add</span>
                    <span>Add User</span>
                  </button>
                  <button class="action-btn" routerLink="/content/questions">
                    <span class="material-symbols-outlined">quiz</span>
                    <span>Questions</span>
                  </button>
                  <button class="action-btn" routerLink="/content/subjects">
                    <span class="material-symbols-outlined">menu_book</span>
                    <span>Subjects</span>
                  </button>
                  <button class="action-btn alert" routerLink="/live/broadcasts">
                    <span class="material-symbols-outlined">campaign</span>
                    <span>Broadcast</span>
                  </button>
                </div>
              </div>

              <!-- Daily Active Users Sparkline -->
              <div class="card sparkline-card">
                <div class="sparkline-header">
                  <h3>Daily Active Users</h3>
                  <span class="sparkline-value">{{ getCurrentDAU() | number }}</span>
                </div>
                @if (charts()?.daily_active_users?.length) {
                  <svg class="sparkline" viewBox="0 0 200 50" preserveAspectRatio="none">
                    <path [attr.d]="getSparklinePath(charts()!.daily_active_users)" class="sparkline-line"/>
                  </svg>
                }
              </div>

              <!-- System Status Summary -->
              <div class="card system-summary">
                <h3>
                  <span class="material-symbols-outlined">monitor_heart</span>
                  Platform Summary
                </h3>
                <div class="summary-stats">
                  <div class="summary-item">
                    <span class="summary-label">Total Users</span>
                    <span class="summary-value">{{ stats()?.total_users?.value | number }}</span>
                  </div>
                  <div class="summary-item">
                    <span class="summary-label">Active Subscriptions</span>
                    <span class="summary-value">{{ stats()?.active_subscriptions?.value | number }}</span>
                  </div>
                  <div class="summary-item">
                    <span class="summary-label">Conversion Rate</span>
                    <span class="summary-value">{{ stats()?.conversion_rate?.value | number:'1.2-2' }}%</span>
                  </div>
                  <div class="summary-item">
                    <span class="summary-label">Avg Session</span>
                    <span class="summary-value">{{ stats()?.avg_session_duration?.value | number:'1.1-1' }} min</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      }
    </div>
  `,
  styles: [`
    /* ============================================================================
       Dashboard Layout
       ============================================================================ */
    .dashboard {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .last-updated {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      font-size: 0.75rem;
      color: var(--text-muted);
      padding-right: 0.75rem;
      border-right: 1px solid var(--border);

      .material-symbols-outlined {
        font-size: 1rem;
      }
    }

    .time-range-select {
      padding: 0.5rem 0.75rem;
      font-size: 0.875rem;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      background-color: var(--surface);
      color: var(--text-primary);
      cursor: pointer;

      &:focus {
        outline: none;
        border-color: var(--primary);
      }
    }

    .spinning {
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    .section-title {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 1rem;
    }

    /* ============================================================================
       Error State
       ============================================================================ */
    .error-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      text-align: center;

      .material-symbols-outlined {
        font-size: 3rem;
        color: var(--error);
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

    /* ============================================================================
       KPI Cards
       ============================================================================ */
    .kpi-section {
      margin-bottom: 0.5rem;
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;

      @media (max-width: 1400px) {
        grid-template-columns: repeat(2, 1fr);
      }

      @media (max-width: 768px) {
        grid-template-columns: 1fr;
      }
    }

    .kpi-card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.25rem;
      transition: all 0.2s ease;
      position: relative;
      overflow: hidden;

      &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--primary);
      }

      &:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
      }

      &.revenue::before { background: #10b981; }
      &.users::before { background: #3b82f6; }
      &.engagement::before { background: #8b5cf6; }
      &.conversion::before { background: #f59e0b; }
    }

    .kpi-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
    }

    .kpi-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 0.5rem;
      background-color: rgba(0, 102, 70, 0.1);

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: var(--primary);
      }
    }

    .kpi-trend {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.25rem 0.5rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;

      &.up {
        background-color: rgba(16, 185, 129, 0.1);
        color: #10b981;
      }

      &.down {
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }

      &.stable {
        background-color: rgba(107, 114, 128, 0.1);
        color: #6b7280;
      }

      .material-symbols-outlined {
        font-size: 0.875rem;
      }
    }

    .kpi-body {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .kpi-value {
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--text-primary);
      font-feature-settings: 'tnum';
      line-height: 1.2;
    }

    .kpi-label {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-secondary);
    }

    .kpi-footer {
      margin-top: 0.75rem;
      padding-top: 0.75rem;
      border-top: 1px solid var(--border);
    }

    .kpi-period {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    /* ============================================================================
       Charts Section
       ============================================================================ */
    .charts-section, .secondary-charts-section {
      margin-bottom: 0.5rem;
    }

    .charts-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1.5rem;

      @media (max-width: 1200px) {
        grid-template-columns: 1fr;
      }
    }

    .secondary-charts-grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1.5fr;
      gap: 1.5rem;

      @media (max-width: 1400px) {
        grid-template-columns: repeat(2, 1fr);
      }

      @media (max-width: 900px) {
        grid-template-columns: 1fr;
      }
    }

    .chart-card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.5rem;

      &.compact {
        padding: 1.25rem;
      }
    }

    .chart-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1.5rem;

      h3 {
        font-size: 1rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
      }
    }

    .chart-subtitle {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .chart-value-highlight {
      text-align: right;
      padding: 0.5rem 0.75rem;
      background-color: rgba(0, 102, 70, 0.05);
      border-radius: 0.5rem;

      &.revenue {
        background-color: rgba(16, 185, 129, 0.05);
      }
    }

    .highlight-value {
      display: block;
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--primary);
      font-feature-settings: 'tnum';
    }

    .chart-value-highlight.revenue .highlight-value {
      color: #10b981;
    }

    .highlight-label {
      font-size: 0.675rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .chart-body {
      position: relative;
    }

    .line-chart {
      width: 100%;
      height: 200px;
      display: block;
    }

    .grid-lines line {
      stroke: var(--border);
      stroke-dasharray: 4 4;
      stroke-width: 1;
    }

    .chart-line {
      fill: none;
      stroke-width: 2.5;
      stroke-linecap: round;
      stroke-linejoin: round;

      &.primary { stroke: var(--primary); }
      &.success { stroke: #10b981; }
    }

    .chart-point {
      fill: var(--surface);
      stroke-width: 2;

      &.primary { stroke: var(--primary); }
      &.success { stroke: #10b981; }
    }

    .chart-x-axis {
      display: flex;
      justify-content: space-between;
      margin-top: 0.75rem;
      font-size: 0.675rem;
      color: var(--text-muted);
      font-family: monospace;
    }

    .chart-empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 200px;
      color: var(--text-muted);

      .material-symbols-outlined {
        font-size: 2rem;
        margin-bottom: 0.5rem;
        opacity: 0.5;
      }

      p {
        font-size: 0.875rem;
      }
    }

    /* ============================================================================
       Donut Chart
       ============================================================================ */
    .donut-container {
      display: flex;
      align-items: center;
      gap: 1.5rem;

      @media (max-width: 500px) {
        flex-direction: column;
      }
    }

    .donut-chart {
      position: relative;
      width: 160px;
      height: 160px;
      flex-shrink: 0;

      svg {
        width: 100%;
        height: 100%;
      }
    }

    .donut-center {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
    }

    .donut-total {
      display: block;
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text-primary);
      font-feature-settings: 'tnum';
    }

    .donut-label {
      font-size: 0.675rem;
      color: var(--text-muted);
    }

    .donut-legend {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.625rem;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .legend-color {
      width: 12px;
      height: 12px;
      border-radius: 3px;
      flex-shrink: 0;
    }

    .legend-label {
      flex: 1;
      font-size: 0.8125rem;
      color: var(--text-secondary);
    }

    .legend-value {
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--text-primary);
      font-feature-settings: 'tnum';
    }

    /* ============================================================================
       Bar Chart
       ============================================================================ */
    .bar-chart-horizontal {
      display: flex;
      flex-direction: column;
      gap: 0.625rem;
    }

    .bar-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .bar-label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .bar-rank {
      width: 18px;
      height: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--background);
      border-radius: 4px;
      font-size: 0.625rem;
      font-weight: 600;
      color: var(--text-muted);
    }

    .bar-name {
      font-size: 0.8125rem;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .bar-track {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      height: 20px;
      background-color: var(--background);
      border-radius: 4px;
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      min-width: 2px;
      border-radius: 4px;
      transition: width 0.5s ease;
    }

    .bar-value {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-secondary);
      padding-right: 0.5rem;
      font-feature-settings: 'tnum';
    }

    /* ============================================================================
       Heatmap
       ============================================================================ */
    .heatmap-card {
      @media (max-width: 1400px) {
        grid-column: span 2;
      }

      @media (max-width: 900px) {
        grid-column: span 1;
      }
    }

    .heatmap {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .heatmap-y-axis {
      display: flex;
      flex-direction: column;
      position: absolute;
      left: 0;
      gap: 2px;

      span {
        height: 14px;
        font-size: 0.625rem;
        color: var(--text-muted);
        display: flex;
        align-items: center;
      }
    }

    .heatmap-grid {
      display: flex;
      flex-direction: column;
      gap: 2px;
      margin-left: 2rem;
    }

    .heatmap-row {
      display: flex;
      gap: 2px;
    }

    .heatmap-cell {
      width: 14px;
      height: 14px;
      border-radius: 2px;
      background-color: var(--background);
      cursor: pointer;
      transition: transform 0.1s ease;

      &:hover {
        transform: scale(1.2);
        z-index: 1;
      }
    }

    .heatmap-x-axis {
      display: flex;
      justify-content: space-between;
      margin-left: 2rem;
      margin-top: 0.25rem;
      font-size: 0.625rem;
      color: var(--text-muted);
    }

    .heatmap-legend {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 0.5rem;
      margin-top: 0.5rem;
      font-size: 0.625rem;
      color: var(--text-muted);
    }

    .heatmap-scale {
      display: flex;
      gap: 2px;
    }

    .scale-item {
      width: 12px;
      height: 12px;
      border-radius: 2px;
    }

    /* ============================================================================
       Bottom Section
       ============================================================================ */
    .bottom-section {
      margin-top: 0.5rem;
    }

    .bottom-grid {
      display: grid;
      grid-template-columns: 1fr 360px;
      gap: 1.5rem;

      @media (max-width: 1200px) {
        grid-template-columns: 1fr;
      }
    }

    .card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.25rem;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;

      h3 {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1rem;
        font-weight: 700;
        color: var(--text-primary);

        .material-symbols-outlined {
          font-size: 1.25rem;
          color: var(--primary);
        }
      }
    }

    .card-actions {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .activity-count {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    /* ============================================================================
       Activity Feed
       ============================================================================ */
    .activity-card {
      max-height: 500px;
      display: flex;
      flex-direction: column;
    }

    .activity-list {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }

    .activity-item {
      display: flex;
      gap: 1rem;
      padding: 1rem 0;
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
      }

      &.registration {
        background-color: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }

      &.upgrade {
        background-color: rgba(16, 185, 129, 0.1);
        color: #10b981;
      }

      &.competition {
        background-color: rgba(139, 92, 246, 0.1);
        color: #8b5cf6;
      }

      &.ticket {
        background-color: rgba(245, 158, 11, 0.1);
        color: #f59e0b;
      }

      &.alert {
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }
    }

    .activity-content {
      flex: 1;
      min-width: 0;
    }

    .activity-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.25rem;
    }

    .activity-title {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--text-primary);
    }

    .activity-type-badge {
      padding: 0.125rem 0.5rem;
      border-radius: 9999px;
      font-size: 0.625rem;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.05em;

      &.registration {
        background-color: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }

      &.upgrade {
        background-color: rgba(16, 185, 129, 0.1);
        color: #10b981;
      }

      &.competition {
        background-color: rgba(139, 92, 246, 0.1);
        color: #8b5cf6;
      }

      &.ticket {
        background-color: rgba(245, 158, 11, 0.1);
        color: #f59e0b;
      }

      &.alert {
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }
    }

    .activity-desc {
      font-size: 0.8125rem;
      color: var(--text-secondary);
      margin-bottom: 0.375rem;
    }

    .activity-meta {
      display: flex;
      align-items: center;
      gap: 1rem;
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .activity-user {
      display: flex;
      align-items: center;
      gap: 0.25rem;

      .material-symbols-outlined {
        font-size: 0.875rem;
      }
    }

    .load-more {
      padding-top: 1rem;
      border-top: 1px solid var(--border);
      text-align: center;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem;
      color: var(--text-muted);

      .material-symbols-outlined {
        font-size: 2rem;
        margin-bottom: 0.5rem;
        opacity: 0.5;
      }
    }

    /* ============================================================================
       Sidebar
       ============================================================================ */
    .sidebar {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .quick-actions h3 {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1rem;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 1rem;

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: var(--primary);
      }
    }

    .actions-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 0.75rem;
    }

    .action-btn {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
      padding: 1rem;
      background-color: var(--background);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      cursor: pointer;
      transition: all 0.15s ease;
      font-family: inherit;
      color: var(--text-primary);
      font-size: 0.8125rem;
      font-weight: 500;

      .material-symbols-outlined {
        font-size: 1.5rem;
        color: var(--primary);
      }

      &:hover {
        border-color: var(--primary);
        background-color: rgba(0, 102, 70, 0.05);
      }

      &.alert {
        .material-symbols-outlined {
          color: var(--error);
        }

        &:hover {
          border-color: var(--error);
          background-color: rgba(239, 68, 68, 0.05);
        }
      }
    }

    /* ============================================================================
       Sparkline Card
       ============================================================================ */
    .sparkline-card {
      padding: 1rem 1.25rem;
    }

    .sparkline-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.5rem;

      h3 {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-secondary);
      }
    }

    .sparkline-value {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--text-primary);
      font-feature-settings: 'tnum';
    }

    .sparkline {
      width: 100%;
      height: 40px;
    }

    .sparkline-line {
      fill: none;
      stroke: var(--primary);
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    /* ============================================================================
       System Summary
       ============================================================================ */
    .system-summary h3 {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1rem;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 1rem;

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: var(--primary);
      }
    }

    .summary-stats {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }

    .summary-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .summary-label {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .summary-value {
      font-size: 1rem;
      font-weight: 600;
      color: var(--text-primary);
      font-feature-settings: 'tnum';
    }

    /* ============================================================================
       Button Styles
       ============================================================================ */
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
      border: none;
      font-family: inherit;

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      .material-symbols-outlined {
        font-size: 1.125rem;
      }
    }

    .btn-primary {
      background-color: var(--primary);
      color: white;

      &:hover:not(:disabled) {
        background-color: var(--primary-hover);
      }
    }

    .btn-secondary {
      background-color: var(--background);
      color: var(--text-primary);
      border: 1px solid var(--border);

      &:hover:not(:disabled) {
        background-color: var(--surface);
        border-color: var(--primary);
      }
    }

    .btn-ghost {
      background: none;
      color: var(--text-secondary);
      padding: 0.375rem 0.75rem;

      &:hover {
        color: var(--primary);
      }
    }

    .btn-sm {
      padding: 0.375rem 0.75rem;
      font-size: 0.8125rem;
    }
  `]
})
export class DashboardComponent implements OnInit, OnDestroy {
  private adminService = inject(AdminService);
  private destroy$ = new Subject<void>();

  // State
  loading = signal(false);
  error = signal<string | null>(null);
  stats = signal<DashboardStats | null>(null);
  charts = signal<DashboardCharts | null>(null);
  activity = signal<DashboardActivity | null>(null);
  lastUpdated = signal<string | null>(null);
  selectedDays = 30;

  // Constants
  heatmapDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  tierColors: Record<string, string> = {
    'FREE': '#94a3b8',
    'BASIC': '#3b82f6',
    'PREMIUM': '#8b5cf6',
    'FAMILY': '#f59e0b',
    'SCHOOL': '#10b981'
  };

  // Computed KPI cards configuration
  kpiCards = computed(() => {
    const s = this.stats();
    if (!s) return [];

    return [
      { key: 'total_users', data: s.total_users, icon: 'group', colorClass: 'users' },
      { key: 'active_students', data: s.active_students_today, icon: 'school', colorClass: 'engagement' },
      { key: 'questions', data: s.questions_answered_today, icon: 'quiz', colorClass: 'engagement' },
      { key: 'messages', data: s.messages_24h, icon: 'chat', colorClass: 'engagement' },
      { key: 'revenue', data: s.revenue_this_month, icon: 'payments', colorClass: 'revenue' },
      { key: 'subscriptions', data: s.active_subscriptions, icon: 'card_membership', colorClass: 'revenue' },
      { key: 'conversion', data: s.conversion_rate, icon: 'trending_up', colorClass: 'conversion' },
      { key: 'session', data: s.avg_session_duration, icon: 'timer', colorClass: 'engagement' },
    ];
  });

  ngOnInit(): void {
    this.loadDashboard();

    // Auto-refresh every 5 minutes
    interval(5 * 60 * 1000)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.refreshData());
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadDashboard(): void {
    this.loading.set(true);
    this.error.set(null);

    forkJoin({
      stats: this.adminService.getDashboardStats(),
      charts: this.adminService.getDashboardCharts(this.selectedDays),
      activity: this.adminService.getDashboardActivity(20)
    }).subscribe({
      next: (data) => {
        this.stats.set(data.stats);
        this.charts.set(data.charts);
        this.activity.set(data.activity);
        this.lastUpdated.set(new Date().toISOString());
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load dashboard:', err);
        this.error.set(err.message || 'Failed to load dashboard data');
        this.loading.set(false);
      }
    });
  }

  refreshData(): void {
    this.loadDashboard();
  }

  onDaysChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    this.selectedDays = parseInt(select.value, 10);
    this.loadDashboard();
  }

  loadMoreActivity(): void {
    const current = this.activity();
    if (!current) return;

    this.adminService.getDashboardActivity(20, current.items.length).subscribe({
      next: (data) => {
        this.activity.set({
          items: [...current.items, ...data.items],
          total_count: data.total_count,
          has_more: data.has_more
        });
      }
    });
  }

  exportReport(): void {
    // TODO: Implement report export
    console.log('Export report clicked');
  }

  // ============================================================================
  // Formatting Helpers
  // ============================================================================
  formatKpiValue(value: number | string): string {
    if (typeof value === 'string') return value;
    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
    if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
    return value.toLocaleString();
  }

  formatTimeAgo(timestamp: string): string {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  }

  // ============================================================================
  // Chart Helpers
  // ============================================================================
  getLinePath(data: TimeSeriesPoint[], width: number, height: number): string {
    if (!data?.length) return '';
    const maxVal = Math.max(...data.map(d => d.value), 1);
    const points = data.map((d, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - (d.value / maxVal) * (height - 20) - 10;
      return `${x},${y}`;
    });
    return `M${points.join(' L')}`;
  }

  getAreaPath(data: TimeSeriesPoint[], width: number, height: number): string {
    if (!data?.length) return '';
    const linePath = this.getLinePath(data, width, height);
    return `${linePath} L${width},${height} L0,${height} Z`;
  }

  getChartPoints(data: TimeSeriesPoint[], width: number, height: number): { x: number; y: number }[] {
    if (!data?.length) return [];
    const maxVal = Math.max(...data.map(d => d.value), 1);
    // Only show every nth point to avoid clutter
    const step = Math.max(1, Math.floor(data.length / 10));
    return data
      .filter((_, i) => i % step === 0 || i === data.length - 1)
      .map((d, i, filtered) => {
        const originalIndex = data.indexOf(d);
        const x = (originalIndex / (data.length - 1)) * width;
        const y = height - (d.value / maxVal) * (height - 20) - 10;
        return { x, y };
      });
  }

  getXAxisLabels(data: TimeSeriesPoint[]): string[] {
    if (!data?.length) return [];
    const step = Math.max(1, Math.floor(data.length / 6));
    return data
      .filter((_, i) => i % step === 0 || i === data.length - 1)
      .map(d => {
        const date = new Date(d.timestamp);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      });
  }

  getTotalFromSeries(data: TimeSeriesPoint[] | undefined): number {
    return data?.reduce((sum, d) => sum + d.value, 0) || 0;
  }

  // ============================================================================
  // Donut Chart Helpers
  // ============================================================================
  getDonutSegments(data: ChartDataPoint[]): { label: string; color: string; dashArray: string; dashOffset: number }[] {
    const total = data.reduce((sum, d) => sum + d.value, 0);
    const circumference = 2 * Math.PI * 70; // r=70
    let offset = 0;

    return data.map(item => {
      const percentage = item.value / total;
      const length = percentage * circumference;
      const segment = {
        label: item.label,
        color: this.getTierColor(item.label),
        dashArray: `${length} ${circumference - length}`,
        dashOffset: -offset
      };
      offset += length;
      return segment;
    });
  }

  getTotalSubscriptions(): number {
    return this.charts()?.subscription_distribution?.reduce((sum, d) => sum + d.value, 0) || 0;
  }

  getTierColor(tier: string): string {
    return this.tierColors[tier] || '#94a3b8';
  }

  // ============================================================================
  // Bar Chart Helpers
  // ============================================================================
  getBarWidth(value: number, data: ChartDataPoint[]): number {
    const max = Math.max(...data.map(d => d.value), 1);
    return (value / max) * 100;
  }

  getSubjectColor(index: number): string {
    const colors = ['#006646', '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899', '#06b6d4', '#84cc16', '#f97316'];
    return colors[index % colors.length];
  }

  // ============================================================================
  // Heatmap Helpers
  // ============================================================================
  getHeatmapColor(value: number): string {
    if (!value) return 'var(--background)';
    const maxVal = this.getHeatmapMax();
    const intensity = Math.min(value / maxVal, 1);
    if (intensity < 0.25) return 'rgba(0, 102, 70, 0.2)';
    if (intensity < 0.5) return 'rgba(0, 102, 70, 0.4)';
    if (intensity < 0.75) return 'rgba(0, 102, 70, 0.6)';
    return 'rgba(0, 102, 70, 0.9)';
  }

  getHeatmapScaleColor(level: number): string {
    const colors = ['var(--background)', 'rgba(0, 102, 70, 0.2)', 'rgba(0, 102, 70, 0.4)', 'rgba(0, 102, 70, 0.6)', 'rgba(0, 102, 70, 0.9)'];
    return colors[level];
  }

  getHeatmapMax(): number {
    const heatmap = this.charts()?.active_hours_heatmap;
    if (!heatmap) return 1;
    let max = 0;
    Object.values(heatmap).forEach(hours => {
      hours.forEach(val => {
        if (val > max) max = val;
      });
    });
    return max || 1;
  }

  // ============================================================================
  // Sparkline Helpers
  // ============================================================================
  getSparklinePath(data: TimeSeriesPoint[]): string {
    if (!data?.length) return '';
    const maxVal = Math.max(...data.map(d => d.value), 1);
    const points = data.map((d, i) => {
      const x = (i / (data.length - 1)) * 200;
      const y = 50 - (d.value / maxVal) * 45;
      return `${x},${y}`;
    });
    return `M${points.join(' L')}`;
  }

  getCurrentDAU(): number {
    const data = this.charts()?.daily_active_users;
    if (!data?.length) return 0;
    return data[data.length - 1]?.value || 0;
  }

  // ============================================================================
  // Activity Feed Helpers
  // ============================================================================
  getActivityIcon(type: ActivityType | string): string {
    const icons: Record<string, string> = {
      'registration': 'person_add',
      'upgrade': 'upgrade',
      'competition': 'emoji_events',
      'ticket': 'support_agent',
      'alert': 'warning'
    };
    return icons[type] || 'info';
  }

  getActivityClass(type: ActivityType | string): string {
    return type.toString().toLowerCase();
  }
}
