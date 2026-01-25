# ============================================================================
# Admin Content Management Service
# ============================================================================
"""
Service layer for curriculum content management.
Handles subjects, topics, questions, documents, and RAG system administration.
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime
from uuid import UUID, uuid4
from pathlib import Path
import logging
import json
import aiofiles
import os

from app.models.curriculum import Subject, Topic, Question, LearningObjective
from app.models.practice import QuestionAttempt

logger = logging.getLogger(__name__)


class ContentManagementService:
    """
    Content management service for curriculum administration.
    
    Provides:
    - CRUD operations for subjects, topics, and questions
    - Bulk import/export capabilities
    - Question bank analytics
    - Document management and RAG integration
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # Subject Management
    # =========================================================================
    async def list_subjects(
        self,
        education_level: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        List all subjects with optional filtering.
        
        Args:
            education_level: Filter by education level
            is_active: Filter by active status
            
        Returns:
            List of subjects with topic counts
        """
        query = select(Subject)
        
        conditions = []
        if education_level:
            conditions.append(Subject.education_level == education_level)
        if is_active is not None:
            conditions.append(Subject.is_active == is_active)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Subject.name)
        result = await self.db.execute(query)
        subjects = result.scalars().all()
        
        # Get topic counts for each subject
        subject_list = []
        for subject in subjects:
            topic_count = await self.db.execute(
                select(func.count(Topic.id)).where(Topic.subject_id == subject.id)
            )
            question_count = await self.db.execute(
                select(func.count(Question.id)).where(Question.subject_id == subject.id)
            )
            
            subject_list.append({
                "id": str(subject.id),
                "name": subject.name,
                "code": subject.code,
                "education_level": subject.education_level,
                "description": subject.description,
                "icon": subject.icon,
                "color": subject.color,
                "is_active": subject.is_active,
                "topic_count": topic_count.scalar() or 0,
                "question_count": question_count.scalar() or 0,
                "created_at": subject.created_at.isoformat()
            })
        
        return subject_list
    
    async def create_subject(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new subject.
        
        Args:
            data: Subject creation data
            
        Returns:
            Created subject data
        """
        subject = Subject(
            name=data["name"],
            code=data["code"],
            education_level=data["education_level"],
            description=data.get("description"),
            icon=data.get("icon"),
            color=data.get("color")
        )
        
        self.db.add(subject)
        await self.db.commit()
        await self.db.refresh(subject)
        
        logger.info(f"Created subject: {subject.name} ({subject.code})")
        
        return {
            "id": str(subject.id),
            "name": subject.name,
            "code": subject.code,
            "message": "Subject created successfully"
        }
    
    async def update_subject(self, subject_id: UUID, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing subject"""
        result = await self.db.execute(select(Subject).where(Subject.id == subject_id))
        subject = result.scalar_one_or_none()
        
        if not subject:
            return None
        
        for field, value in updates.items():
            if value is not None and hasattr(subject, field):
                setattr(subject, field, value)
        
        await self.db.commit()
        await self.db.refresh(subject)
        
        return {"id": str(subject.id), "message": "Subject updated successfully"}
    
    async def delete_subject(self, subject_id: UUID) -> bool:
        """Delete a subject (soft delete by deactivating)"""
        result = await self.db.execute(
            update(Subject).where(Subject.id == subject_id).values(is_active=False)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def list_subjects_paginated(
        self,
        search: Optional[str] = None,
        education_level: Optional[str] = None,
        is_active: Optional[bool] = None,
        has_topics: Optional[bool] = None,
        has_questions: Optional[bool] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        List subjects with filtering, sorting, and pagination.
        Uses optimized subqueries to avoid N+1 problem.
        """
        # Subqueries for counts (avoid N+1)
        topic_count_subq = (
            select(func.count(Topic.id))
            .where(Topic.subject_id == Subject.id)
            .correlate(Subject)
            .scalar_subquery()
        )

        question_count_subq = (
            select(func.count(Question.id))
            .where(Question.subject_id == Subject.id)
            .correlate(Subject)
            .scalar_subquery()
        )

        # Build main query with counts
        query = select(
            Subject,
            topic_count_subq.label('topic_count'),
            question_count_subq.label('question_count')
        )

        # Apply filters
        conditions = []

        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Subject.name.ilike(search_term),
                    Subject.code.ilike(search_term),
                    Subject.description.ilike(search_term)
                )
            )

        if education_level:
            conditions.append(Subject.education_level == education_level)

        if is_active is not None:
            conditions.append(Subject.is_active == is_active)

        if has_topics is not None:
            if has_topics:
                conditions.append(topic_count_subq > 0)
            else:
                conditions.append(topic_count_subq == 0)

        if has_questions is not None:
            if has_questions:
                conditions.append(question_count_subq > 0)
            else:
                conditions.append(question_count_subq == 0)

        if conditions:
            query = query.where(and_(*conditions))

        # Count total for pagination
        count_query = select(func.count(Subject.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_column_map = {
            "name": Subject.name,
            "code": Subject.code,
            "created_at": Subject.created_at,
            "education_level": Subject.education_level,
            "topic_count": topic_count_subq,
            "question_count": question_count_subq
        }
        sort_column = sort_column_map.get(sort_by, Subject.name)

        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute
        result = await self.db.execute(query)
        rows = result.all()

        # Format response
        subjects = []
        for row in rows:
            subject = row[0]
            t_count = row[1] or 0
            q_count = row[2] or 0

            subjects.append({
                "id": subject.id,
                "name": subject.name,
                "code": subject.code,
                "education_level": subject.education_level,
                "description": subject.description,
                "icon": subject.icon,
                "color": subject.color,
                "is_active": subject.is_active,
                "topic_count": t_count,
                "question_count": q_count,
                "document_count": 0,
                "created_at": subject.created_at,
                "updated_at": None
            })

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "subjects": subjects,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }

    async def get_subject_detail(self, subject_id: UUID) -> Optional[Dict[str, Any]]:
        """Get detailed subject information including topics and coverage"""
        result = await self.db.execute(
            select(Subject).where(Subject.id == subject_id)
        )
        subject = result.scalar_one_or_none()

        if not subject:
            return None

        # Get topics
        topics_result = await self.db.execute(
            select(Topic)
            .where(Topic.subject_id == subject_id)
            .where(Topic.is_active == True)
            .order_by(Topic.order_index)
        )
        topics = topics_result.scalars().all()

        # Get topic count and question count
        topic_count = len(topics)
        question_count_result = await self.db.execute(
            select(func.count(Question.id)).where(Question.subject_id == subject_id)
        )
        question_count = question_count_result.scalar() or 0

        # Get difficulty distribution
        difficulty_result = await self.db.execute(
            select(Question.difficulty, func.count(Question.id))
            .where(Question.subject_id == subject_id)
            .group_by(Question.difficulty)
        )
        difficulty_distribution = {row[0]: row[1] for row in difficulty_result.all()}

        # Calculate coverage (topics with questions / total topics)
        topics_with_questions = 0
        topic_data = []
        for topic in topics:
            q_count_result = await self.db.execute(
                select(func.count(Question.id)).where(Question.topic_id == topic.id)
            )
            q_count = q_count_result.scalar() or 0
            if q_count > 0:
                topics_with_questions += 1

            topic_data.append({
                "id": str(topic.id),
                "name": topic.name,
                "grade": topic.grade,
                "order_index": topic.order_index,
                "question_count": q_count
            })

        coverage = (topics_with_questions / topic_count * 100) if topic_count > 0 else 0

        return {
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "education_level": subject.education_level,
            "description": subject.description,
            "icon": subject.icon,
            "color": subject.color,
            "is_active": subject.is_active,
            "topic_count": topic_count,
            "question_count": question_count,
            "document_count": 0,
            "created_at": subject.created_at,
            "updated_at": None,
            "topics": topic_data,
            "coverage_percentage": round(coverage, 1),
            "difficulty_distribution": difficulty_distribution,
            "recent_activity": []
        }

    async def get_subject_stats(self) -> Dict[str, Any]:
        """Get comprehensive subject statistics"""
        from datetime import timedelta

        # Total counts
        total_result = await self.db.execute(select(func.count(Subject.id)))
        total = total_result.scalar() or 0

        active_result = await self.db.execute(
            select(func.count(Subject.id)).where(Subject.is_active == True)
        )
        active = active_result.scalar() or 0

        # By education level
        level_result = await self.db.execute(
            select(Subject.education_level, func.count(Subject.id))
            .group_by(Subject.education_level)
        )
        by_level = {row[0] or "unknown": row[1] for row in level_result.all()}

        # Topics and questions totals
        topics_result = await self.db.execute(select(func.count(Topic.id)))
        total_topics = topics_result.scalar() or 0

        questions_result = await self.db.execute(select(func.count(Question.id)))
        total_questions = questions_result.scalar() or 0

        # Subjects without content
        subjects_with_topics = await self.db.execute(
            select(func.count(func.distinct(Topic.subject_id)))
        )
        with_topics = subjects_with_topics.scalar() or 0
        no_topics = total - with_topics

        subjects_with_questions = await self.db.execute(
            select(func.count(func.distinct(Question.subject_id)))
        )
        with_questions = subjects_with_questions.scalar() or 0
        no_questions = total - with_questions

        # Recently created (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_result = await self.db.execute(
            select(func.count(Subject.id))
            .where(Subject.created_at >= thirty_days_ago)
        )
        recent = recent_result.scalar() or 0

        # Most popular by question count
        popular_result = await self.db.execute(
            select(Subject.name, func.count(Question.id).label('q_count'))
            .join(Question, Question.subject_id == Subject.id)
            .group_by(Subject.name)
            .order_by(func.count(Question.id).desc())
            .limit(5)
        )
        most_popular = [
            {"name": row[0], "question_count": row[1]}
            for row in popular_result.all()
        ]

        return {
            "total_subjects": total,
            "active_subjects": active,
            "inactive_subjects": total - active,
            "by_education_level": by_level,
            "total_topics": total_topics,
            "total_questions": total_questions,
            "subjects_without_topics": no_topics,
            "subjects_without_questions": no_questions,
            "avg_topics_per_subject": round(total_topics / total, 1) if total > 0 else 0,
            "avg_questions_per_subject": round(total_questions / total, 1) if total > 0 else 0,
            "recently_created": recent,
            "most_popular": most_popular
        }

    async def bulk_subject_action(
        self,
        subject_ids: List[UUID],
        action: str,
        admin_id: UUID
    ) -> Dict[str, Any]:
        """Perform bulk actions on subjects"""
        successful = 0
        failed = 0
        errors = []

        for subject_id in subject_ids:
            try:
                if action == "activate":
                    await self.db.execute(
                        update(Subject)
                        .where(Subject.id == subject_id)
                        .values(is_active=True)
                    )
                    successful += 1
                elif action == "deactivate":
                    await self.db.execute(
                        update(Subject)
                        .where(Subject.id == subject_id)
                        .values(is_active=False)
                    )
                    successful += 1
                elif action == "delete":
                    # Check dependencies first
                    deps = await self.check_subject_dependencies(subject_id)
                    if deps["can_delete"]:
                        await self.db.execute(
                            update(Subject)
                            .where(Subject.id == subject_id)
                            .values(is_active=False)
                        )
                        successful += 1
                    else:
                        failed += 1
                        errors.append({
                            "subject_id": str(subject_id),
                            "error": f"Cannot delete: {', '.join(deps['warnings'])}"
                        })
            except Exception as e:
                failed += 1
                errors.append({
                    "subject_id": str(subject_id),
                    "error": str(e)
                })

        await self.db.commit()

        return {
            "total_requested": len(subject_ids),
            "successful": successful,
            "failed": failed,
            "errors": errors[:10],
            "message": f"Successfully processed {successful} of {len(subject_ids)} subjects"
        }

    async def check_subject_dependencies(self, subject_id: UUID) -> Dict[str, Any]:
        """Check dependencies before deletion"""
        result = await self.db.execute(
            select(Subject).where(Subject.id == subject_id)
        )
        subject = result.scalar_one_or_none()

        if not subject:
            return {
                "subject_id": subject_id,
                "subject_name": "Not Found",
                "topic_count": 0,
                "question_count": 0,
                "document_count": 0,
                "active_students_count": 0,
                "can_delete": False,
                "warnings": ["Subject not found"]
            }

        # Count dependencies
        topic_count_result = await self.db.execute(
            select(func.count(Topic.id)).where(Topic.subject_id == subject_id)
        )
        topic_count = topic_count_result.scalar() or 0

        question_count_result = await self.db.execute(
            select(func.count(Question.id)).where(Question.subject_id == subject_id)
        )
        question_count = question_count_result.scalar() or 0

        document_count = 0
        active_students = 0

        warnings = []
        can_delete = True

        if topic_count > 0:
            warnings.append(f"{topic_count} topics will be orphaned")
        if question_count > 0:
            warnings.append(f"{question_count} questions will be orphaned")
            can_delete = False
        if active_students > 0:
            warnings.append(f"{active_students} students are currently studying this subject")
            can_delete = False

        return {
            "subject_id": subject_id,
            "subject_name": subject.name,
            "topic_count": topic_count,
            "question_count": question_count,
            "document_count": document_count,
            "active_students_count": active_students,
            "can_delete": can_delete,
            "warnings": warnings
        }

    async def export_subjects(
        self,
        format: str,
        subject_ids: Optional[List[UUID]] = None,
        include_topics: bool = False,
        include_questions: bool = False
    ) -> Dict[str, Any]:
        """Export subjects to file"""
        import csv
        import io
        from datetime import timedelta

        # Get subjects
        query = select(Subject)
        if subject_ids:
            query = query.where(Subject.id.in_(subject_ids))
        query = query.order_by(Subject.name)

        result = await self.db.execute(query)
        subjects = result.scalars().all()

        # Prepare data
        export_data = []
        for subject in subjects:
            row = {
                "id": str(subject.id),
                "name": subject.name,
                "code": subject.code,
                "education_level": subject.education_level,
                "description": subject.description or "",
                "icon": subject.icon or "",
                "color": subject.color or "",
                "is_active": subject.is_active,
                "created_at": subject.created_at.isoformat()
            }

            if include_topics:
                topics_result = await self.db.execute(
                    select(Topic).where(Topic.subject_id == subject.id)
                )
                row["topics"] = [
                    {"id": str(t.id), "name": t.name, "grade": t.grade}
                    for t in topics_result.scalars().all()
                ]

            export_data.append(row)

        # Generate file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            filename = f"subjects_export_{timestamp}.json"
            content = json.dumps(export_data, indent=2, default=str)
        elif format == "csv":
            filename = f"subjects_export_{timestamp}.csv"
            output = io.StringIO()
            if export_data:
                # Flatten for CSV (exclude nested topics)
                flat_data = []
                for item in export_data:
                    flat_item = {k: v for k, v in item.items() if k != "topics"}
                    if include_topics and "topics" in item:
                        flat_item["topic_count"] = len(item["topics"])
                    flat_data.append(flat_item)
                writer = csv.DictWriter(output, fieldnames=flat_data[0].keys())
                writer.writeheader()
                writer.writerows(flat_data)
            content = output.getvalue()
        else:
            filename = f"subjects_export_{timestamp}.xlsx"
            content = ""

        return {
            "filename": filename,
            "file_size": len(content.encode('utf-8') if isinstance(content, str) else content),
            "record_count": len(export_data),
            "download_url": f"/api/v1/admin/subjects/export/{filename}",
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }

    # =========================================================================
    # Topic Management
    # =========================================================================
    async def list_topics(
        self,
        subject_id: Optional[UUID] = None,
        grade: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        List topics with optional filtering.
        
        Args:
            subject_id: Filter by subject
            grade: Filter by grade
            is_active: Filter by active status
            
        Returns:
            Hierarchical list of topics with question counts
        """
        query = select(Topic).options(selectinload(Topic.subject))
        
        conditions = []
        if subject_id:
            conditions.append(Topic.subject_id == subject_id)
        if grade:
            conditions.append(Topic.grade == grade)
        if is_active is not None:
            conditions.append(Topic.is_active == is_active)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Topic.order_index)
        result = await self.db.execute(query)
        topics = result.scalars().all()
        
        topic_list = []
        for topic in topics:
            question_count = await self.db.execute(
                select(func.count(Question.id)).where(Question.topic_id == topic.id)
            )
            
            topic_list.append({
                "id": str(topic.id),
                "subject_id": str(topic.subject_id),
                "subject_name": topic.subject.name if topic.subject else None,
                "parent_topic_id": str(topic.parent_topic_id) if topic.parent_topic_id else None,
                "name": topic.name,
                "description": topic.description,
                "grade": topic.grade,
                "syllabus_reference": topic.syllabus_reference,
                "order_index": topic.order_index,
                "estimated_hours": float(topic.estimated_hours) if topic.estimated_hours else None,
                "is_active": topic.is_active,
                "question_count": question_count.scalar() or 0,
                "created_at": topic.created_at.isoformat()
            })
        
        return topic_list
    
    async def create_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new topic"""
        topic = Topic(
            subject_id=data["subject_id"],
            parent_topic_id=data.get("parent_topic_id"),
            name=data["name"],
            description=data.get("description"),
            grade=data["grade"],
            syllabus_reference=data.get("syllabus_reference"),
            order_index=data.get("order_index", 0),
            estimated_hours=data.get("estimated_hours")
        )
        
        self.db.add(topic)
        await self.db.commit()
        await self.db.refresh(topic)
        
        logger.info(f"Created topic: {topic.name}")
        
        return {"id": str(topic.id), "message": "Topic created successfully"}
    
    async def update_topic(self, topic_id: UUID, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing topic"""
        result = await self.db.execute(select(Topic).where(Topic.id == topic_id))
        topic = result.scalar_one_or_none()
        
        if not topic:
            return None
        
        for field, value in updates.items():
            if value is not None and hasattr(topic, field):
                setattr(topic, field, value)
        
        await self.db.commit()
        return {"id": str(topic.id), "message": "Topic updated successfully"}
    
    async def reorder_topics(self, topic_orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk update topic ordering.
        
        Args:
            topic_orders: List of {"id": UUID, "order_index": int}
            
        Returns:
            Update result
        """
        for item in topic_orders:
            await self.db.execute(
                update(Topic)
                .where(Topic.id == item["id"])
                .values(order_index=item["order_index"])
            )
        
        await self.db.commit()
        return {"message": f"Updated order for {len(topic_orders)} topics"}
    
    # =========================================================================
    # Question Management
    # =========================================================================
    async def list_questions(
        self,
        subject_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List questions with filtering and pagination.
        
        Returns:
            Paginated list of questions with statistics
        """
        query = select(Question).options(
            selectinload(Question.subject),
            selectinload(Question.topic)
        )
        count_query = select(func.count(Question.id))
        
        conditions = []
        if subject_id:
            conditions.append(Question.subject_id == subject_id)
        if topic_id:
            conditions.append(Question.topic_id == topic_id)
        if difficulty:
            conditions.append(Question.difficulty == difficulty)
        if question_type:
            conditions.append(Question.question_type == question_type)
        if source:
            conditions.append(Question.source == source)
        if is_active is not None:
            conditions.append(Question.is_active == is_active)
        if search:
            conditions.append(Question.question_text.ilike(f"%{search}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Paginate
        offset = (page - 1) * page_size
        query = query.order_by(Question.created_at.desc()).offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        questions = result.scalars().all()
        
        question_list = []
        for q in questions:
            question_list.append({
                "id": str(q.id),
                "subject_id": str(q.subject_id) if q.subject_id else None,
                "subject_name": q.subject.name if q.subject else None,
                "topic_id": str(q.topic_id) if q.topic_id else None,
                "topic_name": q.topic.name if q.topic else None,
                "question_text": q.question_text[:200] + "..." if len(q.question_text) > 200 else q.question_text,
                "question_type": q.question_type,
                "difficulty": q.difficulty,
                "marks": q.marks,
                "source": q.source,
                "source_year": q.source_year,
                "times_attempted": q.times_attempted,
                "success_rate": q.success_rate,
                "is_active": q.is_active,
                "tags": q.tags,
                "created_at": q.created_at.isoformat()
            })
        
        return {
            "questions": question_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    async def get_question_detail(self, question_id: UUID) -> Optional[Dict[str, Any]]:
        """Get full question details including answer and marking scheme"""
        result = await self.db.execute(
            select(Question)
            .options(selectinload(Question.subject), selectinload(Question.topic))
            .where(Question.id == question_id)
        )
        q = result.scalar_one_or_none()
        
        if not q:
            return None
        
        return {
            "id": str(q.id),
            "subject_id": str(q.subject_id) if q.subject_id else None,
            "subject_name": q.subject.name if q.subject else None,
            "topic_id": str(q.topic_id) if q.topic_id else None,
            "topic_name": q.topic.name if q.topic else None,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "marking_scheme": q.marking_scheme,
            "explanation": q.explanation,
            "marks": q.marks,
            "difficulty": q.difficulty,
            "source": q.source,
            "source_year": q.source_year,
            "source_paper": q.source_paper,
            "source_question_number": q.source_question_number,
            "times_attempted": q.times_attempted,
            "times_correct": q.times_correct,
            "success_rate": q.success_rate,
            "avg_time_seconds": q.avg_time_seconds,
            "tags": q.tags,
            "is_active": q.is_active,
            "created_at": q.created_at.isoformat()
        }
    
    async def create_question(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new question"""
        question = Question(
            subject_id=data["subject_id"],
            topic_id=data.get("topic_id"),
            question_text=data["question_text"],
            question_type=data["question_type"],
            options=data.get("options"),
            correct_answer=data["correct_answer"],
            marking_scheme=data.get("marking_scheme"),
            explanation=data.get("explanation"),
            marks=data.get("marks", 1),
            difficulty=data.get("difficulty", "medium"),
            source=data.get("source", "admin"),
            source_year=data.get("source_year"),
            tags=data.get("tags", [])
        )
        
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        
        logger.info(f"Created question: {question.id}")
        
        return {"id": str(question.id), "message": "Question created successfully"}
    
    async def update_question(self, question_id: UUID, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing question"""
        result = await self.db.execute(select(Question).where(Question.id == question_id))
        question = result.scalar_one_or_none()
        
        if not question:
            return None
        
        for field, value in updates.items():
            if value is not None and hasattr(question, field):
                setattr(question, field, value)
        
        await self.db.commit()
        return {"id": str(question.id), "message": "Question updated successfully"}
    
    async def bulk_import_questions(self, questions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk import questions from JSON data.
        
        Args:
            questions_data: List of question dictionaries
            
        Returns:
            Import results with success/failure counts
        """
        successful = 0
        failed = 0
        errors = []
        
        for idx, q_data in enumerate(questions_data):
            try:
                question = Question(
                    subject_id=q_data.get("subject_id"),
                    topic_id=q_data.get("topic_id"),
                    question_text=q_data["question_text"],
                    question_type=q_data.get("question_type", "short_answer"),
                    options=q_data.get("options"),
                    correct_answer=q_data["correct_answer"],
                    marking_scheme=q_data.get("marking_scheme"),
                    explanation=q_data.get("explanation"),
                    marks=q_data.get("marks", 1),
                    difficulty=q_data.get("difficulty", "medium"),
                    source=q_data.get("source", "bulk_import"),
                    source_year=q_data.get("source_year"),
                    tags=q_data.get("tags", [])
                )
                self.db.add(question)
                successful += 1
            except Exception as e:
                failed += 1
                errors.append({"index": idx, "error": str(e)})
        
        await self.db.commit()
        logger.info(f"Bulk import: {successful} successful, {failed} failed")
        
        return {
            "total_processed": len(questions_data),
            "successful": successful,
            "failed": failed,
            "errors": errors[:10]  # Limit error details
        }
    
    async def flag_question(self, question_id: UUID, reason: str, flagged_by: UUID) -> Dict[str, Any]:
        """Flag a question for review"""
        result = await self.db.execute(select(Question).where(Question.id == question_id))
        question = result.scalar_one_or_none()
        
        if not question:
            return {"error": "Question not found"}
        
        # Add flag to tags
        flags = question.tags or []
        flags.append(f"flagged:{reason}:{flagged_by}")
        question.tags = flags
        
        await self.db.commit()
        logger.info(f"Question {question_id} flagged for: {reason}")
        
        return {"message": "Question flagged for review"}
    
    # =========================================================================
    # Question Analytics
    # =========================================================================
    async def get_question_stats(self) -> Dict[str, Any]:
        """Get question bank statistics"""
        # Total questions
        total_result = await self.db.execute(select(func.count(Question.id)))
        total = total_result.scalar() or 0
        
        # By difficulty
        difficulty_result = await self.db.execute(
            select(Question.difficulty, func.count(Question.id))
            .group_by(Question.difficulty)
        )
        by_difficulty = {row[0]: row[1] for row in difficulty_result.all()}
        
        # By subject
        subject_result = await self.db.execute(
            select(Subject.name, func.count(Question.id))
            .join(Question, Question.subject_id == Subject.id)
            .group_by(Subject.name)
        )
        by_subject = {row[0]: row[1] for row in subject_result.all()}
        
        # By type
        type_result = await self.db.execute(
            select(Question.question_type, func.count(Question.id))
            .group_by(Question.question_type)
        )
        by_type = {row[0]: row[1] for row in type_result.all()}
        
        # Low performing questions (success rate < 30%)
        low_performing = await self.db.execute(
            select(func.count(Question.id))
            .where(Question.times_attempted > 10)
            .where((Question.times_correct / Question.times_attempted) < 0.3)
        )
        
        return {
            "total_questions": total,
            "by_difficulty": by_difficulty,
            "by_subject": by_subject,
            "by_type": by_type,
            "low_performing_count": low_performing.scalar() or 0,
            "active_questions": total  # Simplified
        }
    
    # =========================================================================
    # Curriculum Overview
    # =========================================================================
    async def get_curriculum_tree(self, education_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get hierarchical curriculum tree for visualization.
        
        Returns:
            Nested structure of subjects > topics > sub-topics
        """
        query = select(Subject).where(Subject.is_active == True)
        if education_level:
            query = query.where(Subject.education_level == education_level)
        
        query = query.order_by(Subject.name)
        result = await self.db.execute(query)
        subjects = result.scalars().all()
        
        tree = []
        for subject in subjects:
            # Get topics for this subject
            topics_result = await self.db.execute(
                select(Topic)
                .where(Topic.subject_id == subject.id)
                .where(Topic.parent_topic_id.is_(None))
                .where(Topic.is_active == True)
                .order_by(Topic.order_index)
            )
            topics = topics_result.scalars().all()
            
            topic_nodes = []
            for topic in topics:
                # Get sub-topics
                subtopics_result = await self.db.execute(
                    select(Topic)
                    .where(Topic.parent_topic_id == topic.id)
                    .where(Topic.is_active == True)
                    .order_by(Topic.order_index)
                )
                subtopics = subtopics_result.scalars().all()
                
                # Get question count
                q_count = await self.db.execute(
                    select(func.count(Question.id)).where(Question.topic_id == topic.id)
                )
                
                topic_nodes.append({
                    "id": str(topic.id),
                    "name": topic.name,
                    "grade": topic.grade,
                    "question_count": q_count.scalar() or 0,
                    "subtopics": [
                        {"id": str(st.id), "name": st.name, "grade": st.grade}
                        for st in subtopics
                    ]
                })
            
            tree.append({
                "id": str(subject.id),
                "name": subject.name,
                "code": subject.code,
                "icon": subject.icon,
                "color": subject.color,
                "topics": topic_nodes
            })
        
        return tree
    
    async def get_coverage_analysis(self, subject_id: UUID) -> Dict[str, Any]:
        """
        Analyze curriculum coverage - topics without questions.
        
        Args:
            subject_id: Subject to analyze
            
        Returns:
            Coverage statistics and gap analysis
        """
        # Get all topics for subject
        topics_result = await self.db.execute(
            select(Topic)
            .where(Topic.subject_id == subject_id)
            .where(Topic.is_active == True)
        )
        topics = topics_result.scalars().all()
        
        covered = []
        gaps = []
        
        for topic in topics:
            q_count = await self.db.execute(
                select(func.count(Question.id)).where(Question.topic_id == topic.id)
            )
            count = q_count.scalar() or 0
            
            topic_info = {
                "id": str(topic.id),
                "name": topic.name,
                "grade": topic.grade,
                "question_count": count
            }
            
            if count > 0:
                covered.append(topic_info)
            else:
                gaps.append(topic_info)
        
        total_topics = len(topics)
        coverage_pct = (len(covered) / total_topics * 100) if total_topics > 0 else 0
        
        return {
            "total_topics": total_topics,
            "covered_topics": len(covered),
            "gap_topics": len(gaps),
            "coverage_percentage": round(coverage_pct, 1),
            "gaps": gaps,
            "recommendations": self._generate_coverage_recommendations(gaps)
        }
    
    def _generate_coverage_recommendations(self, gaps: List[Dict]) -> List[str]:
        """Generate recommendations based on coverage gaps"""
        recommendations = []
        
        if len(gaps) > 10:
            recommendations.append(f"Consider bulk importing questions - {len(gaps)} topics have no questions")
        
        # Group by grade
        by_grade = {}
        for gap in gaps:
            grade = gap.get("grade", "Unknown")
            by_grade[grade] = by_grade.get(grade, 0) + 1
        
        for grade, count in sorted(by_grade.items(), key=lambda x: x[1], reverse=True)[:3]:
            recommendations.append(f"Priority: {grade} has {count} topics without questions")
        
        return recommendations