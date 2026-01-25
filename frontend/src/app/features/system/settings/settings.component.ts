import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ToastService } from '../../../core/services/toast.service';
import { AdminService, SystemSettings } from '../../../core/services/admin.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>Settings</h1>
          <p class="subtitle">Configure system preferences and options</p>
        </div>
      </div>

      <div class="settings-layout">
        <nav class="settings-nav">
          <button [class.active]="activeSection === 'general'" (click)="activeSection = 'general'">
            <span class="material-symbols-outlined">settings</span>
            General
          </button>
          <button [class.active]="activeSection === 'security'" (click)="activeSection = 'security'">
            <span class="material-symbols-outlined">security</span>
            Security
          </button>
          <button [class.active]="activeSection === 'notifications'" (click)="activeSection = 'notifications'">
            <span class="material-symbols-outlined">notifications</span>
            Notifications
          </button>
          <button [class.active]="activeSection === 'integrations'" (click)="activeSection = 'integrations'">
            <span class="material-symbols-outlined">extension</span>
            Integrations
          </button>
          <button [class.active]="activeSection === 'billing'" (click)="activeSection = 'billing'">
            <span class="material-symbols-outlined">credit_card</span>
            Billing
          </button>
        </nav>

        <div class="settings-content">
          @if (activeSection === 'general') {
            <div class="settings-section">
              <h2>General Settings</h2>
              <p class="section-desc">Basic platform configuration options</p>

              <div class="setting-group">
                <label class="setting-label">Platform Name</label>
                <input type="text" [(ngModel)]="settings.platformName" class="setting-input" />
                <span class="setting-hint">Displayed in emails and the dashboard header</span>
              </div>

              <div class="setting-group">
                <label class="setting-label">Support Email</label>
                <input type="email" [(ngModel)]="settings.supportEmail" class="setting-input" />
              </div>

              <div class="setting-group">
                <label class="setting-label">Default Language</label>
                <select [(ngModel)]="settings.language" class="setting-select">
                  <option value="en">English</option>
                  <option value="sn">Shona</option>
                  <option value="nd">Ndebele</option>
                </select>
              </div>

              <div class="setting-group">
                <label class="setting-label">Timezone</label>
                <select [(ngModel)]="settings.timezone" class="setting-select">
                  <option value="Africa/Harare">Africa/Harare (CAT)</option>
                  <option value="UTC">UTC</option>
                </select>
              </div>

              <div class="setting-toggle">
                <div class="toggle-info">
                  <span class="toggle-label">Maintenance Mode</span>
                  <span class="toggle-desc">Temporarily disable access for non-admin users</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" [(ngModel)]="settings.maintenanceMode" />
                  <span class="slider"></span>
                </label>
              </div>
            </div>
          }

          @if (activeSection === 'security') {
            <div class="settings-section">
              <h2>Security Settings</h2>
              <p class="section-desc">Configure authentication and access controls</p>

              <div class="setting-toggle">
                <div class="toggle-info">
                  <span class="toggle-label">Two-Factor Authentication</span>
                  <span class="toggle-desc">Require 2FA for all admin accounts</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" [(ngModel)]="settings.require2FA" />
                  <span class="slider"></span>
                </label>
              </div>

              <div class="setting-group">
                <label class="setting-label">Session Timeout (minutes)</label>
                <input type="number" [(ngModel)]="settings.sessionTimeout" class="setting-input" min="5" max="1440" />
              </div>

              <div class="setting-group">
                <label class="setting-label">Max Login Attempts</label>
                <input type="number" [(ngModel)]="settings.maxLoginAttempts" class="setting-input" min="3" max="10" />
              </div>

              <div class="setting-toggle">
                <div class="toggle-info">
                  <span class="toggle-label">Password Complexity</span>
                  <span class="toggle-desc">Require strong passwords with special characters</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" [(ngModel)]="settings.strongPasswords" />
                  <span class="slider"></span>
                </label>
              </div>
            </div>
          }

          @if (activeSection === 'notifications') {
            <div class="settings-section">
              <h2>Notification Settings</h2>
              <p class="section-desc">Configure email and push notification preferences</p>

              <div class="setting-toggle">
                <div class="toggle-info">
                  <span class="toggle-label">Email Notifications</span>
                  <span class="toggle-desc">Send email alerts for important events</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" [(ngModel)]="settings.emailNotifications" />
                  <span class="slider"></span>
                </label>
              </div>

              <div class="setting-toggle">
                <div class="toggle-info">
                  <span class="toggle-label">New User Alerts</span>
                  <span class="toggle-desc">Notify when new users register</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" [(ngModel)]="settings.newUserAlerts" />
                  <span class="slider"></span>
                </label>
              </div>

              <div class="setting-toggle">
                <div class="toggle-info">
                  <span class="toggle-label">Payment Alerts</span>
                  <span class="toggle-desc">Notify on successful payments and failures</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" [(ngModel)]="settings.paymentAlerts" />
                  <span class="slider"></span>
                </label>
              </div>

              <div class="setting-toggle">
                <div class="toggle-info">
                  <span class="toggle-label">System Alerts</span>
                  <span class="toggle-desc">Critical system and performance alerts</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" [(ngModel)]="settings.systemAlerts" />
                  <span class="slider"></span>
                </label>
              </div>
            </div>
          }

          @if (activeSection === 'integrations') {
            <div class="settings-section">
              <h2>Integrations</h2>
              <p class="section-desc">Connect with external services</p>

              <div class="integration-card">
                <div class="integration-icon paynow">
                  <span class="material-symbols-outlined">payments</span>
                </div>
                <div class="integration-info">
                  <h4>PayNow</h4>
                  <p>Zimbabwe mobile payment gateway</p>
                </div>
                <span class="integration-status connected">Connected</span>
              </div>

              <div class="integration-card">
                <div class="integration-icon sms">
                  <span class="material-symbols-outlined">sms</span>
                </div>
                <div class="integration-info">
                  <h4>SMS Gateway</h4>
                  <p>Send SMS notifications to users</p>
                </div>
                <button class="btn-connect">Connect</button>
              </div>

              <div class="integration-card">
                <div class="integration-icon ai">
                  <span class="material-symbols-outlined">smart_toy</span>
                </div>
                <div class="integration-info">
                  <h4>OpenAI API</h4>
                  <p>AI-powered tutoring engine</p>
                </div>
                <span class="integration-status connected">Connected</span>
              </div>
            </div>
          }

          @if (activeSection === 'billing') {
            <div class="settings-section">
              <h2>Billing Settings</h2>
              <p class="section-desc">Configure payment and subscription options</p>

              <div class="setting-group">
                <label class="setting-label">Currency</label>
                <select [(ngModel)]="settings.currency" class="setting-select">
                  <option value="USD">USD ($)</option>
                  <option value="ZWL">ZWL (RTGS$)</option>
                </select>
              </div>

              <div class="setting-toggle">
                <div class="toggle-info">
                  <span class="toggle-label">Trial Period</span>
                  <span class="toggle-desc">Allow free trial for new users</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" [(ngModel)]="settings.trialEnabled" />
                  <span class="slider"></span>
                </label>
              </div>

              <div class="setting-group">
                <label class="setting-label">Trial Duration (days)</label>
                <input type="number" [(ngModel)]="settings.trialDays" class="setting-input" min="1" max="30" />
              </div>

              <div class="setting-toggle">
                <div class="toggle-info">
                  <span class="toggle-label">Auto-renew Subscriptions</span>
                  <span class="toggle-desc">Automatically renew expired subscriptions</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" [(ngModel)]="settings.autoRenew" />
                  <span class="slider"></span>
                </label>
              </div>
            </div>
          }

          <div class="settings-actions">
            <button class="btn-secondary" (click)="resetSettings()">Reset to Defaults</button>
            <button class="btn-primary" (click)="saveSettings()">Save Changes</button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .page-container { padding: 1.5rem; }
    .page-header { margin-bottom: 1.5rem; }
    .header-info h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
    .header-info .subtitle { font-size: 0.875rem; color: var(--text-secondary); }

    .settings-layout { display: grid; grid-template-columns: 240px 1fr; gap: 1.5rem; }
    @media (max-width: 768px) { .settings-layout { grid-template-columns: 1fr; } }

    .settings-nav {
      display: flex; flex-direction: column; gap: 0.25rem; padding: 0.5rem;
      background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; height: fit-content;
      button {
        display: flex; align-items: center; gap: 0.75rem; width: 100%; padding: 0.75rem 1rem;
        background: transparent; border: none; border-radius: 0.5rem; text-align: left;
        font-size: 0.875rem; color: var(--text-secondary); cursor: pointer; transition: all 0.15s ease;
        .material-symbols-outlined { font-size: 1.25rem; }
        &:hover { background-color: var(--hover); color: var(--text-primary); }
        &.active { background-color: var(--primary); color: white; }
      }
    }

    .settings-content { background-color: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1.5rem; }
    .settings-section { margin-bottom: 2rem; }
    .settings-section h2 { font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem; }
    .section-desc { font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 1.5rem; }

    .setting-group { margin-bottom: 1.25rem; }
    .setting-label { display: block; font-size: 0.875rem; font-weight: 500; color: var(--text-primary); margin-bottom: 0.5rem; }
    .setting-input, .setting-select {
      width: 100%; max-width: 400px; padding: 0.625rem 0.875rem; font-size: 0.875rem;
      background-color: var(--background); color: var(--text-primary);
      border: 1px solid var(--border); border-radius: 0.5rem;
      &:focus { outline: none; border-color: var(--primary); }
    }
    .setting-hint { display: block; font-size: 0.75rem; color: var(--text-tertiary); margin-top: 0.375rem; }

    .setting-toggle {
      display: flex; justify-content: space-between; align-items: center;
      padding: 1rem; background-color: var(--background); border-radius: 0.5rem; margin-bottom: 0.75rem;
    }
    .toggle-info { .toggle-label { display: block; font-size: 0.875rem; font-weight: 500; color: var(--text-primary); } .toggle-desc { font-size: 0.75rem; color: var(--text-tertiary); } }

    .toggle-switch {
      position: relative; width: 48px; height: 24px;
      input { opacity: 0; width: 0; height: 0; }
      .slider {
        position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background-color: var(--border); border-radius: 24px; cursor: pointer; transition: 0.3s;
        &::before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; border-radius: 50%; transition: 0.3s; }
      }
      input:checked + .slider { background-color: var(--primary); }
      input:checked + .slider::before { transform: translateX(24px); }
    }

    .integration-card {
      display: flex; align-items: center; gap: 1rem; padding: 1rem;
      background-color: var(--background); border-radius: 0.5rem; margin-bottom: 0.75rem;
    }
    .integration-icon {
      width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 0.5rem;
      &.paynow { background-color: rgba(16, 185, 129, 0.1); .material-symbols-outlined { color: #10b981; } }
      &.sms { background-color: rgba(59, 130, 246, 0.1); .material-symbols-outlined { color: #3b82f6; } }
      &.ai { background-color: rgba(139, 92, 246, 0.1); .material-symbols-outlined { color: #8b5cf6; } }
    }
    .integration-info { flex: 1; h4 { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); } p { font-size: 0.75rem; color: var(--text-secondary); } }
    .integration-status { padding: 0.25rem 0.75rem; font-size: 0.75rem; font-weight: 500; border-radius: 9999px; &.connected { background-color: rgba(16, 185, 129, 0.1); color: #10b981; } }
    .btn-connect { padding: 0.375rem 0.75rem; font-size: 0.75rem; font-weight: 500; background-color: var(--primary); color: white; border: none; border-radius: 0.375rem; cursor: pointer; }

    .settings-actions { display: flex; justify-content: flex-end; gap: 0.75rem; padding-top: 1.5rem; border-top: 1px solid var(--border); }
    .btn-primary, .btn-secondary {
      padding: 0.625rem 1.25rem; font-size: 0.875rem; font-weight: 500; border-radius: 0.5rem; cursor: pointer;
    }
    .btn-primary { background-color: var(--primary); color: white; border: none; &:hover { background-color: #005238; } }
    .btn-secondary { background-color: var(--background); color: var(--text-primary); border: 1px solid var(--border); &:hover { background-color: var(--hover); } }
  `]
})
export class SettingsComponent implements OnInit {
  private toastService = inject(ToastService);
  private adminService = inject(AdminService);

  activeSection: 'general' | 'security' | 'notifications' | 'integrations' | 'billing' = 'general';
  isLoading = signal(false);
  isSaving = signal(false);

  settings = {
    platformName: 'EduBot Zimbabwe',
    supportEmail: 'support@edubot.co.zw',
    language: 'en',
    timezone: 'Africa/Harare',
    maintenanceMode: false,
    require2FA: true,
    sessionTimeout: 30,
    maxLoginAttempts: 5,
    strongPasswords: true,
    emailNotifications: true,
    newUserAlerts: true,
    paymentAlerts: true,
    systemAlerts: true,
    currency: 'USD',
    trialEnabled: true,
    trialDays: 7,
    autoRenew: true,
  };

  private defaultSettings = { ...this.settings };

  ngOnInit(): void {
    this.loadSettings();
  }

  loadSettings(): void {
    this.isLoading.set(true);
    this.adminService.getSystemSettings().subscribe({
      next: (apiSettings) => {
        // Map API settings to component settings
        this.settings = {
          platformName: apiSettings.platform_name,
          supportEmail: apiSettings.support_email,
          language: apiSettings.language,
          timezone: apiSettings.timezone,
          maintenanceMode: apiSettings.maintenance_mode,
          require2FA: apiSettings.require_2fa,
          sessionTimeout: apiSettings.session_timeout,
          maxLoginAttempts: apiSettings.max_login_attempts,
          strongPasswords: apiSettings.strong_passwords,
          emailNotifications: apiSettings.email_notifications,
          newUserAlerts: true, // Not in API
          paymentAlerts: true, // Not in API
          systemAlerts: true, // Not in API
          currency: apiSettings.currency,
          trialEnabled: apiSettings.trial_enabled,
          trialDays: apiSettings.trial_days,
          autoRenew: apiSettings.auto_renew,
        };
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load settings:', err);
        this.isLoading.set(false);
      }
    });
  }

  saveSettings(): void {
    this.isSaving.set(true);

    const apiSettings: Partial<SystemSettings> = {
      platform_name: this.settings.platformName,
      support_email: this.settings.supportEmail,
      language: this.settings.language,
      timezone: this.settings.timezone,
      maintenance_mode: this.settings.maintenanceMode,
      require_2fa: this.settings.require2FA,
      session_timeout: this.settings.sessionTimeout,
      max_login_attempts: this.settings.maxLoginAttempts,
      strong_passwords: this.settings.strongPasswords,
      email_notifications: this.settings.emailNotifications,
      currency: this.settings.currency,
      trial_enabled: this.settings.trialEnabled,
      trial_days: this.settings.trialDays,
      auto_renew: this.settings.autoRenew,
    };

    this.adminService.updateSystemSettings(apiSettings).subscribe({
      next: () => {
        this.toastService.success('Settings Saved', 'Your changes have been saved successfully');
        this.isSaving.set(false);
      },
      error: (err) => {
        console.error('Failed to save settings:', err);
        this.toastService.error('Save Failed', 'Could not save settings. Please try again.');
        this.isSaving.set(false);
      }
    });
  }

  resetSettings(): void {
    this.settings = { ...this.defaultSettings };
    this.toastService.info('Settings Reset', 'Settings have been reset to defaults');
  }
}
