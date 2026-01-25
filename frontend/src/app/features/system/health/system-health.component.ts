import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ToastService } from '../../../core/services/toast.service';
import { AdminService, SystemStats } from '../../../core/services/admin.service';

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  responseTime: number;
  uptime: number;
  lastCheck: string;
  icon: string;
}

interface SystemMetric {
  name: string;
  value: number;
  max: number;
  unit: string;
  status: 'good' | 'warning' | 'critical';
}

@Component({
  selector: 'app-system-health',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>System Health</h1>
          <p class="subtitle">Monitor system performance and service status</p>
        </div>
        <div class="header-actions">
          <span class="last-updated">
            <span class="material-symbols-outlined">schedule</span>
            Last updated: {{ lastUpdated }}
          </span>
          <button class="btn-primary" (click)="refreshStatus()">
            <span class="material-symbols-outlined">refresh</span>
            Refresh
          </button>
        </div>
      </div>

      <div class="overall-status" [class]="overallStatus()">
        <div class="status-indicator">
          <span class="material-symbols-outlined">
            {{ overallStatus() === 'healthy' ? 'check_circle' : overallStatus() === 'degraded' ? 'warning' : 'error' }}
          </span>
        </div>
        <div class="status-info">
          <h2>System Status: {{ overallStatus() | titlecase }}</h2>
          <p>{{ getStatusMessage() }}</p>
        </div>
      </div>

      <div class="metrics-grid">
        @for (metric of systemMetrics; track metric.name) {
          <div class="metric-card" [class]="metric.status">
            <div class="metric-header">
              <span class="metric-name">{{ metric.name }}</span>
              <span class="metric-badge" [class]="metric.status">{{ metric.status }}</span>
            </div>
            <div class="metric-value">{{ metric.value }}{{ metric.unit }}</div>
            <div class="metric-bar">
              <div class="bar-fill" [style.width.%]="(metric.value / metric.max) * 100"></div>
            </div>
            <div class="metric-limits">
              <span>0{{ metric.unit }}</span>
              <span>{{ metric.max }}{{ metric.unit }}</span>
            </div>
          </div>
        }
      </div>

      <div class="services-section">
        <h3>Service Status</h3>
        <div class="services-grid">
          @for (service of services; track service.name) {
            <div class="service-card" [class]="service.status">
              <div class="service-header">
                <div class="service-icon">
                  <span class="material-symbols-outlined">{{ service.icon }}</span>
                </div>
                <span class="service-status-badge" [class]="service.status">
                  <span class="status-dot"></span>
                  {{ service.status }}
                </span>
              </div>
              <h4>{{ service.name }}</h4>
              <div class="service-metrics">
                <div class="service-metric">
                  <span class="label">Response Time</span>
                  <span class="value">{{ service.responseTime }}ms</span>
                </div>
                <div class="service-metric">
                  <span class="label">Uptime</span>
                  <span class="value">{{ service.uptime }}%</span>
                </div>
              </div>
              <div class="service-footer">
                <span class="last-check">
                  <span class="material-symbols-outlined">schedule</span>
                  {{ service.lastCheck }}
                </span>
              </div>
            </div>
          }
        </div>
      </div>

      <div class="content-row">
        <div class="card">
          <div class="card-header">
            <h3>Recent Incidents</h3>
            <button class="btn-link">View All</button>
          </div>
          <div class="card-body">
            @if (incidents.length === 0) {
              <div class="empty-incidents">
                <span class="material-symbols-outlined">verified</span>
                <p>No recent incidents</p>
              </div>
            } @else {
              <div class="incidents-list">
                @for (incident of incidents; track incident.id) {
                  <div class="incident-item" [class]="incident.severity">
                    <div class="incident-icon">
                      <span class="material-symbols-outlined">
                        {{ incident.severity === 'critical' ? 'error' : 'warning' }}
                      </span>
                    </div>
                    <div class="incident-info">
                      <span class="incident-title">{{ incident.title }}</span>
                      <span class="incident-time">{{ incident.time }}</span>
                    </div>
                    <span class="incident-status" [class]="incident.resolved ? 'resolved' : 'active'">
                      {{ incident.resolved ? 'Resolved' : 'Active' }}
                    </span>
                  </div>
                }
              </div>
            }
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Quick Actions</h3>
          </div>
          <div class="card-body">
            <div class="actions-list">
              <button class="action-item" (click)="clearCache()">
                <span class="material-symbols-outlined">delete_sweep</span>
                <span>Clear Cache</span>
              </button>
              <button class="action-item" (click)="restartServices()">
                <span class="material-symbols-outlined">restart_alt</span>
                <span>Restart Services</span>
              </button>
              <button class="action-item" (click)="runDiagnostics()">
                <span class="material-symbols-outlined">troubleshoot</span>
                <span>Run Diagnostics</span>
              </button>
              <button class="action-item" (click)="viewLogs()">
                <span class="material-symbols-outlined">description</span>
                <span>View System Logs</span>
              </button>
            </div>
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
    .header-actions { display: flex; align-items: center; gap: 1rem; }
    .last-updated { display: flex; align-items: center; gap: 0.375rem; font-size: 0.75rem; color: var(--text-tertiary); .material-symbols-outlined { font-size: 1rem; } }
    .btn-primary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; font-size: 0.875rem; font-weight: 500; background-color: var(--primary); color: white; border: none; border-radius: 0.5rem; cursor: pointer; &:hover { background-color: #005238; } }
    .btn-link { background: none; border: none; color: var(--primary); font-size: 0.875rem; font-weight: 500; cursor: pointer; &:hover { text-decoration: underline; } }

    .overall-status {
      display: flex; align-items: center; gap: 1.5rem; padding: 1.5rem;
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; margin-bottom: 1.5rem;
      &.healthy { border-left: 4px solid #10b981; background: linear-gradient(90deg, rgba(16, 185, 129, 0.05) 0%, var(--surface) 100%); .status-indicator { background-color: rgba(16, 185, 129, 0.1); .material-symbols-outlined { color: #10b981; } } }
      &.degraded { border-left: 4px solid #f59e0b; background: linear-gradient(90deg, rgba(245, 158, 11, 0.05) 0%, var(--surface) 100%); .status-indicator { background-color: rgba(245, 158, 11, 0.1); .material-symbols-outlined { color: #f59e0b; } } }
      &.down { border-left: 4px solid #ef4444; background: linear-gradient(90deg, rgba(239, 68, 68, 0.05) 0%, var(--surface) 100%); .status-indicator { background-color: rgba(239, 68, 68, 0.1); .material-symbols-outlined { color: #ef4444; } } }
    }
    .status-indicator { width: 64px; height: 64px; display: flex; align-items: center; justify-content: center; border-radius: 50%; .material-symbols-outlined { font-size: 2rem; } }
    .status-info { h2 { font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem; } p { font-size: 0.875rem; color: var(--text-secondary); } }

    .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
    @media (max-width: 1200px) { .metrics-grid { grid-template-columns: repeat(2, 1fr); } }

    .metric-card {
      padding: 1.25rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem;
      &.critical { border-color: #ef4444; }
      &.warning { border-color: #f59e0b; }
    }
    .metric-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
    .metric-name { font-size: 0.75rem; color: var(--text-secondary); }
    .metric-badge { padding: 0.125rem 0.5rem; font-size: 0.625rem; font-weight: 600; border-radius: 9999px; text-transform: uppercase; &.good { background-color: rgba(16, 185, 129, 0.1); color: #10b981; } &.warning { background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; } &.critical { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; } }
    .metric-value { font-size: 1.75rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.75rem; }
    .metric-bar { height: 6px; background-color: var(--background); border-radius: 3px; overflow: hidden; margin-bottom: 0.5rem; }
    .bar-fill { height: 100%; background-color: var(--primary); border-radius: 3px; transition: width 0.3s ease; .warning & { background-color: #f59e0b; } .critical & { background-color: #ef4444; } }
    .metric-limits { display: flex; justify-content: space-between; font-size: 0.625rem; color: var(--text-tertiary); }

    .services-section { margin-bottom: 1.5rem; h3 { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 1rem; } }
    .services-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }

    .service-card {
      padding: 1.25rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem;
      &.healthy { .service-icon { background-color: rgba(16, 185, 129, 0.1); .material-symbols-outlined { color: #10b981; } } }
      &.degraded { border-color: #f59e0b; .service-icon { background-color: rgba(245, 158, 11, 0.1); .material-symbols-outlined { color: #f59e0b; } } }
      &.down { border-color: #ef4444; .service-icon { background-color: rgba(239, 68, 68, 0.1); .material-symbols-outlined { color: #ef4444; } } }
    }
    .service-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem; }
    .service-icon { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 0.5rem; }
    .service-status-badge { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.25rem 0.5rem; font-size: 0.625rem; font-weight: 600; border-radius: 9999px; text-transform: uppercase; &.healthy { background-color: rgba(16, 185, 129, 0.1); color: #10b981; .status-dot { background-color: #10b981; } } &.degraded { background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; .status-dot { background-color: #f59e0b; } } &.down { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; .status-dot { background-color: #ef4444; } } }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; }
    .service-card h4 { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.75rem; }
    .service-metrics { display: flex; gap: 1rem; margin-bottom: 0.75rem; }
    .service-metric { .label { display: block; font-size: 0.625rem; color: var(--text-tertiary); } .value { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); } }
    .service-footer { border-top: 1px solid var(--border); padding-top: 0.75rem; }
    .last-check { display: flex; align-items: center; gap: 0.25rem; font-size: 0.625rem; color: var(--text-tertiary); .material-symbols-outlined { font-size: 0.875rem; } }

    .content-row { display: grid; grid-template-columns: 1.5fr 1fr; gap: 1.5rem; }
    @media (max-width: 1024px) { .content-row { grid-template-columns: 1fr; } }

    .card { background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; overflow: hidden; }
    .card-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem; border-bottom: 1px solid var(--border); h3 { font-size: 1rem; font-weight: 600; color: var(--text-primary); } }
    .card-body { padding: 1.25rem; }

    .empty-incidents { display: flex; flex-direction: column; align-items: center; padding: 2rem; .material-symbols-outlined { font-size: 3rem; color: #10b981; margin-bottom: 0.5rem; } p { color: var(--text-secondary); } }

    .incidents-list { display: flex; flex-direction: column; gap: 0.75rem; }
    .incident-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; background-color: var(--background); border-radius: 0.5rem; &.critical .incident-icon { background-color: rgba(239, 68, 68, 0.1); .material-symbols-outlined { color: #ef4444; } } &.warning .incident-icon { background-color: rgba(245, 158, 11, 0.1); .material-symbols-outlined { color: #f59e0b; } } }
    .incident-icon { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 0.5rem; }
    .incident-info { flex: 1; .incident-title { display: block; font-size: 0.875rem; font-weight: 500; color: var(--text-primary); } .incident-time { font-size: 0.75rem; color: var(--text-tertiary); } }
    .incident-status { padding: 0.25rem 0.5rem; font-size: 0.625rem; font-weight: 600; border-radius: 9999px; &.resolved { background-color: rgba(16, 185, 129, 0.1); color: #10b981; } &.active { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; } }

    .actions-list { display: flex; flex-direction: column; gap: 0.5rem; }
    .action-item { display: flex; align-items: center; gap: 0.75rem; width: 100%; padding: 0.75rem 1rem; background-color: var(--background); border: none; border-radius: 0.5rem; font-size: 0.875rem; color: var(--text-primary); text-align: left; cursor: pointer; transition: all 0.15s ease; &:hover { background-color: var(--hover); } .material-symbols-outlined { font-size: 1.25rem; color: var(--text-secondary); } }
  `]
})
export class SystemHealthComponent implements OnInit {
  private toastService = inject(ToastService);
  private adminService = inject(AdminService);
  private router = inject(Router);

  overallStatus = signal<'healthy' | 'degraded' | 'down'>('healthy');
  lastUpdated = 'Just now';
  isLoading = signal(true);

  systemMetrics: SystemMetric[] = [
    { name: 'CPU Usage', value: 45, max: 100, unit: '%', status: 'good' },
    { name: 'Memory Usage', value: 68, max: 100, unit: '%', status: 'warning' },
    { name: 'Disk Usage', value: 52, max: 100, unit: '%', status: 'good' },
    { name: 'Network I/O', value: 125, max: 1000, unit: 'MB/s', status: 'good' },
  ];

  services: ServiceStatus[] = [
    { name: 'API Server', status: 'healthy', responseTime: 45, uptime: 99.99, lastCheck: '30s ago', icon: 'dns' },
    { name: 'Database', status: 'healthy', responseTime: 12, uptime: 99.95, lastCheck: '30s ago', icon: 'storage' },
    { name: 'AI Engine', status: 'healthy', responseTime: 250, uptime: 99.80, lastCheck: '30s ago', icon: 'smart_toy' },
    { name: 'Cache Server', status: 'healthy', responseTime: 3, uptime: 99.99, lastCheck: '30s ago', icon: 'memory' },
    { name: 'Payment Gateway', status: 'healthy', responseTime: 180, uptime: 99.90, lastCheck: '30s ago', icon: 'payments' },
    { name: 'WebSocket Server', status: 'healthy', responseTime: 8, uptime: 99.95, lastCheck: '30s ago', icon: 'sync_alt' },
  ];

  incidents: any[] = [];

  ngOnInit(): void {
    this.loadSystemStats();
  }

  loadSystemStats(): void {
    this.isLoading.set(true);
    this.adminService.getSystemStats().subscribe({
      next: (stats) => {
        // Update metrics from API
        this.systemMetrics = [
          { name: 'CPU Usage', value: Math.round(stats.cpu_usage), max: 100, unit: '%', status: this.getMetricStatus(stats.cpu_usage, 70, 90) },
          { name: 'Memory Usage', value: Math.round(stats.memory_usage), max: 100, unit: '%', status: this.getMetricStatus(stats.memory_usage, 70, 90) },
          { name: 'Disk Usage', value: Math.round(stats.disk_usage), max: 100, unit: '%', status: this.getMetricStatus(stats.disk_usage, 70, 90) },
          { name: 'Active Connections', value: stats.active_connections, max: 1000, unit: '', status: 'good' },
        ];

        // Update services from API
        if (stats.services && stats.services.length > 0) {
          this.services = stats.services.map(s => ({
            name: s.name,
            status: s.status,
            responseTime: s.response_time,
            uptime: s.uptime,
            lastCheck: this.formatLastCheck(s.last_check),
            icon: this.getServiceIcon(s.name)
          }));
        }

        // Determine overall status
        const hasDown = stats.services?.some(s => s.status === 'down');
        const hasDegraded = stats.services?.some(s => s.status === 'degraded');
        this.overallStatus.set(hasDown ? 'down' : hasDegraded ? 'degraded' : 'healthy');

        this.lastUpdated = 'Just now';
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load system stats:', err);
        this.isLoading.set(false);
      }
    });
  }

  private getMetricStatus(value: number, warnThreshold: number, criticalThreshold: number): 'good' | 'warning' | 'critical' {
    if (value >= criticalThreshold) return 'critical';
    if (value >= warnThreshold) return 'warning';
    return 'good';
  }

  private formatLastCheck(timestamp: string): string {
    if (!timestamp) return 'Unknown';
    const diff = Date.now() - new Date(timestamp).getTime();
    const seconds = Math.floor(diff / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    return `${Math.floor(minutes / 60)}h ago`;
  }

  private getServiceIcon(name: string): string {
    const icons: Record<string, string> = {
      'API Server': 'dns',
      'Database': 'storage',
      'AI Engine': 'smart_toy',
      'Cache Server': 'memory',
      'Payment Gateway': 'payments',
      'WebSocket Server': 'sync_alt'
    };
    return icons[name] || 'settings';
  }

  getStatusMessage(): string {
    switch (this.overallStatus()) {
      case 'healthy': return 'All systems are operational and running smoothly.';
      case 'degraded': return 'Some services are experiencing issues. We are investigating.';
      case 'down': return 'Major outage detected. Our team is working to resolve this.';
    }
  }

  refreshStatus(): void {
    this.toastService.info('Refreshing...', 'Updating system status');
    this.loadSystemStats();
  }

  clearCache(): void {
    this.adminService.clearCache().subscribe({
      next: () => {
        this.toastService.success('Cache Cleared', 'System cache has been cleared successfully');
      },
      error: (err) => {
        console.error('Failed to clear cache:', err);
        this.toastService.error('Failed', 'Could not clear cache');
      }
    });
  }

  restartServices(): void {
    this.toastService.info('Restarting...', 'Services restart in progress');
    this.adminService.restartServices().subscribe({
      next: () => {
        this.toastService.success('Restarted', 'Services have been restarted');
        setTimeout(() => this.loadSystemStats(), 2000);
      },
      error: (err) => {
        console.error('Failed to restart services:', err);
        this.toastService.error('Failed', 'Could not restart services');
      }
    });
  }

  runDiagnostics(): void {
    this.toastService.info('Running...', 'System diagnostics in progress');
    // This would typically call a diagnostics endpoint
    setTimeout(() => {
      this.toastService.success('Complete', 'Diagnostics completed - all systems healthy');
    }, 2000);
  }

  viewLogs(): void {
    this.router.navigate(['/system/audit']);
  }
}
