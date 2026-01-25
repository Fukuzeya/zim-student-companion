import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import {
  CompetitionListResponse,
  Competition,
  CreateCompetitionRequest,
  CompetitionLeaderboard,
  DisqualifyRequest,
  ConversationListResponse,
  Conversation,
  ConversationMessage,
  ConversationAnalytics,
  InterventionRequest,
  InterventionResponse,
  LiveStats,
  LiveConversation,
  ConversationDetail,
  ConversationPipeline,
  ConversationSearchResult,
} from '../models';

@Injectable({
  providedIn: 'root',
})
export class LiveService {
  private readonly basePath = '/admin';

  constructor(private api: ApiService) {}

  // Competitions
  getCompetitions(filters?: {
    status?: string;
    subject?: string;
    page?: number;
    page_size?: number;
  }): Observable<CompetitionListResponse> {
    return this.api.get<CompetitionListResponse>(`${this.basePath}/competitions`, filters);
  }

  getCompetitionById(competitionId: string): Observable<Competition> {
    return this.api.get<Competition>(`${this.basePath}/competitions/${competitionId}`);
  }

  createCompetition(data: CreateCompetitionRequest): Observable<Competition> {
    return this.api.post<Competition>(`${this.basePath}/competitions`, data);
  }

  updateCompetition(competitionId: string, data: Partial<Competition>): Observable<Competition> {
    return this.api.put<Competition>(`${this.basePath}/competitions/${competitionId}`, data);
  }

  getLeaderboard(competitionId: string): Observable<CompetitionLeaderboard> {
    return this.api.get<CompetitionLeaderboard>(
      `${this.basePath}/competitions/${competitionId}/leaderboard`
    );
  }

  disqualifyParticipant(competitionId: string, data: DisqualifyRequest): Observable<void> {
    return this.api.post(`${this.basePath}/competitions/${competitionId}/disqualify`, data);
  }

  exportCompetitionResults(competitionId: string): Observable<Blob> {
    return this.api.download(`${this.basePath}/competitions/${competitionId}/export`);
  }

  finalizeCompetition(competitionId: string): Observable<Competition> {
    return this.api.post<Competition>(`${this.basePath}/competitions/${competitionId}/finalize`, {});
  }

  getLiveCompetitionStatus(competitionId: string): Observable<{
    status: string;
    participants: number;
    avg_score: number;
    time_remaining: number;
  }> {
    return this.api.get(`${this.basePath}/competitions/${competitionId}/live`);
  }

  // =====================
  // Live Conversations API
  // =====================

  /**
   * Get active/live conversations (last 30 minutes)
   * Backend: GET /admin/conversations/live
   */
  getLiveConversations(filters?: {
    status?: string;
    subject_id?: string;
    limit?: number;
  }): Observable<LiveConversation[]> {
    return this.api.get<LiveConversation[]>(`${this.basePath}/conversations/live`, filters).pipe(
      map(conversations => {
        // Normalize response - ensure array
        if (!Array.isArray(conversations)) {
          return [];
        }
        return conversations;
      })
    );
  }

  /**
   * Get conversation processing pipeline status
   * Backend: GET /admin/conversations/pipeline
   */
  getPipelineStatus(): Observable<ConversationPipeline> {
    return this.api.get<ConversationPipeline>(`${this.basePath}/conversations/pipeline`);
  }

  /**
   * Get detailed conversation with messages
   * Backend: GET /admin/conversations/{conversation_id}
   */
  getConversationDetail(conversationId: string): Observable<ConversationDetail> {
    return this.api.get<ConversationDetail>(`${this.basePath}/conversations/${conversationId}`);
  }

  /**
   * Get just the messages for a conversation
   * Backend: GET /admin/conversations/{conversation_id}/messages
   */
  getConversationMessages(
    conversationId: string,
    limit?: number
  ): Observable<ConversationMessage[]> {
    const params: Record<string, any> = {};
    if (limit) params['limit'] = limit;
    return this.api.get<ConversationMessage[]>(
      `${this.basePath}/conversations/${conversationId}/messages`,
      params
    );
  }

  /**
   * Send admin intervention to a student
   * Backend: POST /admin/conversations/{student_id}/intervene
   */
  interveneConversation(
    studentId: string,
    message: string,
    interventionType: string = 'guidance',
    notifyStudent: boolean = true
  ): Observable<InterventionResponse> {
    return this.api.post<InterventionResponse>(
      `${this.basePath}/conversations/${studentId}/intervene`,
      {
        message,
        intervention_type: interventionType,
        notify_student: notifyStudent
      }
    );
  }

  /**
   * Get conversation analytics for a period
   * Backend: GET /admin/conversations/analytics
   */
  getConversationAnalytics(days: number = 7): Observable<ConversationAnalytics> {
    return this.api.get<ConversationAnalytics>(
      `${this.basePath}/conversations/analytics`,
      { days }
    );
  }

  /**
   * Search conversations by content
   * Backend: GET /admin/conversations/search
   */
  searchConversations(filters: {
    query?: string;
    student_id?: string;
    date_from?: string;
    date_to?: string;
    limit?: number;
  }): Observable<ConversationSearchResult[]> {
    return this.api.get<ConversationSearchResult[]>(
      `${this.basePath}/conversations/search`,
      filters
    );
  }

  // =====================
  // Legacy/Compatibility Methods
  // =====================

  getConversations(filters?: {
    status?: string;
    subject?: string;
    is_flagged?: boolean;
    search?: string;
    page?: number;
    page_size?: number;
  }): Observable<ConversationListResponse> {
    return this.api.get<ConversationListResponse>(`${this.basePath}/conversations`, filters);
  }

  getConversationById(conversationId: string): Observable<Conversation> {
    return this.api.get<Conversation>(`${this.basePath}/conversations/${conversationId}`);
  }

  flagConversation(
    conversationId: string,
    reason: string
  ): Observable<Conversation> {
    return this.api.post<Conversation>(
      `${this.basePath}/conversations/${conversationId}/flag`,
      { reason }
    );
  }

  // Live Stats
  getLiveStats(): Observable<LiveStats> {
    return this.api.get<LiveStats>(`${this.basePath}/live/stats`);
  }
}
