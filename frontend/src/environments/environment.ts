export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1',
  wsUrl: 'ws://localhost:8000/ws',
  tokenRefreshThreshold: 5 * 60 * 1000, // 5 minutes before expiry
  defaultPageSize: 50,
  maxPageSize: 100,
  debounceTime: 300,
  toastDuration: 5000,
};