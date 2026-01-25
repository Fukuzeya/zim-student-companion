// Authentication models based on OpenAPI specification

export interface EmailLoginRequest {
  email: string;
  password: string;
}

export interface PhoneLoginRequest {
  phone_number: string;
}

export interface RegisterRequest {
  email: string;
  phone_number: string;
  password: string;
  role?: UserRole;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  role: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface OtpRequest {
  phone_number: string;
}

export interface OtpVerifyRequest {
  phone_number: string;
  otp: string;
}

export interface UserProfileResponse {
  id: string;
  phone_number: string;
  email: string;
  role: UserRole;
  subscription_tier: SubscriptionTier;
  subscription_expires_at: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_active: string;
  student?: StudentProfile;
}

export interface StudentProfile {
  id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  school_name?: string;
  district?: string;
  province?: string;
  education_level: string;
  grade: string;
  subjects: string[];
  total_xp: number;
  level?: number;
  daily_goal_minutes?: number;
  preferred_language?: string;
}

export interface UserUpdate {
  email?: string;
  phone_number?: string;
  role?: UserRole;
  subscription_tier?: SubscriptionTier;
  subscription_expires_at?: string;
  is_active?: boolean;
  is_verified?: boolean;
}

export enum UserRole {
  STUDENT = 'student',
  TEACHER = 'teacher',
  PARENT = 'parent',
  ADMIN = 'admin',
  SUPER_ADMIN = 'super_admin'
}

export enum SubscriptionTier {
  FREE = 'free',
  BASIC = 'basic',
  PREMIUM = 'premium',
  FAMILY = 'family',
  SCHOOL = 'school',
  ENTERPRISE = 'enterprise'
}

export interface MessageResponse {
  message: string;
  success?: boolean;
}
