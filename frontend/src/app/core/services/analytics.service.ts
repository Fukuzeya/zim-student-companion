import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import {
  EngagementAnalytics,
  LearningAnalytics,
  RevenueAnalytics,
  CustomReportRequest,
  AnalyticsFilters,
} from '../models';

@Injectable({
  providedIn: 'root',
})
export class AnalyticsService {
  private readonly basePath = '/admin/analytics';

  constructor(private api: ApiService) {}

  getEngagementAnalytics(filters?: AnalyticsFilters): Observable<EngagementAnalytics> {
    return this.api.get<EngagementAnalytics>(`${this.basePath}/engagement`, filters);
  }

  getLearningAnalytics(filters?: AnalyticsFilters): Observable<LearningAnalytics> {
    return this.api.get<LearningAnalytics>(`${this.basePath}/learning`, filters);
  }

  getRevenueAnalytics(filters?: AnalyticsFilters): Observable<RevenueAnalytics> {
    return this.api.get<RevenueAnalytics>(`${this.basePath}/revenue`, filters);
  }

  generateCustomReport(request: CustomReportRequest): Observable<Blob> {
    return this.api.download(`${this.basePath}/custom`, request as any);
  }
}
