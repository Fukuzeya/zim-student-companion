# ============================================================================
# Admin Competition Management Service
# ============================================================================
"""
Service layer for competition administration.
Handles competition CRUD, live monitoring, leaderboards, and results management.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from uuid import UUID
from decimal import Decimal
import logging

from app.models.user import Student
from app.models.curriculum import Subject
from app.models.gamification import Competition, CompetitionParticipant

logger = logging.getLogger(__name__)


class CompetitionManagementService:
    """
    Competition management service for admin operations.
    
    Provides:
    - Competition CRUD operations
    - Live competition monitoring
    - Leaderboard management
    - Results processing and certificate generation
    - Anomaly detection for cheating
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # Competition Listing
    # =========================================================================
    async def list_competitions(
        self,
        status: Optional[str] = None,
        subject_id: Optional[UUID] = None,
        education_level: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        List competitions with filtering.
        
        Args:
            status: Filter by status (upcoming, active, completed, cancelled)
            subject_id: Filter by subject
            education_level: Filter by education level
            
        Returns:
            Paginated competition list with participant counts
        """
        query = select(Competition).options(selectinload(Competition.participants))
        count_query = select(func.count(Competition.id))
        
        conditions = []
        
        if status:
            conditions.append(Competition.status == status)
        
        if subject_id:
            conditions.append(Competition.subject_id == subject_id)
        
        if education_level:
            conditions.append(Competition.education_level == education_level)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Paginate
        offset = (page - 1) * page_size
        query = query.order_by(Competition.start_date.desc()).offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        competitions = result.scalars().all()
        
        competition_list = []
        for comp in competitions:
            participant_count = len(comp.participants) if comp.participants else 0
            completed_count = sum(
                1 for p in (comp.participants or [])
                if p.status == "completed"
            )
            
            competition_list.append({
                "id": str(comp.id),
                "name": comp.name,
                "description": comp.description,
                "subject_id": str(comp.subject_id) if comp.subject_id else None,
                "education_level": comp.education_level,
                "grade": comp.grade,
                "competition_type": comp.competition_type,
                "start_date": comp.start_date.isoformat(),
                "end_date": comp.end_date.isoformat(),
                "status": comp.status,
                "num_questions": comp.num_questions,
                "time_limit_minutes": comp.time_limit_minutes,
                "participant_count": participant_count,
                "completed_count": completed_count,
                "max_participants": comp.max_participants,
                "entry_fee": float(comp.entry_fee) if comp.entry_fee else 0,
                "prizes": comp.prizes
            })
        
        return {
            "competitions": competition_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    async def get_competition_detail(self, competition_id: UUID) -> Optional[Dict[str, Any]]:
        """Get detailed competition information"""
        result = await self.db.execute(
            select(Competition)
            .options(selectinload(Competition.participants))
            .where(Competition.id == competition_id)
        )
        comp = result.scalar_one_or_none()
        
        if not comp:
            return None
        
        # Get subject name if exists
        subject_name = None
        if comp.subject_id:
            subj_result = await self.db.execute(
                select(Subject.name).where(Subject.id == comp.subject_id)
            )
            subject_name = subj_result.scalar_one_or_none()
        
        return {
            "id": str(comp.id),
            "name": comp.name,
            "description": comp.description,
            "subject_id": str(comp.subject_id) if comp.subject_id else None,
            "subject_name": subject_name,
            "education_level": comp.education_level,
            "grade": comp.grade,
            "competition_type": comp.competition_type,
            "start_date": comp.start_date.isoformat(),
            "end_date": comp.end_date.isoformat(),
            "status": comp.status,
            "max_participants": comp.max_participants,
            "entry_fee": float(comp.entry_fee) if comp.entry_fee else 0,
            "prizes": comp.prizes,
            "rules": comp.rules,
            "num_questions": comp.num_questions,
            "time_limit_minutes": comp.time_limit_minutes,
            "difficulty": comp.difficulty,
            "participant_count": len(comp.participants) if comp.participants else 0,
            "created_at": comp.created_at.isoformat(),
            "created_by": str(comp.created_by) if comp.created_by else None
        }
    
    # =========================================================================
    # Competition CRUD
    # =========================================================================
    async def create_competition(self, data: Dict[str, Any], created_by: UUID) -> Dict[str, Any]:
        """
        Create a new competition.
        
        Args:
            data: Competition data
            created_by: Admin UUID
            
        Returns:
            Created competition ID
        """
        competition = Competition(
            name=data["name"],
            description=data.get("description"),
            subject_id=data.get("subject_id"),
            education_level=data.get("education_level"),
            grade=data.get("grade"),
            competition_type=data.get("competition_type", "individual"),
            start_date=data["start_date"],
            end_date=data["end_date"],
            max_participants=data.get("max_participants"),
            entry_fee=Decimal(str(data.get("entry_fee", 0))),
            prizes=data.get("prizes"),
            rules=data.get("rules"),
            num_questions=data.get("num_questions", 10),
            time_limit_minutes=data.get("time_limit_minutes", 30),
            difficulty=data.get("difficulty", "medium"),
            status="upcoming",
            created_by=created_by
        )
        
        self.db.add(competition)
        await self.db.commit()
        await self.db.refresh(competition)
        
        logger.info(f"Created competition: {competition.name} (ID: {competition.id})")
        
        return {
            "id": str(competition.id),
            "name": competition.name,
            "message": "Competition created successfully"
        }
    
    async def update_competition(
        self,
        competition_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an existing competition"""
        result = await self.db.execute(
            select(Competition).where(Competition.id == competition_id)
        )
        competition = result.scalar_one_or_none()
        
        if not competition:
            return None
        
        # Don't allow certain updates if competition has started
        if competition.status in ["active", "completed"]:
            restricted_fields = ["start_date", "num_questions", "time_limit_minutes", "difficulty"]
            for field in restricted_fields:
                if field in updates:
                    return {"error": f"Cannot update {field} after competition has started"}
        
        for field, value in updates.items():
            if value is not None and hasattr(competition, field):
                if field == "entry_fee":
                    value = Decimal(str(value))
                setattr(competition, field, value)
        
        await self.db.commit()
        
        return {"id": str(competition_id), "message": "Competition updated successfully"}
    
    async def delete_competition(self, competition_id: UUID) -> Dict[str, Any]:
        """Delete or cancel a competition"""
        result = await self.db.execute(
            select(Competition)
            .options(selectinload(Competition.participants))
            .where(Competition.id == competition_id)
        )
        competition = result.scalar_one_or_none()
        
        if not competition:
            return {"success": False, "error": "Competition not found"}
        
        # If has participants, cancel instead of delete
        if competition.participants and len(competition.participants) > 0:
            competition.status = "cancelled"
            await self.db.commit()
            return {
                "success": True,
                "action": "cancelled",
                "message": "Competition cancelled (has participants)"
            }
        
        # Otherwise delete
        await self.db.execute(delete(Competition).where(Competition.id == competition_id))
        await self.db.commit()
        
        return {"success": True, "action": "deleted", "message": "Competition deleted"}
    
    # =========================================================================
    # Live Monitoring
    # =========================================================================
    async def get_live_competition_data(self, competition_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get real-time data for an active competition.
        
        Returns:
            Live participant data, progress, leaderboard, anomalies
        """
        result = await self.db.execute(
            select(Competition)
            .options(selectinload(Competition.participants))
            .where(Competition.id == competition_id)
        )
        competition = result.scalar_one_or_none()
        
        if not competition:
            return None
        
        now = datetime.utcnow()
        
        # Calculate time remaining
        if competition.status == "active" and competition.end_date > now:
            time_remaining = int((competition.end_date - now).total_seconds())
        else:
            time_remaining = 0
        
        # Get participant stats
        participants = competition.participants or []
        total_participants = len(participants)
        active_participants = sum(1 for p in participants if p.status == "in_progress")
        completed_participants = sum(1 for p in participants if p.status == "completed")
        
        # Build leaderboard
        leaderboard = await self._build_leaderboard(competition_id, limit=20)
        
        # Detect anomalies
        anomalies = await self._detect_anomalies(competition_id)
        
        return {
            "competition_id": str(competition_id),
            "name": competition.name,
            "status": competition.status,
            "time_remaining_seconds": time_remaining,
            "total_participants": total_participants,
            "active_participants": active_participants,
            "completed_participants": completed_participants,
            "leaderboard": leaderboard,
            "anomalies": anomalies,
            "last_updated": now.isoformat()
        }
    
    async def _build_leaderboard(
        self,
        competition_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Build leaderboard for a competition"""
        result = await self.db.execute(
            select(CompetitionParticipant, Student)
            .join(Student, CompetitionParticipant.student_id == Student.id)
            .where(CompetitionParticipant.competition_id == competition_id)
            .where(CompetitionParticipant.status.in_(["completed", "in_progress"]))
            .order_by(CompetitionParticipant.score.desc())
            .limit(limit)
        )
        
        leaderboard = []
        for rank, (participant, student) in enumerate(result.all(), 1):
            leaderboard.append({
                "rank": rank,
                "student_id": str(student.id),
                "student_name": student.full_name,
                "school": student.school_name,
                "score": float(participant.score or 0),
                "questions_correct": participant.questions_correct,
                "questions_attempted": participant.questions_attempted,
                "time_taken_seconds": participant.time_taken_seconds,
                "status": participant.status,
                "completed_at": participant.completed_at.isoformat() if participant.completed_at else None
            })
        
        return leaderboard
    
    async def _detect_anomalies(self, competition_id: UUID) -> List[Dict[str, Any]]:
        """
        Detect potential cheating or anomalies in competition.
        
        Checks for:
        - Unusually fast completion times
        - Perfect scores with fast times
        - Suspicious answer patterns
        """
        anomalies = []
        
        result = await self.db.execute(
            select(CompetitionParticipant, Student)
            .join(Student, CompetitionParticipant.student_id == Student.id)
            .where(CompetitionParticipant.competition_id == competition_id)
            .where(CompetitionParticipant.status == "completed")
        )
        
        for participant, student in result.all():
            # Check for unusually fast completion
            if participant.time_taken_seconds and participant.time_taken_seconds < 60:
                anomalies.append({
                    "type": "fast_completion",
                    "severity": "high",
                    "student_id": str(student.id),
                    "student_name": student.full_name,
                    "description": f"Completed in {participant.time_taken_seconds} seconds",
                    "score": float(participant.score or 0)
                })
            
            # Check for perfect score with very fast time
            if (participant.questions_correct == participant.questions_attempted and
                participant.time_taken_seconds and
                participant.time_taken_seconds < 120):
                anomalies.append({
                    "type": "perfect_fast",
                    "severity": "medium",
                    "student_id": str(student.id),
                    "student_name": student.full_name,
                    "description": f"Perfect score in {participant.time_taken_seconds}s",
                    "score": float(participant.score or 0)
                })
        
        return anomalies
    
    # =========================================================================
    # Leaderboard
    # =========================================================================
    async def get_leaderboard(
        self,
        competition_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """Get paginated leaderboard for a competition"""
        # Get total count
        count_result = await self.db.execute(
            select(func.count(CompetitionParticipant.id))
            .where(CompetitionParticipant.competition_id == competition_id)
            .where(CompetitionParticipant.status == "completed")
        )
        total = count_result.scalar() or 0
        
        # Get paginated results
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(CompetitionParticipant, Student)
            .join(Student, CompetitionParticipant.student_id == Student.id)
            .where(CompetitionParticipant.competition_id == competition_id)
            .where(CompetitionParticipant.status == "completed")
            .order_by(
                CompetitionParticipant.score.desc(),
                CompetitionParticipant.time_taken_seconds.asc()
            )
            .offset(offset)
            .limit(page_size)
        )
        
        entries = []
        for idx, (participant, student) in enumerate(result.all()):
            entries.append({
                "rank": offset + idx + 1,
                "student_id": str(student.id),
                "student_name": student.full_name,
                "school": student.school_name,
                "grade": student.grade,
                "score": float(participant.score or 0),
                "questions_correct": participant.questions_correct,
                "questions_attempted": participant.questions_attempted,
                "time_taken_seconds": participant.time_taken_seconds,
                "prize_won": participant.prize_won,
                "completed_at": participant.completed_at.isoformat() if participant.completed_at else None
            })
        
        return {
            "entries": entries,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    # =========================================================================
    # Results & Awards
    # =========================================================================
    async def finalize_competition(self, competition_id: UUID) -> Dict[str, Any]:
        """
        Finalize a competition - calculate final rankings and distribute prizes.
        
        Called after competition ends to process results.
        """
        result = await self.db.execute(
            select(Competition)
            .options(selectinload(Competition.participants))
            .where(Competition.id == competition_id)
        )
        competition = result.scalar_one_or_none()
        
        if not competition:
            return {"success": False, "error": "Competition not found"}
        
        if competition.status == "completed":
            return {"success": False, "error": "Competition already finalized"}
        
        # Get all completed participants ordered by score
        participants = await self.db.execute(
            select(CompetitionParticipant)
            .where(CompetitionParticipant.competition_id == competition_id)
            .where(CompetitionParticipant.status == "completed")
            .order_by(
                CompetitionParticipant.score.desc(),
                CompetitionParticipant.time_taken_seconds.asc()
            )
        )
        participants = participants.scalars().all()
        
        # Assign ranks and prizes
        prizes = competition.prizes or {}
        for rank, participant in enumerate(participants, 1):
            participant.rank = rank
            
            # Assign prize if applicable
            rank_key = f"{rank}{'st' if rank == 1 else 'nd' if rank == 2 else 'rd' if rank == 3 else 'th'}"
            if rank_key in prizes:
                participant.prize_won = prizes[rank_key]
            elif str(rank) in prizes:
                participant.prize_won = prizes[str(rank)]
        
        # Update competition status
        competition.status = "completed"
        
        await self.db.commit()
        
        logger.info(f"Finalized competition: {competition_id} with {len(participants)} participants")
        
        return {
            "success": True,
            "competition_id": str(competition_id),
            "participants_ranked": len(participants),
            "message": "Competition finalized successfully"
        }
    
    async def disqualify_participant(
        self,
        competition_id: UUID,
        student_id: UUID,
        reason: str,
        admin_id: UUID
    ) -> Dict[str, Any]:
        """Disqualify a participant from competition"""
        result = await self.db.execute(
            select(CompetitionParticipant)
            .where(CompetitionParticipant.competition_id == competition_id)
            .where(CompetitionParticipant.student_id == student_id)
        )
        participant = result.scalar_one_or_none()
        
        if not participant:
            return {"success": False, "error": "Participant not found"}
        
        participant.status = "disqualified"
        participant.prize_won = None
        participant.rank = None
        
        await self.db.commit()
        
        logger.info(
            f"Disqualified participant: Student {student_id} from competition {competition_id}. "
            f"Reason: {reason}. By admin: {admin_id}"
        )
        
        return {
            "success": True,
            "student_id": str(student_id),
            "message": "Participant disqualified"
        }
    
    async def export_results(
        self,
        competition_id: UUID,
        format: str = "csv"
    ) -> Dict[str, Any]:
        """Export competition results"""
        leaderboard = await self._build_leaderboard(competition_id, limit=10000)
        
        if format == "csv":
            import io
            import csv
            
            output = io.StringIO()
            if leaderboard:
                writer = csv.DictWriter(output, fieldnames=leaderboard[0].keys())
                writer.writeheader()
                writer.writerows(leaderboard)
            
            return {
                "data": output.getvalue(),
                "filename": f"competition_{competition_id}_results.csv",
                "content_type": "text/csv"
            }
        
        return {
            "data": leaderboard,
            "format": "json"
        }