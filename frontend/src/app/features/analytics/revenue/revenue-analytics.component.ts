import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-revenue-analytics',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>Revenue Analytics</h1>
          <p class="subtitle">Financial performance and subscription metrics</p>
        </div>
        <div class="header-actions">
          <select [(value)]="selectedPeriod">
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

      <div class="metrics-grid">
        <div class="metric-card highlight">
          <div class="metric-header">
            <span class="metric-label">Monthly Recurring Revenue</span>
            <span class="metric-trend positive">
              <span class="material-symbols-outlined">trending_up</span>
              +15.7%
            </span>
          </div>
          <span class="metric-value">$24,890</span>
          <div class="metric-comparison">vs $21,500 last month</div>
        </div>
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-label">Total Revenue (YTD)</span>
          </div>
          <span class="metric-value">$186,450</span>
          <div class="metric-comparison">Target: $200,000</div>
        </div>
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-label">Average Revenue Per User</span>
            <span class="metric-trend positive">
              <span class="material-symbols-outlined">trending_up</span>
              +8.2%
            </span>
          </div>
          <span class="metric-value">$7.85</span>
        </div>
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-label">Churn Rate</span>
            <span class="metric-trend negative">
              <span class="material-symbols-outlined">trending_down</span>
              -2.1%
            </span>
          </div>
          <span class="metric-value">3.2%</span>
        </div>
      </div>

      <div class="content-row">
        <div class="card">
          <div class="card-header">
            <h3>Revenue Trend</h3>
          </div>
          <div class="card-body">
            <div class="revenue-chart">
              @for (month of months; track month; let i = $index) {
                <div class="chart-column">
                  <div class="bar-container">
                    <div class="bar" [style.height.%]="revenueData[i]"></div>
                  </div>
                  <span class="month-label">{{ month }}</span>
                </div>
              }
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Revenue by Plan</h3>
          </div>
          <div class="card-body">
            <div class="plan-breakdown">
              @for (plan of planRevenue; track plan.name) {
                <div class="plan-item">
                  <div class="plan-header">
                    <span class="plan-name">{{ plan.name }}</span>
                    <span class="plan-amount">\${{ plan.amount | number }}</span>
                  </div>
                  <div class="plan-bar">
                    <div class="bar-fill" [style.width.%]="plan.percentage" [style.background-color]="plan.color"></div>
                  </div>
                  <div class="plan-meta">
                    <span>{{ plan.subscribers }} subscribers</span>
                    <span>{{ plan.percentage }}% of total</span>
                  </div>
                </div>
              }
            </div>
          </div>
        </div>
      </div>

      <div class="content-row">
        <div class="card">
          <div class="card-header">
            <h3>Recent Transactions</h3>
            <button class="btn-link">View All</button>
          </div>
          <div class="card-body no-padding">
            <table class="transactions-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Plan</th>
                  <th>Amount</th>
                  <th>Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                @for (tx of recentTransactions; track tx.id) {
                  <tr>
                    <td>
                      <div class="user-cell">
                        <div class="avatar">{{ tx.initials }}</div>
                        <span>{{ tx.user }}</span>
                      </div>
                    </td>
                    <td>{{ tx.plan }}</td>
                    <td class="amount">\${{ tx.amount }}</td>
                    <td>{{ tx.date }}</td>
                    <td><span class="status-badge" [class]="tx.status">{{ tx.status }}</span></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Key Metrics</h3>
          </div>
          <div class="card-body">
            <div class="key-metrics">
              <div class="metric-row">
                <span class="label">Customer Lifetime Value</span>
                <span class="value">$156.80</span>
              </div>
              <div class="metric-row">
                <span class="label">Customer Acquisition Cost</span>
                <span class="value">$12.50</span>
              </div>
              <div class="metric-row">
                <span class="label">LTV:CAC Ratio</span>
                <span class="value highlight">12.5x</span>
              </div>
              <div class="metric-row">
                <span class="label">Payback Period</span>
                <span class="value">1.6 months</span>
              </div>
              <div class="metric-row">
                <span class="label">Net Revenue Retention</span>
                <span class="value">108%</span>
              </div>
              <div class="metric-row">
                <span class="label">Gross Margin</span>
                <span class="value">82%</span>
              </div>
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
    .header-actions { display: flex; gap: 0.75rem; }
    .header-actions select { padding: 0.5rem 1rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem; color: var(--text-primary); font-size: 0.875rem; }
    .btn-secondary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; font-size: 0.875rem; font-weight: 500; background-color: var(--surface); color: var(--text-primary); border: 1px solid var(--border); border-radius: 0.5rem; cursor: pointer; &:hover { background-color: var(--hover); } }
    .btn-link { background: none; border: none; color: var(--primary); font-size: 0.875rem; font-weight: 500; cursor: pointer; &:hover { text-decoration: underline; } }

    .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
    @media (max-width: 1200px) { .metrics-grid { grid-template-columns: repeat(2, 1fr); } }

    .metric-card { padding: 1.25rem; background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; &.highlight { border-color: var(--primary); background: linear-gradient(135deg, rgba(0, 102, 70, 0.05) 0%, rgba(0, 102, 70, 0.1) 100%); } }
    .metric-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
    .metric-label { font-size: 0.75rem; color: var(--text-secondary); }
    .metric-trend { display: flex; align-items: center; gap: 0.25rem; font-size: 0.75rem; font-weight: 500; &.positive { color: #10b981; } &.negative { color: #ef4444; } .material-symbols-outlined { font-size: 1rem; } }
    .metric-value { font-size: 1.75rem; font-weight: 700; color: var(--text-primary); display: block; }
    .metric-comparison { font-size: 0.75rem; color: var(--text-tertiary); margin-top: 0.25rem; }

    .content-row { display: grid; grid-template-columns: 1.5fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
    @media (max-width: 1024px) { .content-row { grid-template-columns: 1fr; } }

    .card { background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; overflow: hidden; }
    .card-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem; border-bottom: 1px solid var(--border); h3 { font-size: 1rem; font-weight: 600; color: var(--text-primary); } }
    .card-body { padding: 1.25rem; &.no-padding { padding: 0; } }

    .revenue-chart { display: flex; align-items: flex-end; justify-content: space-between; height: 200px; padding-top: 1rem; }
    .chart-column { display: flex; flex-direction: column; align-items: center; flex: 1; height: 100%; }
    .bar-container { flex: 1; width: 100%; display: flex; align-items: flex-end; justify-content: center; padding: 0 8px; }
    .bar { width: 100%; max-width: 40px; background: linear-gradient(180deg, var(--primary) 0%, #004d34 100%); border-radius: 4px 4px 0 0; transition: height 0.3s ease; }
    .month-label { font-size: 0.625rem; color: var(--text-tertiary); margin-top: 8px; }

    .plan-breakdown { display: flex; flex-direction: column; gap: 1.25rem; }
    .plan-item { display: flex; flex-direction: column; gap: 0.5rem; }
    .plan-header { display: flex; justify-content: space-between; }
    .plan-name { font-size: 0.875rem; font-weight: 500; color: var(--text-primary); }
    .plan-amount { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); }
    .plan-bar { height: 8px; background-color: var(--background); border-radius: 4px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 4px; }
    .plan-meta { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-tertiary); }

    .transactions-table { width: 100%; border-collapse: collapse; }
    .transactions-table th, .transactions-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }
    .transactions-table th { font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); background-color: var(--background); text-transform: uppercase; }
    .transactions-table td { font-size: 0.875rem; color: var(--text-primary); }
    .transactions-table tr:last-child td { border-bottom: none; }
    .user-cell { display: flex; align-items: center; gap: 0.5rem; }
    .avatar { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background-color: var(--primary); color: white; font-size: 0.625rem; font-weight: 600; border-radius: 50%; }
    .amount { font-weight: 600; color: var(--primary); }
    .status-badge { padding: 0.25rem 0.5rem; font-size: 0.625rem; font-weight: 500; border-radius: 9999px; text-transform: capitalize; &.completed { background-color: rgba(16, 185, 129, 0.1); color: #10b981; } &.pending { background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; } &.failed { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; } }

    .key-metrics { display: flex; flex-direction: column; gap: 1rem; }
    .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background-color: var(--background); border-radius: 0.5rem; }
    .metric-row .label { font-size: 0.875rem; color: var(--text-secondary); }
    .metric-row .value { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); &.highlight { color: var(--primary); font-size: 1rem; } }
  `]
})
export class RevenueAnalyticsComponent implements OnInit {
  selectedPeriod = '30d';
  months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  revenueData = [45, 52, 48, 60, 55, 65, 70, 75, 68, 80, 85, 90];

  planRevenue = [
    { name: 'Premium', amount: 12450, subscribers: 1245, percentage: 50, color: '#006646' },
    { name: 'Basic', amount: 6890, subscribers: 1380, percentage: 28, color: '#3b82f6' },
    { name: 'Enterprise', amount: 4250, subscribers: 142, percentage: 17, color: '#8b5cf6' },
    { name: 'Free Trial', amount: 1300, subscribers: 520, percentage: 5, color: '#f59e0b' },
  ];

  recentTransactions = [
    { id: 1, user: 'John Doe', initials: 'JD', plan: 'Premium', amount: 9.99, date: 'Today', status: 'completed' },
    { id: 2, user: 'Jane Smith', initials: 'JS', plan: 'Basic', amount: 4.99, date: 'Today', status: 'completed' },
    { id: 3, user: 'Bob Wilson', initials: 'BW', plan: 'Enterprise', amount: 29.99, date: 'Yesterday', status: 'completed' },
    { id: 4, user: 'Alice Brown', initials: 'AB', plan: 'Premium', amount: 9.99, date: 'Yesterday', status: 'pending' },
    { id: 5, user: 'Charlie Davis', initials: 'CD', plan: 'Basic', amount: 4.99, date: '2 days ago', status: 'completed' },
  ];

  ngOnInit(): void {}
}
