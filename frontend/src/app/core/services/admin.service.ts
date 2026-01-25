import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import {
  DashboardStats,
  DashboardCharts,
  DashboardActivity,
  UserListResponse,
  UserFilters,
  User,
  UserDetail,
  BulkUserAction,
  BulkActionResponse,
  ImpersonateResponse,
  ExportFormat,
  StudentListResponse,
  StudentDetails,
  StudentDetailResponse,
  StudentAnalytics,
  StudentSessionsResponse,
  StudentActivityResponse,
  StudentStatsOverview,
  AdminUser,
  CreateAdminRequest,
} from '../models';

export interface CreateUserRequest {
  email: string;
  phone_number: string;
  password: string;
  role: string;
  full_name?: string;
  institution?: string;
}

export interface SystemStats {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_connections: number;
  uptime: number;
  services: ServiceStatus[];
}

export interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  response_time: number;
  uptime: number;
  last_check: string;
}

export interface AuditLog {
  id: string;
  action: string;
  category: string;
  user_id: string;
  user_email: string;
  ip_address: string;
  details: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error';
}

export interface AuditLogResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogFilters {
  category?: string;
  status?: string;
  user_id?: string;
  from_date?: string;
  to_date?: string;
  page?: number;
  page_size?: number;
}

export interface SystemSettings {
  platform_name: string;
  support_email: string;
  language: string;
  timezone: string;
  maintenance_mode: boolean;
  require_2fa: boolean;
  session_timeout: number;
  max_login_attempts: number;
  strong_passwords: boolean;
  email_notifications: boolean;
  currency: string;
  trial_enabled: boolean;
  trial_days: number;
  auto_renew: boolean;
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  action_url?: string;
  action_label?: string;
}

@Injectable({
  providedIn: 'root',
})
export class AdminService {
  private readonly basePath = '/admin';

  constructor(private api: ApiService) {}

  // Dashboard
  getDashboardStats(): Observable<DashboardStats> {
    return this.api.get<DashboardStats>(`${this.basePath}/dashboard/stats`);
  }

  getDashboardCharts(days: number = 30): Observable<DashboardCharts> {
    return this.api.get<DashboardCharts>(`${this.basePath}/dashboard/charts`, { days });
  }

  getDashboardActivity(limit: number = 50, offset: number = 0): Observable<DashboardActivity> {
    return this.api.get<DashboardActivity>(`${this.basePath}/dashboard/activity`, { limit, offset });
  }

  // Legacy method for backward compatibility
  getActivity(): Observable<DashboardActivity> {
    return this.getDashboardActivity();
  }

  getChartData(): Observable<DashboardCharts> {
    return this.getDashboardCharts();
  }

  // User Management
  getUsers(filters?: UserFilters): Observable<UserListResponse> {
    return this.api.get<UserListResponse>(`${this.basePath}/users`, filters).pipe(
      map(response => {
        // Normalize response - backend may return 'users' instead of 'items'
        if (response && !response.items && (response as any).users) {
          return {
            ...response,
            items: (response as any).users
          };
        }
        return response;
      })
    );
  }

  getUserById(userId: string): Observable<UserDetail> {
    return this.api.get<UserDetail>(`${this.basePath}/users/${userId}`);
  }

  getUser(userId: string): Observable<User> {
    return this.api.get<User>(`${this.basePath}/users/${userId}`);
  }

  createUser(data: CreateUserRequest): Observable<User> {
    return this.api.post<User>(`${this.basePath}/users`, data);
  }

  updateUser(userId: string, data: Partial<User>): Observable<User> {
    return this.api.put<User>(`${this.basePath}/users/${userId}`, data);
  }

  deleteUser(userId: string): Observable<{ success: boolean }> {
    return this.api.delete(`${this.basePath}/users/${userId}`);
  }

  suspendUser(userId: string): Observable<User> {
    return this.api.post<User>(`${this.basePath}/users/${userId}/suspend`, {});
  }

  activateUser(userId: string): Observable<User> {
    return this.api.post<User>(`${this.basePath}/users/${userId}/activate`, {});
  }

  resetUserPassword(userId: string): Observable<{ success: boolean; message?: string }> {
    return this.api.post(`${this.basePath}/users/${userId}/reset-password`, {});
  }

  verifyUser(userId: string): Observable<User> {
    return this.api.post<User>(`${this.basePath}/users/${userId}/verify`, {});
  }

  bulkUserAction(action: BulkUserAction): Observable<BulkActionResponse> {
    return this.api.post<BulkActionResponse>(`${this.basePath}/users/bulk-action`, action);
  }

  exportUsers(filters?: UserFilters, format: ExportFormat = ExportFormat.CSV): Observable<Blob> {
    return this.api.download(`${this.basePath}/users/export`, { ...filters, format });
  }

  impersonateUser(userId: string, readOnly: boolean = true): Observable<ImpersonateResponse> {
    return this.api.post<ImpersonateResponse>(`${this.basePath}/users/${userId}/impersonate`, { read_only: readOnly });
  }

  // End impersonation session
  endImpersonation(): Observable<{ success: boolean }> {
    return this.api.post(`${this.basePath}/users/end-impersonation`, {});
  }

  // Get user activity/audit log
  getUserActivity(userId: string, limit: number = 50): Observable<any[]> {
    return this.api.get<any[]>(`${this.basePath}/users/${userId}/activity`, { limit });
  }

  // Update subscription tier
  updateUserSubscription(userId: string, tier: string, expiresAt?: string): Observable<User> {
    return this.api.put<User>(`${this.basePath}/users/${userId}`, {
      subscription_tier: tier,
      subscription_expires_at: expiresAt
    });
  }

  // Admin Management
  getAdmins(): Observable<AdminUser[]> {
    return this.api.get<AdminUser[]>(`${this.basePath}/admins`).pipe(
      map(response => {
        // Normalize backend response to match AdminUser interface
        if (Array.isArray(response)) {
          return response.map(admin => ({
            id: admin.id,
            email: admin.email,
            name: admin.name || admin.email?.split('@')[0] || 'Unknown',
            phone_number: (admin as any).phone_number,
            role: admin.role || 'admin',
            permissions: admin.permissions || [],
            created_at: admin.created_at,
            last_login: admin.last_login || (admin as any).last_active,
            is_active: admin.is_active,
            is_verified: (admin as any).is_verified
          } as AdminUser));
        }
        return response;
      })
    );
  }

  createAdmin(data: CreateAdminRequest): Observable<{ success: boolean; id?: string; email?: string; message?: string; error?: string }> {
    // Backend expects form data: email, password, phone_number
    return this.api.postForm(`${this.basePath}/admins`, {
      email: data.email,
      password: data.password,
      phone_number: data.phone_number || null
    });
  }

  updateAdmin(adminId: string, data: Partial<AdminUser> & { password?: string }): Observable<{ id: string; message: string }> {
    // Backend expects form data: email, password, is_active
    const formData: Record<string, any> = {};
    if (data.email) formData['email'] = data.email;
    if (data.password) formData['password'] = data.password;
    if (data.is_active !== undefined) formData['is_active'] = data.is_active;
    return this.api.putForm(`${this.basePath}/admins/${adminId}`, formData);
  }

  deleteAdmin(adminId: string): Observable<{ success: boolean; message?: string; error?: string }> {
    return this.api.delete(`${this.basePath}/admins/${adminId}`);
  }

  reactivateAdmin(adminId: string): Observable<{ id: string; message: string }> {
    return this.api.putForm(`${this.basePath}/admins/${adminId}`, { is_active: true });
  }

  // Student Management
  getStudents(filters?: {
    grade?: string;
    education_level?: string;
    school?: string;
    subscription_tier?: string;
    is_active?: boolean;
    search?: string;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }): Observable<StudentListResponse> {
    return this.api.get<StudentListResponse>(`${this.basePath}/students`, filters);
  }

  getStudentById(studentId: string): Observable<StudentDetailResponse> {
    return this.api.get<StudentDetailResponse>(`${this.basePath}/students/${studentId}`);
  }

  getStudentAnalytics(studentId: string): Observable<StudentAnalytics> {
    return this.api.get<StudentAnalytics>(`${this.basePath}/students/${studentId}/analytics`);
  }

  getStudentSessions(studentId: string, options?: {
    limit?: number;
    offset?: number;
    session_type?: string;
    status?: string;
  }): Observable<StudentSessionsResponse> {
    return this.api.get<StudentSessionsResponse>(
      `${this.basePath}/students/${studentId}/sessions`,
      options
    );
  }

  getStudentActivity(studentId: string, limit: number = 20): Observable<StudentActivityResponse> {
    return this.api.get<StudentActivityResponse>(
      `${this.basePath}/students/${studentId}/activity`,
      { limit }
    );
  }

  getStudentsStats(): Observable<StudentStatsOverview> {
    return this.api.get<StudentStatsOverview>(`${this.basePath}/students/stats/overview`);
  }

  getStudentReport(studentId: string, format: string = 'json'): Observable<Blob> {
    return this.api.download(`${this.basePath}/students/${studentId}/report`, { format });
  }

  // System Management
  getSystemStats(): Observable<SystemStats> {
    return this.api.get<SystemStats>(`${this.basePath}/system/stats`);
  }

  getSystemSettings(): Observable<SystemSettings> {
    return this.api.get<SystemSettings>(`${this.basePath}/system/settings`);
  }

  updateSystemSettings(settings: Partial<SystemSettings>): Observable<SystemSettings> {
    return this.api.put<SystemSettings>(`${this.basePath}/system/settings`, settings);
  }

  clearCache(): Observable<{ success: boolean }> {
    return this.api.post(`${this.basePath}/system/cache/clear`, {});
  }

  restartServices(): Observable<{ success: boolean }> {
    return this.api.post(`${this.basePath}/system/restart`, {});
  }

  // Audit Logs
  getAuditLogs(filters?: AuditLogFilters): Observable<AuditLogResponse> {
    // Backend endpoint uses hyphen: /audit-log
    const params: Record<string, any> = {};
    if (filters?.user_id) params['admin_id'] = filters.user_id;
    if (filters?.category) params['resource_type'] = filters.category;
    if (filters?.status) params['action'] = filters.status;
    if (filters?.from_date) params['date_from'] = filters.from_date;
    if (filters?.to_date) params['date_to'] = filters.to_date;
    if (filters?.page_size) params['limit'] = filters.page_size;
    if (filters?.page) params['offset'] = ((filters.page - 1) * (filters.page_size || 20));

    return this.api.get<any>(`${this.basePath}/audit-log`, params).pipe(
      map(response => {
        // Normalize backend response format
        return {
          items: (response.entries || []).map((entry: any) => ({
            id: entry.id,
            action: entry.action,
            category: entry.resource_type || 'system',
            user_id: entry.admin_id,
            user_email: entry.admin_email || 'Unknown',
            ip_address: entry.ip_address || 'N/A',
            details: typeof entry.details === 'object' ? JSON.stringify(entry.details) : entry.details,
            timestamp: entry.timestamp,
            status: 'success' as const // Backend doesn't track status, default to success
          })),
          total: response.total || 0,
          page: filters?.page || 1,
          page_size: filters?.page_size || 20
        };
      })
    );
  }

  exportAuditLogs(filters?: AuditLogFilters): Observable<Blob> {
    // Build CSV content from audit logs
    return this.getAuditLogs({ ...filters, page_size: 1000 }).pipe(
      map(response => {
        const headers = ['Timestamp', 'Action', 'Category', 'User', 'IP Address', 'Details'];
        const rows = response.items.map(item =>
          [item.timestamp, item.action, item.category, item.user_email, item.ip_address, item.details]
            .map(v => `"${String(v).replace(/"/g, '""')}"`)
            .join(',')
        );
        const csv = [headers.join(','), ...rows].join('\n');
        return new Blob([csv], { type: 'text/csv' });
      })
    );
  }

  // Notifications
  getNotifications(): Observable<Notification[]> {
    return this.api.get<Notification[]>(`${this.basePath}/notifications`);
  }

  markNotificationRead(notificationId: string): Observable<{ success: boolean }> {
    return this.api.post(`${this.basePath}/notifications/${notificationId}/read`, {});
  }

  markAllNotificationsRead(): Observable<{ success: boolean }> {
    return this.api.post(`${this.basePath}/notifications/read-all`, {});
  }

  deleteNotification(notificationId: string): Observable<{ success: boolean }> {
    return this.api.delete(`${this.basePath}/notifications/${notificationId}`);
  }

  clearAllNotifications(): Observable<{ success: boolean }> {
    return this.api.delete(`${this.basePath}/notifications`);
  }
}
