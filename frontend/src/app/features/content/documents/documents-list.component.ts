import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ContentService } from '../../../core/services/content.service';
import { ToastService } from '../../../core/services/toast.service';

interface Document {
  id: string;
  title: string;
  description: string;
  subject: string;
  type: 'pdf' | 'doc' | 'video' | 'image';
  file_size: number;
  downloads: number;
  created_at: string;
  is_public: boolean;
}

@Component({
  selector: 'app-documents-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>Documents</h1>
          <p class="subtitle">Manage learning materials and resources</p>
        </div>
        <div class="header-actions">
          <button class="btn-secondary">
            <span class="material-symbols-outlined">folder</span>
            Manage Folders
          </button>
          <button class="btn-primary" (click)="openUploadModal()">
            <span class="material-symbols-outlined">upload</span>
            Upload Document
          </button>
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon">
            <span class="material-symbols-outlined">description</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ totalDocuments() }}</span>
            <span class="stat-label">Total Documents</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon pdf">
            <span class="material-symbols-outlined">picture_as_pdf</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ pdfCount() }}</span>
            <span class="stat-label">PDF Files</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon video">
            <span class="material-symbols-outlined">play_circle</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ videoCount() }}</span>
            <span class="stat-label">Videos</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon downloads">
            <span class="material-symbols-outlined">download</span>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ totalDownloads() }}</span>
            <span class="stat-label">Total Downloads</span>
          </div>
        </div>
      </div>

      <div class="filters-bar">
        <div class="search-box">
          <span class="material-symbols-outlined">search</span>
          <input
            type="text"
            placeholder="Search documents..."
            [(ngModel)]="searchQuery"
            (input)="onSearch()"
          />
        </div>
        <div class="filter-group">
          <select [(ngModel)]="selectedSubject" (change)="applyFilters()">
            <option value="">All Subjects</option>
            <option value="Mathematics">Mathematics</option>
            <option value="English">English</option>
            <option value="Physics">Physics</option>
            <option value="Chemistry">Chemistry</option>
            <option value="Biology">Biology</option>
          </select>
          <select [(ngModel)]="selectedType" (change)="applyFilters()">
            <option value="">All Types</option>
            <option value="pdf">PDF</option>
            <option value="doc">Document</option>
            <option value="video">Video</option>
            <option value="image">Image</option>
          </select>
        </div>
        <div class="view-toggle">
          <button [class.active]="viewMode() === 'grid'" (click)="setViewMode('grid')">
            <span class="material-symbols-outlined">grid_view</span>
          </button>
          <button [class.active]="viewMode() === 'list'" (click)="setViewMode('list')">
            <span class="material-symbols-outlined">view_list</span>
          </button>
        </div>
      </div>

      @if (isLoading()) {
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Loading documents...</p>
        </div>
      } @else {
        @if (viewMode() === 'grid') {
          <div class="documents-grid">
            @for (doc of filteredDocuments(); track doc.id) {
              <div class="document-card">
                <div class="card-preview" [class]="doc.type">
                  <span class="material-symbols-outlined">{{ getTypeIcon(doc.type) }}</span>
                </div>
                <div class="card-body">
                  <h3>{{ doc.title }}</h3>
                  <p class="description">{{ doc.description }}</p>
                  <div class="card-meta">
                    <span class="subject">{{ doc.subject }}</span>
                    <span class="size">{{ formatSize(doc.file_size) }}</span>
                  </div>
                </div>
                <div class="card-footer">
                  <div class="downloads">
                    <span class="material-symbols-outlined">download</span>
                    {{ doc.downloads }}
                  </div>
                  <div class="actions">
                    <button class="action-btn" title="Preview">
                      <span class="material-symbols-outlined">visibility</span>
                    </button>
                    <button class="action-btn" title="Download">
                      <span class="material-symbols-outlined">download</span>
                    </button>
                    <button class="action-btn" title="Edit">
                      <span class="material-symbols-outlined">edit</span>
                    </button>
                    <button class="action-btn danger" (click)="deleteDocument(doc)" title="Delete">
                      <span class="material-symbols-outlined">delete</span>
                    </button>
                  </div>
                </div>
              </div>
            } @empty {
              <div class="empty-state">
                <span class="material-symbols-outlined">folder_open</span>
                <h3>No documents found</h3>
                <p>Upload your first document to get started.</p>
                <button class="btn-primary" (click)="openUploadModal()">Upload Document</button>
              </div>
            }
          </div>
        } @else {
          <div class="card">
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Subject</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Downloads</th>
                    <th>Uploaded</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (doc of filteredDocuments(); track doc.id) {
                    <tr>
                      <td>
                        <div class="doc-info">
                          <div class="doc-icon" [class]="doc.type">
                            <span class="material-symbols-outlined">{{ getTypeIcon(doc.type) }}</span>
                          </div>
                          <div class="doc-details">
                            <span class="title">{{ doc.title }}</span>
                            <span class="desc">{{ doc.description }}</span>
                          </div>
                        </div>
                      </td>
                      <td>{{ doc.subject }}</td>
                      <td>
                        <span class="type-badge" [class]="doc.type">{{ doc.type | uppercase }}</span>
                      </td>
                      <td>{{ formatSize(doc.file_size) }}</td>
                      <td>{{ doc.downloads }}</td>
                      <td>{{ doc.created_at | date:'mediumDate' }}</td>
                      <td>
                        <div class="actions">
                          <button class="action-btn" title="Preview">
                            <span class="material-symbols-outlined">visibility</span>
                          </button>
                          <button class="action-btn" title="Download">
                            <span class="material-symbols-outlined">download</span>
                          </button>
                          <button class="action-btn danger" (click)="deleteDocument(doc)">
                            <span class="material-symbols-outlined">delete</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .page-container {
      padding: 1.5rem;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .header-info {
      h1 {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
      }

      .subtitle {
        font-size: 0.875rem;
        color: var(--text-secondary);
      }
    }

    .header-actions {
      display: flex;
      gap: 0.75rem;
    }

    .btn-primary, .btn-secondary {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      font-size: 0.875rem;
      font-weight: 500;
      border-radius: 0.5rem;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .btn-primary {
      background-color: var(--primary);
      color: white;
      border: none;

      &:hover {
        background-color: #005238;
      }
    }

    .btn-secondary {
      background-color: var(--surface);
      color: var(--text-primary);
      border: 1px solid var(--border);

      &:hover {
        background-color: var(--hover);
      }
    }

    .stats-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 1.5rem;

      @media (max-width: 1024px) {
        grid-template-columns: repeat(2, 1fr);
      }

      @media (max-width: 640px) {
        grid-template-columns: 1fr;
      }
    }

    .stat-card {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1.25rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: rgba(0, 102, 70, 0.1);
      border-radius: 0.5rem;

      .material-symbols-outlined {
        font-size: 1.5rem;
        color: var(--primary);
      }

      &.pdf {
        background-color: rgba(239, 68, 68, 0.1);
        .material-symbols-outlined { color: #ef4444; }
      }

      &.video {
        background-color: rgba(139, 92, 246, 0.1);
        .material-symbols-outlined { color: #8b5cf6; }
      }

      &.downloads {
        background-color: rgba(59, 130, 246, 0.1);
        .material-symbols-outlined { color: #3b82f6; }
      }
    }

    .stat-info {
      display: flex;
      flex-direction: column;

      .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
      }

      .stat-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
      }
    }

    .filters-bar {
      display: flex;
      gap: 1rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
      align-items: center;
    }

    .search-box {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex: 1;
      min-width: 250px;
      padding: 0.5rem 1rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;

      input {
        flex: 1;
        border: none;
        background: transparent;
        color: var(--text-primary);
        font-size: 0.875rem;

        &:focus { outline: none; }
      }
    }

    .filter-group {
      display: flex;
      gap: 0.5rem;

      select {
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        color: var(--text-primary);
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        cursor: pointer;
      }
    }

    .view-toggle {
      display: flex;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      overflow: hidden;

      button {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: transparent;
        border: none;
        color: var(--text-tertiary);
        cursor: pointer;

        &:hover {
          background-color: var(--hover);
        }

        &.active {
          background-color: var(--primary);
          color: white;
        }
      }
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 4rem;

      .spinner {
        width: 2.5rem;
        height: 2.5rem;
        border: 3px solid var(--border);
        border-top-color: var(--primary);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        margin-bottom: 1rem;
      }
    }

    .documents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1.5rem;
    }

    .document-card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
      transition: all 0.15s ease;

      &:hover {
        border-color: var(--primary);
      }
    }

    .card-preview {
      height: 120px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--background);

      .material-symbols-outlined {
        font-size: 3rem;
        color: var(--text-tertiary);
      }

      &.pdf {
        background-color: rgba(239, 68, 68, 0.1);
        .material-symbols-outlined { color: #ef4444; }
      }

      &.doc {
        background-color: rgba(59, 130, 246, 0.1);
        .material-symbols-outlined { color: #3b82f6; }
      }

      &.video {
        background-color: rgba(139, 92, 246, 0.1);
        .material-symbols-outlined { color: #8b5cf6; }
      }

      &.image {
        background-color: rgba(16, 185, 129, 0.1);
        .material-symbols-outlined { color: #10b981; }
      }
    }

    .card-body {
      padding: 1rem;

      h3 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .description {
        font-size: 0.75rem;
        color: var(--text-secondary);
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin-bottom: 0.75rem;
      }

      .card-meta {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;

        .subject {
          color: var(--primary);
          font-weight: 500;
        }

        .size {
          color: var(--text-tertiary);
        }
      }
    }

    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      background-color: var(--background);
      border-top: 1px solid var(--border);
    }

    .downloads {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      font-size: 0.75rem;
      color: var(--text-secondary);

      .material-symbols-outlined {
        font-size: 1rem;
      }
    }

    .actions {
      display: flex;
      gap: 0.25rem;
    }

    .action-btn {
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      border-radius: 0.25rem;
      color: var(--text-tertiary);
      cursor: pointer;

      &:hover {
        background-color: var(--hover);
        color: var(--text-primary);
      }

      &.danger:hover {
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }

      .material-symbols-outlined {
        font-size: 1rem;
      }
    }

    .card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }

    .table-container {
      overflow-x: auto;
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;

      th, td {
        padding: 1rem;
        text-align: left;
        border-bottom: 1px solid var(--border);
      }

      th {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        background-color: var(--background);
      }

      td {
        font-size: 0.875rem;
        color: var(--text-primary);
      }
    }

    .doc-info {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .doc-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 0.5rem;
      background-color: var(--background);

      &.pdf { background-color: rgba(239, 68, 68, 0.1); .material-symbols-outlined { color: #ef4444; } }
      &.doc { background-color: rgba(59, 130, 246, 0.1); .material-symbols-outlined { color: #3b82f6; } }
      &.video { background-color: rgba(139, 92, 246, 0.1); .material-symbols-outlined { color: #8b5cf6; } }
      &.image { background-color: rgba(16, 185, 129, 0.1); .material-symbols-outlined { color: #10b981; } }
    }

    .doc-details {
      display: flex;
      flex-direction: column;

      .title {
        font-weight: 500;
      }

      .desc {
        font-size: 0.75rem;
        color: var(--text-secondary);
      }
    }

    .type-badge {
      display: inline-flex;
      padding: 0.25rem 0.5rem;
      font-size: 0.625rem;
      font-weight: 600;
      border-radius: 0.25rem;

      &.pdf { background-color: rgba(239, 68, 68, 0.1); color: #ef4444; }
      &.doc { background-color: rgba(59, 130, 246, 0.1); color: #3b82f6; }
      &.video { background-color: rgba(139, 92, 246, 0.1); color: #8b5cf6; }
      &.image { background-color: rgba(16, 185, 129, 0.1); color: #10b981; }
    }

    .empty-state {
      grid-column: 1 / -1;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 4rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;

      .material-symbols-outlined {
        font-size: 4rem;
        color: var(--text-tertiary);
        margin-bottom: 1rem;
      }

      h3 {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
      }

      p {
        color: var(--text-secondary);
        margin-bottom: 1.5rem;
      }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class DocumentsListComponent implements OnInit {
  private contentService = inject(ContentService);
  private toastService = inject(ToastService);

  documents = signal<Document[]>([]);
  filteredDocuments = signal<Document[]>([]);
  isLoading = signal(true);
  viewMode = signal<'grid' | 'list'>('grid');

  totalDocuments = signal(0);
  pdfCount = signal(0);
  videoCount = signal(0);
  totalDownloads = signal(0);

  searchQuery = '';
  selectedSubject = '';
  selectedType = '';

  ngOnInit(): void {
    this.loadDocuments();
  }

  loadDocuments(): void {
    this.isLoading.set(true);
    const filters = {
      subject: this.selectedSubject || undefined,
      page: 1,
      page_size: 50
    };

    this.contentService.getDocuments(filters).subscribe({
      next: (response) => {
        if (response && response.items && Array.isArray(response.items)) {
          const docs = response.items.map((d: any) => ({
            id: d.id,
            title: d.title || d.filename || 'Untitled',
            description: d.description || '',
            subject: d.subject || 'General',
            type: this.getDocType(d.mime_type || d.type),
            file_size: d.file_size || 0,
            downloads: d.downloads || 0,
            created_at: d.created_at,
            is_public: d.is_public ?? true
          }));
          this.documents.set(docs);
          this.filteredDocuments.set(docs);
          this.updateDocStats(docs);
        } else {
          this.setMockDocuments();
        }
        this.isLoading.set(false);
      },
      error: () => {
        this.setMockDocuments();
        this.isLoading.set(false);
      }
    });
  }

  getDocType(mimeType: string): 'pdf' | 'doc' | 'video' | 'image' {
    if (mimeType?.includes('pdf')) return 'pdf';
    if (mimeType?.includes('video')) return 'video';
    if (mimeType?.includes('image')) return 'image';
    return 'doc';
  }

  setMockDocuments(): void {
    const mockDocs: Document[] = [
      { id: '1', title: 'Mathematics Past Paper 2023', description: 'O Level Mathematics past paper', subject: 'Mathematics', type: 'pdf', file_size: 2500000, downloads: 234, created_at: '2024-01-15', is_public: true },
      { id: '2', title: 'Physics Formulas Guide', description: 'Comprehensive physics formulas', subject: 'Physics', type: 'pdf', file_size: 1800000, downloads: 567, created_at: '2024-01-12', is_public: true },
      { id: '3', title: 'Chemistry Lab Manual', description: 'Laboratory experiment instructions', subject: 'Chemistry', type: 'doc', file_size: 3200000, downloads: 189, created_at: '2024-01-10', is_public: true },
      { id: '4', title: 'Biology Cell Structure', description: 'Video of cell structure', subject: 'Biology', type: 'video', file_size: 45000000, downloads: 423, created_at: '2024-01-08', is_public: true }
    ];
    this.documents.set(mockDocs);
    this.filteredDocuments.set(mockDocs);
    this.updateDocStats(mockDocs);
  }

  updateDocStats(docs: Document[]): void {
    this.totalDocuments.set(docs.length);
    this.pdfCount.set(docs.filter(d => d.type === 'pdf').length);
    this.videoCount.set(docs.filter(d => d.type === 'video').length);
    this.totalDownloads.set(docs.reduce((sum, d) => sum + d.downloads, 0));
  }

  getTypeIcon(type: string): string {
    const icons: Record<string, string> = {
      pdf: 'picture_as_pdf',
      doc: 'description',
      video: 'play_circle',
      image: 'image'
    };
    return icons[type] || 'description';
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  setViewMode(mode: 'grid' | 'list'): void {
    this.viewMode.set(mode);
  }

  onSearch(): void {
    this.applyFilters();
  }

  applyFilters(): void {
    let filtered = this.documents();

    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(d =>
        d.title.toLowerCase().includes(query) ||
        d.description.toLowerCase().includes(query)
      );
    }

    if (this.selectedSubject) {
      filtered = filtered.filter(d => d.subject === this.selectedSubject);
    }

    if (this.selectedType) {
      filtered = filtered.filter(d => d.type === this.selectedType);
    }

    this.filteredDocuments.set(filtered);
  }

  openUploadModal(): void {
    this.toastService.info('Upload modal would open here');
  }

  deleteDocument(doc: Document): void {
    if (confirm(`Delete "${doc.title}"? This action cannot be undone.`)) {
      this.documents.update(docs => docs.filter(d => d.id !== doc.id));
      this.applyFilters();
      this.toastService.success('Document deleted');
    }
  }
}
