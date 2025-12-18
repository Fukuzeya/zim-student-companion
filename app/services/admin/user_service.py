# ============================================================================
# Admin User Management Service
# ============================================================================
"""
Service layer for admin user management operations.
Handles user CRUD, filtering, bulk actions, and impersonation.
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from uuid import UUID
from decimal import Decimal
import logging

from app.models.user import User, Student, UserRole, SubscriptionTier, EducationLevel
from app.models.practice import PracticeSession, QuestionAttempt
from app.models.payment import Payment, PaymentStatus
from app.models.conversation import Conversation
from app.models.gamification import StudentAchievement
from app.core.security import create_access_token

logger = logging.getLogger(__name__)


class UserManagementService:
    """
    User management service for admin operations.
    
    Provides comprehensive user management including:
    - Filtered user listing with pagination
    - Detailed user profiles with statistics
    - User updates and bulk operations
    - Secure user impersonation for debugging
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # User Listing
    # =========================================================================
    async def list_users(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        List users with advanced filtering and pagination.
        
        Args:
            filters: Dictionary of filter criteria
            page: Page number (1-indexed)
            page_size: Number of items per page
            sort_by: Field to sort by
            sort_order: Sort direction ('asc' or 'desc')
            
        Returns:
            Paginated user list with metadata
        """
        filters = filters or {}
        
        # Base query with student join for names
        query = select(User).outerjoin(Student, User.id == Student.user_id)
        count_query = select(func.count(User.id))
        
        # Apply filters
        conditions = []
        
        if filters.get("role"):
            conditions.append(User.role == filters["role"])
        
        if filters.get("subscription_tier"):
            conditions.append(User.subscription_tier == filters["subscription_tier"])
        
        if filters.get("is_active") is not None:
            conditions.append(User.is_active == filters["is_active"])
        
        if filters.get("is_verified") is not None:
            conditions.append(User.is_verified == filters["is_verified"])
        
        if filters.get("registration_date_from"):
            conditions.append(func.date(User.created_at) >= filters["registration_date_from"])
        
        if filters.get("registration_date_to"):
            conditions.append(func.date(User.created_at) <= filters["registration_date_to"])
        
        if filters.get("last_active_from"):
            conditions.append(func.date(User.last_active) >= filters["last_active_from"])
        
        if filters.get("last_active_to"):
            conditions.append(func.date(User.last_active) <= filters["last_active_to"])
        
        if filters.get("education_level"):
            conditions.append(Student.education_level == filters["education_level"])
        
        if filters.get("province"):
            conditions.append(Student.province == filters["province"])
        
        if filters.get("district"):
            conditions.append(Student.district == filters["district"])
        
        if filters.get("school"):
            conditions.append(Student.school_name.ilike(f"%{filters['school']}%"))
        
        # Global search across multiple fields
        if filters.get("search"):
            search_term = f"%{filters['search']}%"
            conditions.append(or_(
                User.phone_number.ilike(search_term),
                User.email.ilike(search_term),
                Student.first_name.ilike(search_term),
                Student.last_name.ilike(search_term),
                Student.school_name.ilike(search_term)
            ))
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.outerjoin(Student, User.id == Student.user_id).where(and_(*conditions))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        # Build response with student info
        user_list = []
        for user in users:
            # Fetch associated student if exists
            student_result = await self.db.execute(
                select(Student).where(Student.user_id == user.id)
            )
            student = student_result.scalar_one_or_none()
            
            user_list.append({
                "id": str(user.id),
                "phone_number": user.phone_number,
                "email": user.email,
                "role": user.role.value,
                "subscription_tier": user.subscription_tier.value,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
                "last_active": user.last_active.isoformat() if user.last_active else None,
                "student_name": student.full_name if student else None,
                "school": student.school_name if student else None
            })
        
        return {
            "users": user_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    # =========================================================================
    # User Details
    # =========================================================================
    async def get_user_detail(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive user details including statistics.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Detailed user profile with all related statistics
        """
        # Fetch user with relationships
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Fetch student profile if exists
        student_result = await self.db.execute(
            select(Student).where(Student.user_id == user_id)
        )
        student = student_result.scalar_one_or_none()
        
        # Calculate statistics
        stats = await self._calculate_user_stats(user_id)
        
        # Build student dict if exists
        student_data = None
        if student:
            student_data = {
                "id": str(student.id),
                "first_name": student.first_name,
                "last_name": student.last_name,
                "full_name": student.full_name,
                "grade": student.grade,
                "education_level": student.education_level.value,
                "school_name": student.school_name,
                "district": student.district,
                "province": student.province,
                "subjects": student.subjects,
                "total_xp": student.total_xp,
                "level": student.level,
                "daily_goal_minutes": student.daily_goal_minutes,
                "preferred_language": student.preferred_language
            }
        
        return {
            "id": str(user.id),
            "phone_number": user.phone_number,
            "whatsapp_id": user.whatsapp_id,
            "email": user.email,
            "role": user.role.value,
            "subscription_tier": user.subscription_tier.value,
            "subscription_expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat(),
            "last_active": user.last_active.isoformat() if user.last_active else None,
            "student": student_data,
            **stats
        }
    
    async def _calculate_user_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Calculate user statistics for profile view"""
        # Get student ID if exists
        student_result = await self.db.execute(
            select(Student.id).where(Student.user_id == user_id)
        )
        student_id = student_result.scalar_one_or_none()
        
        stats = {
            "total_sessions": 0,
            "total_questions_answered": 0,
            "total_payments": Decimal("0"),
            "conversations_count": 0,
            "achievements_count": 0,
            "payments_count": 0
        }
        
        if student_id:
            # Sessions count
            result = await self.db.execute(
                select(func.count(PracticeSession.id))
                .where(PracticeSession.student_id == student_id)
            )
            stats["total_sessions"] = result.scalar() or 0
            
            # Questions answered
            result = await self.db.execute(
                select(func.count(QuestionAttempt.id))
                .where(QuestionAttempt.student_id == student_id)
            )
            stats["total_questions_answered"] = result.scalar() or 0
            
            # Conversations
            result = await self.db.execute(
                select(func.count(Conversation.id))
                .where(Conversation.student_id == student_id)
            )
            stats["conversations_count"] = result.scalar() or 0
            
            # Achievements
            result = await self.db.execute(
                select(func.count(StudentAchievement.id))
                .where(StudentAchievement.student_id == student_id)
            )
            stats["achievements_count"] = result.scalar() or 0
        
        # Payments (linked to user, not student)
        result = await self.db.execute(
            select(func.count(Payment.id), func.sum(Payment.amount))
            .where(Payment.user_id == user_id)
            .where(Payment.status == PaymentStatus.COMPLETED)
        )
        row = result.one()
        stats["payments_count"] = row[0] or 0
        stats["total_payments"] = float(row[1] or 0)
        
        return stats
    
    # =========================================================================
    # User Updates
    # =========================================================================
    async def update_user(self, user_id: UUID, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update user information.
        
        Args:
            user_id: UUID of the user to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated user data or None if not found
        """
        # Fetch existing user
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Apply updates
        for field, value in updates.items():
            if value is not None and hasattr(user, field):
                # Handle enum fields
                if field == "role" and isinstance(value, str):
                    value = UserRole(value)
                elif field == "subscription_tier" and isinstance(value, str):
                    value = SubscriptionTier(value)
                
                setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return await self.get_user_detail(user_id)
    
    async def bulk_action(self, user_ids: List[UUID], action: str) -> Dict[str, Any]:
        """
        Perform bulk action on multiple users.
        
        Args:
            user_ids: List of user UUIDs
            action: Action to perform (activate, deactivate, delete, upgrade, downgrade)
            
        Returns:
            Results of the bulk operation
        """
        success_count = 0
        failed_ids = []
        
        for user_id in user_ids:
            try:
                if action == "activate":
                    await self.db.execute(
                        update(User).where(User.id == user_id).values(is_active=True)
                    )
                elif action == "deactivate":
                    await self.db.execute(
                        update(User).where(User.id == user_id).values(is_active=False)
                    )
                elif action == "delete":
                    await self.db.execute(delete(User).where(User.id == user_id))
                elif action == "upgrade":
                    await self.db.execute(
                        update(User).where(User.id == user_id).values(
                            subscription_tier=SubscriptionTier.BASIC,
                            subscription_expires_at=datetime.utcnow() + timedelta(days=30)
                        )
                    )
                elif action == "downgrade":
                    await self.db.execute(
                        update(User).where(User.id == user_id).values(
                            subscription_tier=SubscriptionTier.FREE,
                            subscription_expires_at=None
                        )
                    )
                
                success_count += 1
            except Exception as e:
                logger.error(f"Bulk action failed for user {user_id}: {e}")
                failed_ids.append(str(user_id))
        
        await self.db.commit()
        
        return {
            "action": action,
            "total_requested": len(user_ids),
            "successful": success_count,
            "failed": len(failed_ids),
            "failed_ids": failed_ids
        }
    
    # =========================================================================
    # User Impersonation
    # =========================================================================
    async def impersonate_user(
        self,
        admin_id: UUID,
        target_user_id: UUID,
        read_only: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Generate impersonation token for debugging user issues.
        
        Args:
            admin_id: UUID of the admin performing impersonation
            target_user_id: UUID of the user to impersonate
            read_only: Whether the session should be read-only
            
        Returns:
            Impersonation token and metadata
        """
        # Verify target user exists
        result = await self.db.execute(select(User).where(User.id == target_user_id))
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            return None
        
        # Create impersonation token with limited expiry and metadata
        token_data = {
            "sub": str(target_user_id),
            "impersonated_by": str(admin_id),
            "read_only": read_only,
            "type": "impersonation"
        }
        
        # Short-lived token (30 minutes)
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        token = create_access_token(data=token_data, expires_delta=timedelta(minutes=30))
        
        logger.info(f"Admin {admin_id} impersonating user {target_user_id} (read_only={read_only})")
        
        return {
            "access_token": token,
            "user_id": str(target_user_id),
            "expires_at": expires_at.isoformat(),
            "read_only": read_only
        }
    
    # =========================================================================
    # Data Export
    # =========================================================================
    async def export_users(
        self,
        filters: Optional[Dict[str, Any]] = None,
        format: str = "csv"
    ) -> Tuple[bytes, str]:
        """
        Export user data for download.
        
        Args:
            filters: Filter criteria for user selection
            format: Export format (csv, excel, json)
            
        Returns:
            Tuple of (file_bytes, filename)
        """
        import io
        import csv
        import json
        
        # Get filtered users (all pages)
        users_data = await self.list_users(filters=filters, page=1, page_size=10000)
        users = users_data["users"]
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        if format == "csv":
            output = io.StringIO()
            if users:
                writer = csv.DictWriter(output, fieldnames=users[0].keys())
                writer.writeheader()
                writer.writerows(users)
            
            return output.getvalue().encode('utf-8'), f"users_export_{timestamp}.csv"
        
        elif format == "json":
            return json.dumps(users, indent=2).encode('utf-8'), f"users_export_{timestamp}.json"
        
        else:
            raise ValueError(f"Unsupported export format: {format}")