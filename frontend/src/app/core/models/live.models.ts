// Live operations models based on OpenAPI specification

export interface Competition {
  id: string;
  name: string;
  description: string;
  subject: string;
  education_level: string;
  grade?: string;
  type: CompetitionType;
  status: CompetitionStatus;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  max_participants?: number;
  current_participants: number;
  entry_fee?: number;
  prize_pool?: number;
  rules: string[];
  created_by: string;
  created_at: string;
}

export enum CompetitionType {
  QUIZ = 'quiz',
  SPEED_ROUND = 'speed_round',
  CHALLENGE = 'challenge',
  TOURNAMENT = 'tournament'
}

export enum CompetitionStatus {
  DRAFT = 'draft',
  SCHEDULED = 'scheduled',
  LIVE = 'live',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled'
}

export interface CompetitionListResponse {
  items: Competition[];
  total: number;
  page: number;
  page_size: number;
}

export interface CompetitionLeaderboard {
  competition_id: string;
  entries: LeaderboardEntry[];
  total_participants: number;
  last_updated: string;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  user_name: string;
  school?: string;
  score: number;
  correct_answers: number;
  total_questions: number;
  time_taken: number;
  finished_at?: string;
}

export interface CreateCompetitionRequest {
  name: string;
  description: string;
  subject: string;
  education_level: string;
  grade?: string;
  type: CompetitionType;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  max_participants?: number;
  entry_fee?: number;
  prize_pool?: number;
  rules: string[];
  question_ids: string[];
}

export interface DisqualifyRequest {
  user_id: string;
  reason: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  subject?: string;
  topic?: string;
  status: ConversationStatus;
  message_count: number;
  started_at: string;
  last_message_at: string;
  is_flagged: boolean;
  flag_reason?: string;
  sentiment_score?: number;
}

export enum ConversationStatus {
  ACTIVE = 'active',
  IDLE = 'idle',
  ENDED = 'ended',
  FLAGGED = 'flagged'
}

export interface ConversationListResponse {
  items: Conversation[];
  total: number;
  page: number;
  page_size: number;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  tokens_used?: number;
  metadata?: Record<string, any>;
}

export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system'
}

export interface ConversationAnalytics {
  total_conversations: number;
  active_conversations: number;
  avg_messages_per_conversation: number;
  avg_session_duration: number;
  total_tokens_used: number;
  flagged_conversations: number;
  sentiment_distribution: SentimentDistribution;
  topic_distribution: TopicDistribution[];
}

export interface SentimentDistribution {
  positive: number;
  neutral: number;
  negative: number;
}

export interface TopicDistribution {
  topic: string;
  count: number;
  percentage: number;
}

export interface InterventionRequest {
  conversation_id: string;
  message: string;
  action?: InterventionAction;
}

export enum InterventionAction {
  SEND_MESSAGE = 'send_message',
  END_CONVERSATION = 'end_conversation',
  FLAG_CONVERSATION = 'flag_conversation',
  ESCALATE = 'escalate'
}

export interface LiveStats {
  active_users: number;
  active_conversations: number;
  active_competitions: number;
  messages_per_minute: number;
  tokens_per_minute: number;
  avg_response_time: number;
}
