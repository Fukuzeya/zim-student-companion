import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, catchError, throwError, BehaviorSubject } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  EmailLoginRequest,
  TokenResponse,
  UserProfileResponse,
  RefreshTokenRequest,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  RegisterRequest,
  MessageResponse,
} from '../models';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly apiUrl = `${environment.apiUrl}/auth`;
  private readonly TOKEN_KEY = 'access_token';
  private readonly REFRESH_TOKEN_KEY = 'refresh_token';
  private readonly USER_KEY = 'user';

  // Signals for reactive state
  private _currentUser = signal<UserProfileResponse | null>(null);
  private _isAuthenticated = signal<boolean>(false);
  private _isLoading = signal<boolean>(false);

  // Public computed signals
  readonly currentUser = computed(() => this._currentUser());
  readonly isAuthenticated = computed(() => this._isAuthenticated());
  readonly isLoading = computed(() => this._isLoading());
  readonly userRole = computed(() => this._currentUser()?.role || null);
  readonly isAdmin = computed(() => {
    const role = this._currentUser()?.role;
    return role === 'admin' || role === 'super_admin';
  });

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    this.initializeAuth();
  }

  private initializeAuth(): void {
    const token = this.getToken();
    const user = this.getStoredUser();
    if (token && user) {
      this._currentUser.set(user);
      this._isAuthenticated.set(true);
    }
  }

  login(credentials: EmailLoginRequest): Observable<TokenResponse> {
    this._isLoading.set(true);
    return this.http.post<TokenResponse>(`${this.apiUrl}/login`, credentials).pipe(
      tap((response) => this.handleAuthSuccess(response)),
      catchError((error) => {
        this._isLoading.set(false);
        return throwError(() => error);
      })
    );
  }

  register(data: RegisterRequest): Observable<TokenResponse> {
    this._isLoading.set(true);
    return this.http.post<TokenResponse>(`${this.apiUrl}/register`, data).pipe(
      tap((response) => this.handleAuthSuccess(response)),
      catchError((error) => {
        this._isLoading.set(false);
        return throwError(() => error);
      })
    );
  }

  refreshToken(): Observable<TokenResponse> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      return throwError(() => new Error('No refresh token available'));
    }

    const request: RefreshTokenRequest = { refresh_token: refreshToken };
    return this.http.post<TokenResponse>(`${this.apiUrl}/refresh`, request).pipe(
      tap((response) => {
        this.setToken(response.access_token);
        this.setRefreshToken(response.refresh_token);
      }),
      catchError((error) => {
        this.logout();
        return throwError(() => error);
      })
    );
  }

  logout(): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.apiUrl}/logout`, {}).pipe(
      tap(() => this.clearAuth()),
      catchError((error) => {
        this.clearAuth();
        return throwError(() => error);
      })
    );
  }

  getCurrentUser(): Observable<UserProfileResponse> {
    return this.http.get<UserProfileResponse>(`${this.apiUrl}/me`).pipe(
      tap((user) => {
        this._currentUser.set(user);
        this.setStoredUser(user);
      })
    );
  }

  updateProfile(data: Partial<UserProfileResponse>): Observable<UserProfileResponse> {
    return this.http.put<UserProfileResponse>(`${this.apiUrl}/me`, data).pipe(
      tap((user) => {
        this._currentUser.set(user);
        this.setStoredUser(user);
      })
    );
  }

  changePassword(data: ChangePasswordRequest): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.apiUrl}/change-password`, data);
  }

  forgotPassword(data: ForgotPasswordRequest): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.apiUrl}/forgot-password`, data);
  }

  resetPassword(data: ResetPasswordRequest): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.apiUrl}/reset-password`, data);
  }

  sendVerificationEmail(): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.apiUrl}/send-verification`, {});
  }

  verifyEmail(token: string): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.apiUrl}/verify-email`, { token });
  }

  private handleAuthSuccess(response: TokenResponse): void {
    this.setToken(response.access_token);
    this.setRefreshToken(response.refresh_token);
    this._isAuthenticated.set(true);
    this._isLoading.set(false);
    this.getCurrentUser().subscribe();
  }

  private clearAuth(): void {
    this.clearAuthState();
    this.router.navigate(['/auth/login']);
  }

  // Public method to clear auth state without redirect (used by interceptor)
  clearAuthState(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this._currentUser.set(null);
    this._isAuthenticated.set(false);
    this._isLoading.set(false);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private setToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  private setRefreshToken(token: string): void {
    localStorage.setItem(this.REFRESH_TOKEN_KEY, token);
  }

  private getStoredUser(): UserProfileResponse | null {
    const user = localStorage.getItem(this.USER_KEY);
    return user ? JSON.parse(user) : null;
  }

  private setStoredUser(user: UserProfileResponse): void {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  }
}
