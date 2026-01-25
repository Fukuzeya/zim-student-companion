import { Component, Input, Output, EventEmitter, TemplateRef, ContentChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LoadingSpinnerComponent } from '../loading-spinner/loading-spinner.component';

export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  template?: TemplateRef<any>;
}

export interface PageEvent {
  page: number;
  pageSize: number;
}

export interface SortEvent {
  column: string;
  direction: 'asc' | 'desc';
}

@Component({
  selector: 'app-data-table',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  template: `
    <div class="data-table-wrapper">
      <!-- Header with search and actions -->
      @if (showHeader) {
        <div class="table-header">
          <div class="table-search">
            @if (showSearch) {
              <div class="search-input-wrapper">
                <span class="material-symbols-outlined">search</span>
                <input
                  type="text"
                  [placeholder]="searchPlaceholder"
                  [(ngModel)]="searchQuery"
                  (ngModelChange)="onSearch($event)"
                />
              </div>
            }
          </div>
          <div class="table-actions">
            <ng-content select="[tableActions]"></ng-content>
          </div>
        </div>
      }

      <!-- Table container -->
      <div class="table-container" [class.loading]="loading">
        @if (loading) {
          <div class="loading-overlay">
            <app-loading-spinner [size]="1.5" />
          </div>
        }

        <table>
          <thead>
            <tr>
              @if (selectable) {
                <th class="checkbox-cell">
                  <input
                    type="checkbox"
                    [checked]="allSelected"
                    [indeterminate]="someSelected"
                    (change)="toggleSelectAll($event)"
                  />
                </th>
              }
              @for (column of columns; track column.key) {
                <th
                  [style.width]="column.width"
                  [style.text-align]="column.align || 'left'"
                  [class.sortable]="column.sortable"
                  (click)="column.sortable ? onSort(column.key) : null"
                >
                  <div class="th-content">
                    {{ column.label }}
                    @if (column.sortable) {
                      <span class="sort-icon material-symbols-outlined">
                        @if (sortColumn === column.key) {
                          {{ sortDirection === 'asc' ? 'arrow_upward' : 'arrow_downward' }}
                        } @else {
                          unfold_more
                        }
                      </span>
                    }
                  </div>
                </th>
              }
              @if (showActions) {
                <th class="actions-cell">Actions</th>
              }
            </tr>
          </thead>
          <tbody>
            @if (data.length === 0 && !loading) {
              <tr>
                <td [attr.colspan]="totalColumns" class="empty-cell">
                  <div class="empty-state">
                    <span class="material-symbols-outlined empty-icon">{{ emptyIcon }}</span>
                    <p class="empty-title">{{ emptyTitle }}</p>
                    <p class="empty-description">{{ emptyDescription }}</p>
                  </div>
                </td>
              </tr>
            } @else {
              @for (row of data; track trackBy ? trackBy(row) : $index; let i = $index) {
                <tr [class.selected]="isSelected(row)" (click)="onRowClick(row)">
                  @if (selectable) {
                    <td class="checkbox-cell" (click)="$event.stopPropagation()">
                      <input
                        type="checkbox"
                        [checked]="isSelected(row)"
                        (change)="toggleSelect(row)"
                      />
                    </td>
                  }
                  @for (column of columns; track column.key) {
                    <td [style.text-align]="column.align || 'left'">
                      @if (column.template) {
                        <ng-container *ngTemplateOutlet="column.template; context: { $implicit: row, column: column }"></ng-container>
                      } @else {
                        {{ getNestedValue(row, column.key) }}
                      }
                    </td>
                  }
                  @if (showActions) {
                    <td class="actions-cell" (click)="$event.stopPropagation()">
                      <ng-content select="[rowActions]"></ng-content>
                    </td>
                  }
                </tr>
              }
            }
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      @if (showPagination && total > 0) {
        <div class="table-pagination">
          <div class="pagination-info">
            <span>Rows per page:</span>
            <select [(ngModel)]="pageSize" (ngModelChange)="onPageSizeChange($event)">
              @for (size of pageSizeOptions; track size) {
                <option [value]="size">{{ size }}</option>
              }
            </select>
          </div>
          <div class="pagination-status">
            Showing {{ startIndex + 1 }}-{{ endIndex }} of {{ total }}
          </div>
          <div class="pagination-controls">
            <button
              class="btn-icon"
              [disabled]="page === 1"
              (click)="onPageChange(page - 1)"
            >
              <span class="material-symbols-outlined">chevron_left</span>
            </button>
            <button
              class="btn-icon"
              [disabled]="page >= totalPages"
              (click)="onPageChange(page + 1)"
            >
              <span class="material-symbols-outlined">chevron_right</span>
            </button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .data-table-wrapper {
      display: flex;
      flex-direction: column;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }

    .table-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem;
      border-bottom: 1px solid var(--border);
      gap: 1rem;
      flex-wrap: wrap;
    }

    .search-input-wrapper {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background-color: var(--background);
      border-radius: 0.5rem;
      padding: 0 0.75rem;
      min-width: 250px;

      .material-symbols-outlined {
        color: var(--text-muted);
        font-size: 1.25rem;
      }

      input {
        flex: 1;
        border: none;
        background: transparent;
        padding: 0.5rem 0;

        &:focus {
          outline: none;
          box-shadow: none;
        }
      }
    }

    .table-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .table-container {
      position: relative;
      overflow-x: auto;

      &.loading {
        min-height: 200px;
      }
    }

    .loading-overlay {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: rgba(var(--background-rgb), 0.7);
      z-index: 10;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    th {
      padding: 0.75rem 1rem;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      background-color: var(--background);
      border-bottom: 1px solid var(--border);
      white-space: nowrap;

      &.sortable {
        cursor: pointer;

        &:hover {
          color: var(--text-primary);
        }
      }
    }

    .th-content {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
    }

    .sort-icon {
      font-size: 1rem;
      opacity: 0.5;
    }

    td {
      padding: 0.75rem 1rem;
      font-size: 0.875rem;
      color: var(--text-primary);
      border-bottom: 1px solid var(--border);
    }

    tbody tr {
      transition: background-color 0.15s ease;

      &:hover {
        background-color: var(--background);
      }

      &.selected {
        background-color: rgba(0, 102, 70, 0.05);
      }
    }

    .checkbox-cell {
      width: 3rem;
      text-align: center;

      input[type="checkbox"] {
        width: 1rem;
        height: 1rem;
        cursor: pointer;
      }
    }

    .actions-cell {
      width: 8rem;
      text-align: right;
    }

    .empty-cell {
      padding: 3rem 1rem;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
    }

    .empty-icon {
      font-size: 3rem;
      color: var(--text-muted);
      margin-bottom: 1rem;
    }

    .empty-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 0.25rem;
    }

    .empty-description {
      font-size: 0.875rem;
      color: var(--text-muted);
    }

    .table-pagination {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1rem;
      border-top: 1px solid var(--border);
      background-color: var(--background);
      gap: 1rem;
      flex-wrap: wrap;
    }

    .pagination-info {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      color: var(--text-muted);

      select {
        padding: 0.25rem 0.5rem;
        font-size: 0.875rem;
        background: transparent;
        border: none;
        color: var(--text-primary);
        cursor: pointer;
      }
    }

    .pagination-status {
      font-size: 0.875rem;
      color: var(--text-muted);
    }

    .pagination-controls {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .btn-icon {
      padding: 0.25rem;
      background: transparent;
      border: none;
      color: var(--text-primary);
      cursor: pointer;
      border-radius: 0.25rem;
      transition: background-color 0.15s ease;

      &:hover:not(:disabled) {
        background-color: var(--surface);
      }

      &:disabled {
        color: var(--text-muted);
        cursor: not-allowed;
      }

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }
  `]
})
export class DataTableComponent<T> {
  @Input() columns: TableColumn[] = [];
  @Input() data: T[] = [];
  @Input() loading = false;
  @Input() selectable = false;
  @Input() showActions = false;
  @Input() showHeader = true;
  @Input() showSearch = true;
  @Input() showPagination = true;
  @Input() searchPlaceholder = 'Search...';
  @Input() emptyIcon = 'inbox';
  @Input() emptyTitle = 'No data found';
  @Input() emptyDescription = 'There are no items to display.';
  @Input() page = 1;
  @Input() pageSize = 10;
  @Input() total = 0;
  @Input() pageSizeOptions = [10, 25, 50, 100];
  @Input() trackBy?: (item: T) => any;

  @Output() searchChange = new EventEmitter<string>();
  @Output() sortChange = new EventEmitter<SortEvent>();
  @Output() pageChange = new EventEmitter<PageEvent>();
  @Output() selectionChange = new EventEmitter<T[]>();
  @Output() rowClick = new EventEmitter<T>();

  searchQuery = '';
  sortColumn = '';
  sortDirection: 'asc' | 'desc' = 'asc';
  selectedItems: Set<T> = new Set();

  get totalColumns(): number {
    return this.columns.length + (this.selectable ? 1 : 0) + (this.showActions ? 1 : 0);
  }

  get totalPages(): number {
    return Math.ceil(this.total / this.pageSize);
  }

  get startIndex(): number {
    return (this.page - 1) * this.pageSize;
  }

  get endIndex(): number {
    return Math.min(this.startIndex + this.pageSize, this.total);
  }

  get allSelected(): boolean {
    return this.data.length > 0 && this.selectedItems.size === this.data.length;
  }

  get someSelected(): boolean {
    return this.selectedItems.size > 0 && this.selectedItems.size < this.data.length;
  }

  onSearch(query: string): void {
    this.searchChange.emit(query);
  }

  onSort(column: string): void {
    if (this.sortColumn === column) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortColumn = column;
      this.sortDirection = 'asc';
    }
    this.sortChange.emit({ column: this.sortColumn, direction: this.sortDirection });
  }

  onPageChange(page: number): void {
    this.page = page;
    this.pageChange.emit({ page: this.page, pageSize: this.pageSize });
  }

  onPageSizeChange(size: number): void {
    this.pageSize = size;
    this.page = 1;
    this.pageChange.emit({ page: this.page, pageSize: this.pageSize });
  }

  isSelected(item: T): boolean {
    return this.selectedItems.has(item);
  }

  toggleSelect(item: T): void {
    if (this.selectedItems.has(item)) {
      this.selectedItems.delete(item);
    } else {
      this.selectedItems.add(item);
    }
    this.selectionChange.emit(Array.from(this.selectedItems));
  }

  toggleSelectAll(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      this.data.forEach(item => this.selectedItems.add(item));
    } else {
      this.selectedItems.clear();
    }
    this.selectionChange.emit(Array.from(this.selectedItems));
  }

  onRowClick(row: T): void {
    this.rowClick.emit(row);
  }

  getNestedValue(obj: any, path: string): any {
    return path.split('.').reduce((o, p) => o?.[p], obj);
  }
}
