# ============================================================================
# Admin System & Settings Service
# ============================================================================
"""
Service layer for system administration, settings, and health monitoring.
Handles system configuration, admin user management, audit logging, and health checks.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field
import logging
import asyncio
import time
import psutil
import os

from app.models.user import User, UserRole
from app.core.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)


# ============================================================================
# Audit Log Models
# ============================================================================
class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    IMPERSONATE = "impersonate"
    EXPORT = "export"
    REFUND = "refund"
    BROADCAST = "broadcast"
    SETTINGS_CHANGE = "settings_change"

@dataclass
class AuditLogEntry:
    id: UUID
    admin_id: UUID
    admin_email: str
    action: AuditAction
    resource_type: str
    resource_id: Optional[UUID]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime


# ============================================================================
# System Settings Model
# ============================================================================
@dataclass
class SystemSettings:
    app_name: str = "EduBot Zimbabwe"
    app_tagline: str = "AI-Powered Learning for ZIMSEC Success"
    contact_email: str = "support@edubot.co.zw"
    contact_phone: str = "+263 77 123 4567"
    support_hours: str = "Mon-Fri 8:00 AM - 6:00 PM CAT"
    
    # Feature flags
    feature_flags: Dict[str, bool] = field(default_factory=lambda: {
        "whatsapp_enabled": True,
        "competitions_enabled": True,
        "payments_enabled": True,
        "ai_hints_enabled": True,
        "parent_dashboard_enabled": True,
        "school_accounts_enabled": False,
        "referral_program_enabled": False,
    })
    
    # Maintenance mode
    maintenance_mode: bool = False
    maintenance_message: Optional[str] = None
    
    # Rate limits
    rate_limits: Dict[str, int] = field(default_factory=lambda: {
        "api_requests_per_minute": 60,
        "messages_per_hour_free": 20,
        "messages_per_hour_premium": 100,
        "file_uploads_per_day": 10,
    })
    
    # AI Configuration
    ai_config: Dict[str, Any] = field(default_factory=lambda: {
        "model": "gemini-pro",
        "max_tokens": 2048,
        "temperature": 0.7,
        "safety_threshold": "medium",
    })


class SystemService:
    """
    System administration and monitoring service.
    
    Provides:
    - System settings management
    - Admin user CRUD
    - Audit logging
    - System health monitoring
    - Performance metrics
    """
    
    # Application start time for uptime calculation
    _start_time: datetime = datetime.utcnow()
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # In-memory storage (use Redis/DB in production)
        self._settings = SystemSettings()
        self._audit_log: List[AuditLogEntry] = []
    
    # =========================================================================
    # System Settings
    # =========================================================================
    async def get_settings(self) -> Dict[str, Any]:
        """Get current system settings"""
        return {
            "app_name": self._settings.app_name,
            "app_tagline": self._settings.app_tagline,
            "contact_email": self._settings.contact_email,
            "contact_phone": self._settings.contact_phone,
            "support_hours": self._settings.support_hours,
            "feature_flags": self._settings.feature_flags,
            "maintenance_mode": self._settings.maintenance_mode,
            "maintenance_message": self._settings.maintenance_message,
            "rate_limits": self._settings.rate_limits,
            "ai_config": self._settings.ai_config
        }
    
    async def update_settings(
        self,
        updates: Dict[str, Any],
        admin_id: UUID
    ) -> Dict[str, Any]:
        """
        Update system settings.
        
        Args:
            updates: Dictionary of settings to update
            admin_id: Admin performing the update
            
        Returns:
            Updated settings
        """
        old_settings = await self.get_settings()
        
        for key, value in updates.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        
        # Log the change
        await self.log_action(
            admin_id=admin_id,
            admin_email="",  # Would fetch from DB
            action=AuditAction.SETTINGS_CHANGE,
            resource_type="system_settings",
            resource_id=None,
            details={
                "old_values": {k: old_settings.get(k) for k in updates.keys()},
                "new_values": updates
            }
        )
        
        logger.info(f"System settings updated by admin {admin_id}")
        
        return await self.get_settings()
    
    async def toggle_feature_flag(
        self,
        flag_name: str,
        enabled: bool,
        admin_id: UUID
    ) -> Dict[str, Any]:
        """Toggle a feature flag"""
        if flag_name not in self._settings.feature_flags:
            return {"success": False, "error": f"Unknown feature flag: {flag_name}"}
        
        old_value = self._settings.feature_flags[flag_name]
        self._settings.feature_flags[flag_name] = enabled
        
        await self.log_action(
            admin_id=admin_id,
            admin_email="",
            action=AuditAction.SETTINGS_CHANGE,
            resource_type="feature_flag",
            resource_id=None,
            details={
                "flag": flag_name,
                "old_value": old_value,
                "new_value": enabled
            }
        )
        
        return {
            "success": True,
            "flag": flag_name,
            "enabled": enabled,
            "message": f"Feature flag '{flag_name}' {'enabled' if enabled else 'disabled'}"
        }
    
    async def set_maintenance_mode(
        self,
        enabled: bool,
        message: Optional[str],
        admin_id: UUID
    ) -> Dict[str, Any]:
        """Enable or disable maintenance mode"""
        self._settings.maintenance_mode = enabled
        self._settings.maintenance_message = message if enabled else None
        
        await self.log_action(
            admin_id=admin_id,
            admin_email="",
            action=AuditAction.SETTINGS_CHANGE,
            resource_type="maintenance_mode",
            resource_id=None,
            details={"enabled": enabled, "message": message}
        )
        
        status = "enabled" if enabled else "disabled"
        logger.warning(f"Maintenance mode {status} by admin {admin_id}")
        
        return {
            "success": True,
            "maintenance_mode": enabled,
            "message": f"Maintenance mode {status}"
        }
    
    # =========================================================================
    # Admin User Management
    # =========================================================================
    async def list_admins(self) -> List[Dict[str, Any]]:
        """List all admin users"""
        result = await self.db.execute(
            select(User)
            .where(User.role == UserRole.ADMIN)
            .order_by(User.created_at.desc())
        )
        admins = result.scalars().all()
        
        return [
            {
                "id": str(admin.id),
                "email": admin.email,
                "phone_number": admin.phone_number,
                "is_active": admin.is_active,
                "is_verified": admin.is_verified,
                "created_at": admin.created_at.isoformat(),
                "last_active": admin.last_active.isoformat() if admin.last_active else None
            }
            for admin in admins
        ]
    
    async def create_admin(
        self,
        email: str,
        password: str,
        phone_number: Optional[str],
        created_by: UUID
    ) -> Dict[str, Any]:
        """
        Create a new admin user.
        
        Args:
            email: Admin email
            password: Admin password
            phone_number: Optional phone number
            created_by: Admin creating this user
            
        Returns:
            Created admin details
        """
        # Check if email exists
        existing = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            return {"success": False, "error": "Email already exists"}
        
        admin = User(
            email=email,
            password_hash=get_password_hash(password),
            phone_number=phone_number or f"admin_{email}",
            role=UserRole.ADMIN,
            is_verified=True,
            is_active=True
        )
        
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)
        
        await self.log_action(
            admin_id=created_by,
            admin_email="",
            action=AuditAction.CREATE,
            resource_type="admin_user",
            resource_id=admin.id,
            details={"email": email}
        )
        
        logger.info(f"Admin user created: {email} by {created_by}")
        
        return {
            "success": True,
            "id": str(admin.id),
            "email": email,
            "message": "Admin user created successfully"
        }
    
    async def update_admin(
        self,
        admin_id: UUID,
        updates: Dict[str, Any],
        updated_by: UUID
    ) -> Optional[Dict[str, Any]]:
        """Update an admin user"""
        result = await self.db.execute(
            select(User).where(User.id == admin_id).where(User.role == UserRole.ADMIN)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            return None
        
        for field, value in updates.items():
            if field == "password":
                admin.password_hash = get_password_hash(value)
            elif hasattr(admin, field) and value is not None:
                setattr(admin, field, value)
        
        await self.db.commit()
        
        await self.log_action(
            admin_id=updated_by,
            admin_email="",
            action=AuditAction.UPDATE,
            resource_type="admin_user",
            resource_id=admin_id,
            details={"updated_fields": list(updates.keys())}
        )
        
        return {"id": str(admin_id), "message": "Admin updated successfully"}
    
    async def deactivate_admin(
        self,
        admin_id: UUID,
        deactivated_by: UUID
    ) -> Dict[str, Any]:
        """Deactivate an admin user"""
        # Prevent self-deactivation
        if admin_id == deactivated_by:
            return {"success": False, "error": "Cannot deactivate yourself"}
        
        result = await self.db.execute(
            select(User).where(User.id == admin_id).where(User.role == UserRole.ADMIN)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            return {"success": False, "error": "Admin not found"}
        
        admin.is_active = False
        await self.db.commit()
        
        await self.log_action(
            admin_id=deactivated_by,
            admin_email="",
            action=AuditAction.UPDATE,
            resource_type="admin_user",
            resource_id=admin_id,
            details={"action": "deactivated"}
        )
        
        return {"success": True, "message": "Admin deactivated"}
    
    # =========================================================================
    # Audit Logging
    # =========================================================================
    async def log_action(
        self,
        admin_id: UUID,
        admin_email: str,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[UUID],
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log an admin action to the audit log.
        
        All sensitive admin operations should be logged for compliance.
        """
        entry = AuditLogEntry(
            id=uuid4(),
            admin_id=admin_id,
            admin_email=admin_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow()
        )
        
        self._audit_log.append(entry)
        
        # Keep only last 10000 entries in memory
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]
        
        logger.info(
            f"AUDIT: {action.value} on {resource_type} "
            f"by {admin_id} - {details}"
        )
    
    async def get_audit_log(
        self,
        admin_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Retrieve audit log entries with filtering.
        
        Args:
            admin_id: Filter by admin who performed action
            action: Filter by action type
            resource_type: Filter by resource type
            date_from: Start date filter
            date_to: End date filter
            limit: Maximum entries to return
            offset: Pagination offset
            
        Returns:
            Filtered and paginated audit log entries
        """
        entries = self._audit_log.copy()
        
        # Apply filters
        if admin_id:
            entries = [e for e in entries if e.admin_id == admin_id]
        
        if action:
            entries = [e for e in entries if e.action.value == action]
        
        if resource_type:
            entries = [e for e in entries if e.resource_type == resource_type]
        
        if date_from:
            entries = [e for e in entries if e.timestamp >= date_from]
        
        if date_to:
            entries = [e for e in entries if e.timestamp <= date_to]
        
        # Sort by timestamp descending
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        total = len(entries)
        entries = entries[offset:offset + limit]
        
        return {
            "entries": [
                {
                    "id": str(e.id),
                    "admin_id": str(e.admin_id),
                    "admin_email": e.admin_email,
                    "action": e.action.value,
                    "resource_type": e.resource_type,
                    "resource_id": str(e.resource_id) if e.resource_id else None,
                    "details": e.details,
                    "ip_address": e.ip_address,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in entries
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    # =========================================================================
    # System Health
    # =========================================================================
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.
        
        Checks:
        - Database connectivity and latency
        - Redis connectivity
        - External service status
        - System resources (CPU, memory)
        - Application metrics
        """
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Database check
        db_health = await self._check_database()
        health["checks"]["database"] = db_health
        
        # Redis check
        redis_health = await self._check_redis()
        health["checks"]["redis"] = redis_health
        
        # External services
        external_health = await self._check_external_services()
        health["checks"]["external_services"] = external_health
        
        # System resources
        resources = self._get_system_resources()
        health["checks"]["resources"] = resources
        
        # Application metrics
        app_metrics = await self._get_application_metrics()
        health["checks"]["application"] = app_metrics
        
        # Calculate uptime
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        health["uptime_seconds"] = int(uptime)
        
        # Determine overall status
        critical_checks = ["database", "redis"]
        for check in critical_checks:
            if health["checks"].get(check, {}).get("status") == "unhealthy":
                health["status"] = "critical"
                break
            elif health["checks"].get(check, {}).get("status") == "degraded":
                health["status"] = "degraded"
        
        return health
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and latency"""
        try:
            start = time.time()
            await self.db.execute(text("SELECT 1"))
            latency = (time.time() - start) * 1000
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "message": "Database connection successful"
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "message": str(e)
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            from app.core.redis import cache
            
            start = time.time()
            await cache.set("health_check", "ok", ttl=10)
            value = await cache.get("health_check")
            latency = (time.time() - start) * 1000
            
            if value == "ok":
                return {
                    "status": "healthy",
                    "latency_ms": round(latency, 2),
                    "message": "Redis connection successful"
                }
            else:
                return {
                    "status": "degraded",
                    "latency_ms": round(latency, 2),
                    "message": "Redis read/write mismatch"
                }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "message": str(e)
            }
    
    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity"""
        services = {}
        
        # WhatsApp API (mock check)
        services["whatsapp"] = {
            "status": "healthy",
            "message": "WhatsApp API available"
        }
        
        # Payment gateway (mock check)
        services["paynow"] = {
            "status": "healthy",
            "message": "Paynow gateway available"
        }
        
        # AI service (mock check)
        services["gemini"] = {
            "status": "healthy",
            "message": "Gemini API available"
        }
        
        return services
    
    def _get_system_resources(self) -> Dict[str, Any]:
        """Get system resource utilization"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "status": "healthy" if cpu_percent < 80 and memory.percent < 80 else "degraded",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": round(memory.available / (1024 * 1024), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2)
            }
        except Exception as e:
            return {
                "status": "unknown",
                "message": str(e)
            }
    
    async def _get_application_metrics(self) -> Dict[str, Any]:
        """Get application-level metrics"""
        # Get user counts
        total_users_result = await self.db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0
        
        # Get active users (last 24h)
        day_ago = datetime.utcnow() - timedelta(hours=24)
        active_result = await self.db.execute(
            select(func.count(User.id))
            .where(User.last_active >= day_ago)
        )
        active_users = active_result.scalar() or 0
        
        return {
            "status": "healthy",
            "total_users": total_users,
            "active_users_24h": active_users,
            "maintenance_mode": self._settings.maintenance_mode
        }
    
    async def get_error_logs(
        self,
        level: str = "ERROR",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent error logs.
        
        In production, this would query a logging service like CloudWatch or Elasticsearch.
        """
        # Mock error logs for demonstration
        return [
            {
                "timestamp": (datetime.utcnow() - timedelta(minutes=i*5)).isoformat(),
                "level": level,
                "message": f"Sample error message {i}",
                "source": "app.services.example",
                "trace_id": str(uuid4())
            }
            for i in range(min(limit, 10))
        ]