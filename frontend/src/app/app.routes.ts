import { Routes } from '@angular/router';
import { authGuard } from './core/auth/guards/auth.guard';
import { guestGuard } from './core/auth/guards/guest.guard';

export const routes: Routes = [
  // Redirect root to dashboard or login based on auth state
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full'
  },

  // Auth routes (no layout, guest only)
  {
    path: 'auth',
    canActivate: [guestGuard],
    children: [
      {
        path: '',
        redirectTo: 'login',
        pathMatch: 'full'
      },
      {
        path: 'login',
        loadComponent: () =>
          import('./features/auth/login/login.component').then(m => m.LoginComponent),
        title: 'Login - EduBot Admin'
      },
      {
        path: 'register',
        loadComponent: () =>
          import('./features/auth/register/register.component').then(m => m.RegisterComponent),
        title: 'Register - EduBot Admin'
      },
      {
        path: 'forgot-password',
        loadComponent: () =>
          import('./features/auth/forgot-password/forgot-password.component').then(
            m => m.ForgotPasswordComponent
          ),
        title: 'Forgot Password - EduBot Admin'
      },
      {
        path: 'reset-password',
        loadComponent: () =>
          import('./features/auth/reset-password/reset-password.component').then(
            m => m.ResetPasswordComponent
          ),
        title: 'Reset Password - EduBot Admin'
      }
    ]
  },

  // Protected routes (with main layout)
  {
    path: '',
    loadComponent: () =>
      import('./layout/main-layout/main-layout.component').then(m => m.MainLayoutComponent),
    canActivate: [authGuard],
    children: [
      // Dashboard
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
        title: 'Dashboard - EduBot Admin'
      },

      // Users Management
      {
        path: 'users',
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./features/users/users-list/users-list.component').then(
                m => m.UsersListComponent
              ),
            title: 'Users - EduBot Admin'
          },
          {
            path: 'admins',
            loadComponent: () =>
              import('./features/users/admins/admins-list.component').then(
                m => m.AdminsListComponent
              ),
            title: 'Administrators - EduBot Admin'
          },
          {
            path: ':id',
            loadComponent: () =>
              import('./features/users/user-detail/user-detail.component').then(
                m => m.UserDetailComponent
              ),
            title: 'User Details - EduBot Admin'
          }
        ]
      },

      // Students
      {
        path: 'students',
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./features/students/students-list/students-list.component').then(
                m => m.StudentsListComponent
              ),
            title: 'Students - EduBot Admin'
          },
          {
            path: ':id',
            loadComponent: () =>
              import('./features/students/student-detail/student-detail.component').then(
                m => m.StudentDetailComponent
              ),
            title: 'Student Details - EduBot Admin'
          }
        ]
      },

      // Content Management
      {
        path: 'content',
        children: [
          {
            path: '',
            redirectTo: 'questions',
            pathMatch: 'full'
          },
          {
            path: 'questions',
            loadComponent: () =>
              import('./features/content/questions/questions-list.component').then(
                m => m.QuestionsListComponent
              ),
            title: 'Questions - EduBot Admin'
          },
          {
            path: 'subjects',
            loadComponent: () =>
              import('./features/content/subjects/subjects-list.component').then(
                m => m.SubjectsListComponent
              ),
            title: 'Subjects - EduBot Admin'
          },
          {
            path: 'documents',
            loadComponent: () =>
              import('./features/content/documents/rag-documents.component').then(
                m => m.RagDocumentsComponent
              ),
            title: 'Documents - EduBot Admin'
          },
          {
            path: 'curriculum',
            loadComponent: () =>
              import('./features/content/curriculum/curriculum.component').then(
                m => m.CurriculumComponent
              ),
            title: 'Curriculum - EduBot Admin'
          }
        ]
      },

      // Payments & Finance
      {
        path: 'payments',
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./features/payments/payments-list/payments-list.component').then(
                m => m.PaymentsListComponent
              ),
            title: 'Payments - EduBot Admin'
          },
          {
            path: 'subscriptions',
            loadComponent: () =>
              import('./features/payments/subscriptions/subscriptions-list.component').then(
                m => m.SubscriptionsListComponent
              ),
            title: 'Subscriptions - EduBot Admin'
          },
          {
            path: 'plans',
            loadComponent: () =>
              import('./features/payments/plans/plans-list.component').then(
                m => m.PlansListComponent
              ),
            title: 'Plans - EduBot Admin'
          },
          {
            path: ':id',
            loadComponent: () =>
              import('./features/payments/payment-detail/payment-detail.component').then(
                m => m.PaymentDetailComponent
              ),
            title: 'Payment Details - EduBot Admin'
          }
        ]
      },

      // Live Operations
      {
        path: 'live',
        children: [
          {
            path: '',
            redirectTo: 'conversations',
            pathMatch: 'full'
          },
          {
            path: 'conversations',
            loadComponent: () =>
              import('./features/live/conversations/live-conversations.component').then(
                m => m.LiveConversationsComponent
              ),
            title: 'Live Conversations - EduBot Admin'
          },
          {
            path: 'competitions',
            loadComponent: () =>
              import('./features/live/competitions/competitions-list.component').then(
                m => m.CompetitionsListComponent
              ),
            title: 'Competitions - EduBot Admin'
          }
        ]
      },

      // Analytics
      {
        path: 'analytics',
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./features/analytics/analytics-dashboard.component').then(
                m => m.AnalyticsDashboardComponent
              ),
            title: 'Analytics - EduBot Admin'
          },
          {
            path: 'engagement',
            loadComponent: () =>
              import('./features/analytics/engagement/engagement-analytics.component').then(
                m => m.EngagementAnalyticsComponent
              ),
            title: 'Engagement Analytics - EduBot Admin'
          },
          {
            path: 'revenue',
            loadComponent: () =>
              import('./features/analytics/revenue/revenue-analytics.component').then(
                m => m.RevenueAnalyticsComponent
              ),
            title: 'Revenue Analytics - EduBot Admin'
          }
        ]
      },

      // System & Settings
      {
        path: 'system',
        children: [
          {
            path: '',
            redirectTo: 'settings',
            pathMatch: 'full'
          },
          {
            path: 'settings',
            loadComponent: () =>
              import('./features/system/settings/settings.component').then(
                m => m.SettingsComponent
              ),
            title: 'Settings - EduBot Admin'
          },
          {
            path: 'audit',
            loadComponent: () =>
              import('./features/system/audit-log/audit-log.component').then(
                m => m.AuditLogComponent
              ),
            title: 'Audit Log - EduBot Admin'
          },
          {
            path: 'health',
            loadComponent: () =>
              import('./features/system/health/system-health.component').then(
                m => m.SystemHealthComponent
              ),
            title: 'System Health - EduBot Admin'
          }
        ]
      },

      // Notifications
      {
        path: 'notifications',
        loadComponent: () =>
          import('./features/notifications/notifications.component').then(
            m => m.NotificationsComponent
          ),
        title: 'Notifications - EduBot Admin'
      }
    ]
  },

  // Catch-all redirect
  {
    path: '**',
    redirectTo: 'dashboard'
  }
];
