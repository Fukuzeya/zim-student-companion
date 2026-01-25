import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ToastService } from '../../../core/services/toast.service';

interface Topic {
  id: string;
  name: string;
  description: string;
  order: number;
  questions_count: number;
  is_completed?: boolean;
}

interface Chapter {
  id: string;
  name: string;
  description: string;
  order: number;
  topics: Topic[];
  expanded?: boolean;
}

interface CurriculumSubject {
  id: string;
  name: string;
  code: string;
  level: string;
  chapters: Chapter[];
}

@Component({
  selector: 'app-curriculum',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <div class="header-info">
          <h1>Curriculum</h1>
          <p class="subtitle">Manage curriculum structure and learning paths</p>
        </div>
        <div class="header-actions">
          <button class="btn-secondary">
            <span class="material-symbols-outlined">download</span>
            Export
          </button>
          <button class="btn-primary" (click)="openAddChapter()">
            <span class="material-symbols-outlined">add</span>
            Add Chapter
          </button>
        </div>
      </div>

      <div class="content-layout">
        <div class="sidebar">
          <div class="sidebar-header">
            <h3>Subjects</h3>
          </div>
          <div class="subject-list">
            @for (subject of subjects(); track subject.id) {
              <button
                class="subject-item"
                [class.active]="selectedSubject()?.id === subject.id"
                (click)="selectSubject(subject)"
              >
                <div class="subject-icon">
                  <span class="material-symbols-outlined">menu_book</span>
                </div>
                <div class="subject-info">
                  <span class="name">{{ subject.name }}</span>
                  <span class="meta">{{ subject.chapters.length }} chapters</span>
                </div>
                <span class="level-badge" [class]="subject.level">{{ subject.level }}</span>
              </button>
            }
          </div>
        </div>

        <div class="main-content">
          @if (selectedSubject()) {
            <div class="subject-header-card">
              <div class="subject-title">
                <h2>{{ selectedSubject()!.name }}</h2>
                <span class="subject-code">{{ selectedSubject()!.code }}</span>
              </div>
              <div class="subject-stats">
                <div class="stat">
                  <span class="value">{{ selectedSubject()!.chapters.length }}</span>
                  <span class="label">Chapters</span>
                </div>
                <div class="stat">
                  <span class="value">{{ getTotalTopics() }}</span>
                  <span class="label">Topics</span>
                </div>
                <div class="stat">
                  <span class="value">{{ getTotalQuestions() }}</span>
                  <span class="label">Questions</span>
                </div>
              </div>
            </div>

            <div class="chapters-list">
              @for (chapter of selectedSubject()!.chapters; track chapter.id) {
                <div class="chapter-card" [class.expanded]="chapter.expanded">
                  <div class="chapter-header" (click)="toggleChapter(chapter)">
                    <div class="chapter-info">
                      <span class="chapter-order">{{ chapter.order }}</span>
                      <div class="chapter-details">
                        <h3>{{ chapter.name }}</h3>
                        <p>{{ chapter.description }}</p>
                      </div>
                    </div>
                    <div class="chapter-actions">
                      <span class="topics-count">{{ chapter.topics.length }} topics</span>
                      <button class="action-btn" (click)="editChapter(chapter, $event)">
                        <span class="material-symbols-outlined">edit</span>
                      </button>
                      <button class="action-btn" (click)="addTopic(chapter, $event)">
                        <span class="material-symbols-outlined">add</span>
                      </button>
                      <span class="material-symbols-outlined expand-icon">
                        {{ chapter.expanded ? 'expand_less' : 'expand_more' }}
                      </span>
                    </div>
                  </div>

                  @if (chapter.expanded) {
                    <div class="chapter-content">
                      <div class="topics-list">
                        @for (topic of chapter.topics; track topic.id) {
                          <div class="topic-item" draggable="true">
                            <div class="drag-handle">
                              <span class="material-symbols-outlined">drag_indicator</span>
                            </div>
                            <div class="topic-info">
                              <span class="topic-name">{{ topic.name }}</span>
                              <span class="topic-desc">{{ topic.description }}</span>
                            </div>
                            <div class="topic-meta">
                              <span class="questions-badge">
                                <span class="material-symbols-outlined">quiz</span>
                                {{ topic.questions_count }}
                              </span>
                            </div>
                            <div class="topic-actions">
                              <button class="action-btn" title="Edit">
                                <span class="material-symbols-outlined">edit</span>
                              </button>
                              <button class="action-btn danger" title="Delete">
                                <span class="material-symbols-outlined">delete</span>
                              </button>
                            </div>
                          </div>
                        } @empty {
                          <div class="empty-topics">
                            <p>No topics in this chapter yet.</p>
                            <button class="btn-small" (click)="addTopic(chapter, $event)">Add Topic</button>
                          </div>
                        }
                      </div>
                    </div>
                  }
                </div>
              } @empty {
                <div class="empty-state">
                  <span class="material-symbols-outlined">menu_book</span>
                  <h3>No chapters yet</h3>
                  <p>Add chapters to build the curriculum structure.</p>
                  <button class="btn-primary" (click)="openAddChapter()">Add Chapter</button>
                </div>
              }
            </div>
          } @else {
            <div class="empty-state">
              <span class="material-symbols-outlined">school</span>
              <h3>Select a Subject</h3>
              <p>Choose a subject from the sidebar to view and manage its curriculum.</p>
            </div>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .page-container {
      padding: 1.5rem;
      height: calc(100vh - 64px);
      display: flex;
      flex-direction: column;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      flex-shrink: 0;
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

      &:hover { background-color: #005238; }
    }

    .btn-secondary {
      background-color: var(--surface);
      color: var(--text-primary);
      border: 1px solid var(--border);

      &:hover { background-color: var(--hover); }
    }

    .btn-small {
      padding: 0.375rem 0.75rem;
      font-size: 0.75rem;
      font-weight: 500;
      background-color: var(--primary);
      color: white;
      border: none;
      border-radius: 0.375rem;
      cursor: pointer;

      &:hover { background-color: #005238; }
    }

    .content-layout {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 1.5rem;
      flex: 1;
      min-height: 0;

      @media (max-width: 1024px) {
        grid-template-columns: 1fr;
      }
    }

    .sidebar {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .sidebar-header {
      padding: 1rem;
      border-bottom: 1px solid var(--border);

      h3 {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    .subject-list {
      flex: 1;
      overflow-y: auto;
      padding: 0.5rem;
    }

    .subject-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      width: 100%;
      padding: 0.75rem;
      background: transparent;
      border: none;
      border-radius: 0.5rem;
      cursor: pointer;
      text-align: left;
      transition: all 0.15s ease;

      &:hover {
        background-color: var(--hover);
      }

      &.active {
        background-color: rgba(0, 102, 70, 0.1);

        .subject-icon {
          background-color: var(--primary);
          .material-symbols-outlined { color: white; }
        }
      }
    }

    .subject-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--background);
      border-radius: 0.5rem;
      flex-shrink: 0;

      .material-symbols-outlined {
        font-size: 1.25rem;
        color: var(--text-secondary);
      }
    }

    .subject-info {
      flex: 1;
      min-width: 0;

      .name {
        display: block;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .meta {
        font-size: 0.75rem;
        color: var(--text-tertiary);
      }
    }

    .level-badge {
      padding: 0.125rem 0.5rem;
      font-size: 0.625rem;
      font-weight: 600;
      border-radius: 9999px;
      text-transform: uppercase;
      flex-shrink: 0;

      &.o_level {
        background-color: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }

      &.a_level {
        background-color: rgba(139, 92, 246, 0.1);
        color: #8b5cf6;
      }
    }

    .main-content {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      overflow-y: auto;
    }

    .subject-header-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.5rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
    }

    .subject-title {
      h2 {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-primary);
      }

      .subject-code {
        font-size: 0.75rem;
        color: var(--text-tertiary);
        font-family: 'JetBrains Mono', monospace;
      }
    }

    .subject-stats {
      display: flex;
      gap: 2rem;
    }

    .stat {
      text-align: center;

      .value {
        display: block;
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--primary);
      }

      .label {
        font-size: 0.75rem;
        color: var(--text-secondary);
      }
    }

    .chapters-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .chapter-card {
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
      transition: all 0.15s ease;

      &.expanded {
        border-color: var(--primary);
      }
    }

    .chapter-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.25rem;
      cursor: pointer;
      transition: background-color 0.15s ease;

      &:hover {
        background-color: var(--hover);
      }
    }

    .chapter-info {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .chapter-order {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--primary);
      color: white;
      font-size: 0.875rem;
      font-weight: 600;
      border-radius: 0.5rem;
    }

    .chapter-details {
      h3 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
      }

      p {
        font-size: 0.75rem;
        color: var(--text-secondary);
      }
    }

    .chapter-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .topics-count {
      font-size: 0.75rem;
      color: var(--text-tertiary);
      padding: 0.25rem 0.75rem;
      background-color: var(--background);
      border-radius: 9999px;
    }

    .action-btn {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      border-radius: 0.375rem;
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
        font-size: 1.125rem;
      }
    }

    .expand-icon {
      color: var(--text-tertiary);
      transition: transform 0.15s ease;
    }

    .chapter-content {
      border-top: 1px solid var(--border);
      padding: 1rem;
      background-color: var(--background);
    }

    .topics-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .topic-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      background-color: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      cursor: grab;

      &:hover {
        border-color: var(--primary);
      }
    }

    .drag-handle {
      color: var(--text-tertiary);
      cursor: grab;

      .material-symbols-outlined {
        font-size: 1.25rem;
      }
    }

    .topic-info {
      flex: 1;

      .topic-name {
        display: block;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);
      }

      .topic-desc {
        font-size: 0.75rem;
        color: var(--text-secondary);
      }
    }

    .topic-meta {
      .questions-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.25rem 0.5rem;
        font-size: 0.75rem;
        background-color: var(--background);
        color: var(--text-secondary);
        border-radius: 0.25rem;

        .material-symbols-outlined {
          font-size: 0.875rem;
        }
      }
    }

    .topic-actions {
      display: flex;
      gap: 0.25rem;
    }

    .empty-topics {
      text-align: center;
      padding: 2rem;

      p {
        color: var(--text-secondary);
        margin-bottom: 1rem;
      }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
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
  `]
})
export class CurriculumComponent implements OnInit {
  private toastService = inject(ToastService);

  subjects = signal<CurriculumSubject[]>([]);
  selectedSubject = signal<CurriculumSubject | null>(null);

  ngOnInit(): void {
    this.loadSubjects();
  }

  loadSubjects(): void {
    const mockSubjects: CurriculumSubject[] = [
      {
        id: '1',
        name: 'Mathematics',
        code: 'MATH-001',
        level: 'o_level',
        chapters: [
          {
            id: 'c1',
            name: 'Algebra',
            description: 'Introduction to algebraic expressions and equations',
            order: 1,
            expanded: false,
            topics: [
              { id: 't1', name: 'Linear Equations', description: 'Solving linear equations in one variable', order: 1, questions_count: 45 },
              { id: 't2', name: 'Quadratic Equations', description: 'Solving quadratic equations using various methods', order: 2, questions_count: 52 },
              { id: 't3', name: 'Simultaneous Equations', description: 'Solving systems of linear equations', order: 3, questions_count: 38 }
            ]
          },
          {
            id: 'c2',
            name: 'Geometry',
            description: 'Study of shapes, sizes, and properties of figures',
            order: 2,
            expanded: false,
            topics: [
              { id: 't4', name: 'Angles and Lines', description: 'Properties of angles and parallel lines', order: 1, questions_count: 34 },
              { id: 't5', name: 'Triangles', description: 'Properties and theorems of triangles', order: 2, questions_count: 41 }
            ]
          }
        ]
      },
      {
        id: '2',
        name: 'Physics',
        code: 'PHY-001',
        level: 'o_level',
        chapters: [
          {
            id: 'c3',
            name: 'Mechanics',
            description: 'Study of motion and forces',
            order: 1,
            expanded: false,
            topics: [
              { id: 't6', name: 'Kinematics', description: 'Motion in one and two dimensions', order: 1, questions_count: 48 },
              { id: 't7', name: 'Dynamics', description: 'Newton\'s laws of motion', order: 2, questions_count: 55 }
            ]
          }
        ]
      },
      {
        id: '3',
        name: 'Advanced Mathematics',
        code: 'AMATH-001',
        level: 'a_level',
        chapters: []
      }
    ];

    this.subjects.set(mockSubjects);
    if (mockSubjects.length > 0) {
      this.selectedSubject.set(mockSubjects[0]);
    }
  }

  selectSubject(subject: CurriculumSubject): void {
    this.selectedSubject.set(subject);
  }

  toggleChapter(chapter: Chapter): void {
    chapter.expanded = !chapter.expanded;
  }

  getTotalTopics(): number {
    const subject = this.selectedSubject();
    if (!subject) return 0;
    return subject.chapters.reduce((sum, ch) => sum + ch.topics.length, 0);
  }

  getTotalQuestions(): number {
    const subject = this.selectedSubject();
    if (!subject) return 0;
    return subject.chapters.reduce((sum, ch) =>
      sum + ch.topics.reduce((tSum, t) => tSum + t.questions_count, 0), 0);
  }

  openAddChapter(): void {
    this.toastService.info('Add chapter modal would open here');
  }

  editChapter(chapter: Chapter, event: Event): void {
    event.stopPropagation();
    this.toastService.info(`Edit chapter: ${chapter.name}`);
  }

  addTopic(chapter: Chapter, event: Event): void {
    event.stopPropagation();
    this.toastService.info(`Add topic to: ${chapter.name}`);
  }
}
