import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import {
  AuditLogResponse,
  AuditLogFilters,
  GlobalSettings,
  FeatureFlag,
  SystemHealthStatus,
  ErrorLogResponse,
  Notification,
  BroadcastRequest,
  RAGStats,
} from '../models';

@Injectable({
  providedIn: 'root',
})
export class SystemService {
  private readonly basePath = '/admin';

  constructor(private api: ApiService) {}

  // Audit Log
  getAuditLog(filters?: AuditLogFilters): Observable<AuditLogResponse> {
    return this.api.get<AuditLogResponse>(`${this.basePath}/audit-log`, filters);
  }

  // Settings
  getGlobalSettings(): Observable<GlobalSettings> {
    return this.api.get<GlobalSettings>(`${this.basePath}/settings`);
  }

  updateGlobalSettings(data: Partial<GlobalSettings>): Observable<GlobalSettings> {
    return this.api.put<GlobalSettings>(`${this.basePath}/settings`, data);
  }

  // Feature Flags
  getFeatureFlags(): Observable<FeatureFlag[]> {
    return this.api.get<FeatureFlag[]>(`${this.basePath}/settings/features`);
  }

  updateFeatureFlag(flagId: string, data: Partial<FeatureFlag>): Observable<FeatureFlag> {
    return this.api.put<FeatureFlag>(`${this.basePath}/settings/features/${flagId}`, data);
  }

  // Maintenance Mode
  setMaintenanceMode(enabled: boolean, message?: string): Observable<{ success: boolean }> {
    return this.api.post(`${this.basePath}/settings/maintenance`, { enabled, message });
  }

  // System Health
  getSystemHealth(): Observable<SystemHealthStatus> {
    return this.api.get<SystemHealthStatus>(`${this.basePath}/system/health`);
  }

  getErrorLogs(filters?: {
    level?: string;
    source?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }): Observable<ErrorLogResponse> {
    return this.api.get<ErrorLogResponse>(`${this.basePath}/system/errors`, filters);
  }

  // Notifications
  getNotifications(filters?: {
    type?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Observable<{ items: Notification[]; total: number }> {
    return this.api.get(`${this.basePath}/notifications`, filters);
  }

  broadcastNotification(data: BroadcastRequest): Observable<Notification> {
    return this.api.post<Notification>(`${this.basePath}/notifications/broadcast`, data);
  }

  previewSegment(filters: Record<string, any>): Observable<{ count: number; sample: string[] }> {
    return this.api.post(`${this.basePath}/notifications/preview-segment`, filters);
  }

  deleteNotification(notificationId: string): Observable<{ success: boolean }> {
    return this.api.delete(`${this.basePath}/notifications/${notificationId}`);
  }

  // RAG Stats
  getRAGStats(): Observable<RAGStats> {
    return this.api.get<RAGStats>(`${this.basePath}/rag/stats`);
  }
}
