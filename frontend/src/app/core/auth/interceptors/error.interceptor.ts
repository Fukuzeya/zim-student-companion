import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError, EMPTY } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { ToastService } from '../../services/toast.service';

let isRefreshing = false;
let hasShownSessionExpiredToast = false;

export const errorInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const authService = inject(AuthService);
  const toastService = inject(ToastService);
  const router = inject(Router);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Handle 401 Unauthorized - session expired
      if (error.status === 401 && !req.url.includes('/auth/login') && !req.url.includes('/auth/refresh')) {
        if (!isRefreshing) {
          isRefreshing = true;
          return authService.refreshToken().pipe(
            switchMap(() => {
              isRefreshing = false;
              hasShownSessionExpiredToast = false;
              const token = authService.getToken();
              const cloned = req.clone({
                headers: req.headers.set('Authorization', `Bearer ${token}`),
              });
              return next(cloned);
            }),
            catchError((refreshError) => {
              isRefreshing = false;
              // Show session expired toast only once
              if (!hasShownSessionExpiredToast) {
                hasShownSessionExpiredToast = true;
                toastService.warning('Session Expired', 'Your session has expired. Please log in again.');
                // Store the current URL to redirect back after login
                const currentUrl = router.url;
                if (currentUrl && !currentUrl.includes('/auth/')) {
                  sessionStorage.setItem('redirectUrl', currentUrl);
                }
              }
              // Clear auth state and redirect to login
              authService.clearAuthState();
              router.navigate(['/auth/login']);
              return throwError(() => refreshError);
            })
          );
        } else {
          // Already refreshing, wait for it to complete
          return EMPTY;
        }
      }

      // Handle other errors
      if (error.status === 403) {
        toastService.error('Access Denied', 'You do not have permission to perform this action.');
      } else if (error.status === 404) {
        // Don't show toast for 404 on API calls - let components handle it
        // toastService.error('Not Found', 'The requested resource was not found.');
      } else if (error.status === 422) {
        const message = error.error?.detail || 'Validation error occurred.';
        toastService.error('Validation Error', message);
      } else if (error.status === 500) {
        toastService.error('Server Error', 'An unexpected error occurred. Please try again later.');
      } else if (error.status === 0) {
        toastService.error('Connection Error', 'Unable to connect to the server. Please check your internet connection.');
      }

      return throwError(() => error);
    })
  );
};
