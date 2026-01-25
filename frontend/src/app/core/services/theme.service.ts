import { Injectable, signal, computed, effect } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { inject } from '@angular/core';

export type Theme = 'light' | 'dark' | 'system';

@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  private document = inject(DOCUMENT);
  private readonly THEME_KEY = 'edubot-admin-theme';

  // Signals for reactive state
  private _theme = signal<Theme>(this.getStoredTheme());
  private _isDark = signal<boolean>(false);

  // Public computed signals
  readonly theme = computed(() => this._theme());
  readonly isDark = computed(() => this._isDark());

  constructor() {
    // Initialize theme
    this.applyTheme(this._theme());

    // Listen for system theme changes
    this.listenToSystemTheme();

    // Effect to persist theme changes
    effect(() => {
      const theme = this._theme();
      localStorage.setItem(this.THEME_KEY, theme);
      this.applyTheme(theme);
    });
  }

  setTheme(theme: Theme): void {
    this._theme.set(theme);
  }

  toggleTheme(): void {
    const currentTheme = this._theme();
    if (currentTheme === 'dark') {
      this._theme.set('light');
    } else {
      this._theme.set('dark');
    }
  }

  private getStoredTheme(): Theme {
    const stored = localStorage.getItem(this.THEME_KEY) as Theme | null;
    return stored || 'dark'; // Default to dark theme as per design
  }

  private applyTheme(theme: Theme): void {
    const isDark = this.shouldUseDarkMode(theme);
    this._isDark.set(isDark);

    const htmlElement = this.document.documentElement;
    if (isDark) {
      htmlElement.classList.add('dark');
      htmlElement.classList.remove('light');
    } else {
      htmlElement.classList.add('light');
      htmlElement.classList.remove('dark');
    }
  }

  private shouldUseDarkMode(theme: Theme): boolean {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return theme === 'dark';
  }

  private listenToSystemTheme(): void {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', () => {
      if (this._theme() === 'system') {
        this.applyTheme('system');
      }
    });
  }
}
