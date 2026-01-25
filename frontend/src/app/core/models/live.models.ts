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

// Live Conversation from backend /conversations/live endpoint
export interface LiveConversation {
  id: string;
  student_id: string;
  student_name: string;
  student_grade?: string;
  subject?: string;
  topic?: string;
  last_message_at: string;
  last_message_preview?: string;
  message_count: number;
  status: ConversationStatus;
  context_type?: string;
  time_since_last_seconds?: number;
  sentiment?: 'positive' | 'neutral' | 'negative';
}

// Legacy Conversation interface for backward compatibility
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
  NEEDS_ATTENTION = 'needs_attention',
  ENDED = 'ended',
  FLAGGED = 'flagged'
}

export interface ConversationListResponse {
  items: Conversation[];
  total: number;
  page: number;
  page_size: number;
}

// Conversation Message from backend
export interface ConversationMessage {
  id: string;
  conversation_id?: string;
  role: MessageRole;
  content: string;
  context_type?: string;
  tokens_used?: number;
  response_time_ms?: number;
  sources_used?: number;
  created_at: string;
  timestamp?: string; // Alias for backward compatibility
  metadata?: Record<string, any>;
}

export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system'
}

// Conversation Detail from backend
export interface ConversationDetail {
  id: string;
  student_id: string;
  student_name: string;
  student_grade?: string;
  student_phone?: string;
  messages: ConversationMessage[];
  total_messages: number;
  total_tokens: number;
  avg_response_time_ms: number;
  subjects_discussed: string[];
  started_at: string;
  last_message_at: string;
}

// Pipeline Status from backend /conversations/pipeline
export interface ConversationPipeline {
  pending: number;
  processing: number;
  completed_today: number;
  failed_today: number;
  avg_processing_time_ms: number;
  queue_health: 'healthy' | 'degraded' | 'critical';
}

// Conversation Analytics from backend
export interface ConversationAnalytics {
  period_days: number;
  total_messages: number;
  unique_students: number;
  messages_per_student: number;
  by_context_type: Record<string, number>;
  by_subject: Record<string, number>;
  daily_volume: DailyVolume[];
  avg_tokens_per_message: number;
  // Legacy fields for backward compatibility
  total_conversations?: number;
  active_conversations?: number;
  avg_messages_per_conversation?: number;
  avg_session_duration?: number;
  total_tokens_used?: number;
  flagged_conversations?: number;
  sentiment_distribution?: SentimentDistribution;
  topic_distribution?: TopicDistribution[];
}

export interface DailyVolume {
  date: string;
  count: number;
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

// Intervention Request to backend
export interface InterventionRequest {
  student_id: string;
  message: string;
  intervention_type: InterventionType;
  notify_student?: boolean;
}

export enum InterventionType {
  GUIDANCE = 'guidance',
  CORRECTION = 'correction',
  ESCALATION = 'escalation'
}

// Intervention Response from backend
export interface InterventionResponse {
  success: boolean;
  intervention_id: string;
  student_id: string;
  intervention_type: string;
  notified: boolean;
  message: string;
}

// Search Result from backend
export interface ConversationSearchResult {
  id: string;
  student_id: string;
  student_name: string;
  role: string;
  content: string;
  context_type?: string;
  created_at: string;
  relevance_score?: number;
}

// Legacy InterventionAction for backward compatibility
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
