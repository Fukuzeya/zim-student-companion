import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
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
  LiveStats,
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

  // Conversations
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

  getConversationMessages(
    conversationId: string,
    page?: number
  ): Observable<{ items: ConversationMessage[]; total: number }> {
    return this.api.get(`${this.basePath}/conversations/${conversationId}/messages`, { page });
  }

  searchConversations(query: string): Observable<ConversationListResponse> {
    return this.api.get<ConversationListResponse>(`${this.basePath}/conversations/search`, {
      query,
    });
  }

  getConversationAnalytics(filters?: {
    date_from?: string;
    date_to?: string;
  }): Observable<ConversationAnalytics> {
    return this.api.get<ConversationAnalytics>(
      `${this.basePath}/conversations/analytics`,
      filters
    );
  }

  interveneConversation(data: InterventionRequest): Observable<{ success: boolean }> {
    return this.api.post(`${this.basePath}/conversations/intervene`, data);
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
