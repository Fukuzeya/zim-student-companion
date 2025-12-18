# ============================================================================
# Admin WebSocket Endpoints
# ============================================================================
"""
WebSocket endpoints for real-time admin functionality.
Provides live streaming for conversations and competition monitoring.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Set, Optional
from uuid import UUID
from datetime import datetime
import asyncio
import json
import logging

from app.core.database import get_db

from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.services.admin.conversation_service import ConversationMonitoringService
from app.services.admin.competition_service import CompetitionManagementService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-websocket"])


# ============================================================================
# WebSocket Connection Manager
# ============================================================================
class ConnectionManager:
    """
    Manages WebSocket connections for admin real-time features.
    
    Supports:
    - Multiple connection types (conversations, competitions)
    - Room-based broadcasting (per competition, global)
    - Authentication verification
    - Automatic cleanup on disconnect
    """
    
    def __init__(self):
        # Active connections by type and room
        self.active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {
            "conversations": {"global": set()},
            "competitions": {}
        }
        # Track admin info per connection
        self.connection_info: Dict[WebSocket, Dict] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        connection_type: str,
        room: str = "global",
        admin_id: Optional[UUID] = None
    ):
        """Accept and register a WebSocket connection"""
        await websocket.accept()
        
        # Ensure room exists
        if room not in self.active_connections[connection_type]:
            self.active_connections[connection_type][room] = set()
        
        self.active_connections[connection_type][room].add(websocket)
        self.connection_info[websocket] = {
            "admin_id": admin_id,
            "type": connection_type,
            "room": room,
            "connected_at": datetime.utcnow()
        }
        
        logger.info(f"WebSocket connected: {connection_type}/{room} - Admin {admin_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        info = self.connection_info.get(websocket)
        if info:
            conn_type = info["type"]
            room = info["room"]
            if room in self.active_connections[conn_type]:
                self.active_connections[conn_type][room].discard(websocket)
            del self.connection_info[websocket]
            logger.info(f"WebSocket disconnected: {conn_type}/{room}")
    
    async def broadcast(
        self,
        message: dict,
        connection_type: str,
        room: str = "global"
    ):
        """Broadcast message to all connections in a room"""
        if room not in self.active_connections[connection_type]:
            return
        
        disconnected = set()
        for websocket in self.active_connections[connection_type][room]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect(ws)
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to a specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"WebSocket personal send error: {e}")
            self.disconnect(websocket)
    
    def get_connection_count(self, connection_type: str, room: str = "global") -> int:
        """Get number of active connections in a room"""
        if room not in self.active_connections[connection_type]:
            return 0
        return len(self.active_connections[connection_type][room])


# Global connection manager
manager = ConnectionManager()


# ============================================================================
# WebSocket Authentication
# ============================================================================
async def verify_admin_token(token: str, db: AsyncSession) -> Optional[User]:
    """
    Verify admin authentication token for WebSocket connections.
    
    WebSocket connections can't use standard HTTP headers easily,
    so we accept the token as a query parameter.
    """
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user and user.role == UserRole.ADMIN and user.is_active:
            return user
        return None
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        return None


# ============================================================================
# Conversation Streaming WebSocket
# ============================================================================
@router.websocket("/conversations/stream")
async def conversation_stream(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time conversation monitoring.
    
    Streams:
    - New messages as they arrive
    - Conversation status changes
    - Alerts for conversations needing attention
    
    Usage:
        ws://host/admin/conversations/stream?token=<admin_token>
    
    Message format:
        {
            "type": "new_message" | "status_change" | "alert",
            "data": { ... },
            "timestamp": "ISO datetime"
        }
    """
    # Verify admin authentication
    admin = await verify_admin_token(token, db)
    if not admin:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await manager.connect(websocket, "conversations", "global", admin.id)
    
    try:
        # Start background task to push updates
        push_task = asyncio.create_task(
            _push_conversation_updates(websocket, db)
        )
        
        # Listen for client messages (filters, commands)
        while True:
            try:
                data = await websocket.receive_json()
                await _handle_conversation_command(websocket, data, db)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal(websocket, {
                    "type": "error",
                    "message": "Invalid JSON"
                })
    
    finally:
        push_task.cancel()
        manager.disconnect(websocket)


async def _push_conversation_updates(websocket: WebSocket, db: AsyncSession):
    """Background task to push conversation updates"""
    service = ConversationMonitoringService(db)
    last_check = datetime.utcnow()
    
    while True:
        try:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            # Get live conversations
            conversations = await service.get_live_conversations(limit=20)
            
            # Check for conversations needing attention
            attention_needed = [
                c for c in conversations
                if c.get("status") == "needs_attention"
            ]
            
            # Send updates
            await manager.send_personal(websocket, {
                "type": "conversations_update",
                "data": {
                    "active_count": len(conversations),
                    "attention_needed": len(attention_needed),
                    "conversations": conversations[:10]  # Top 10
                },
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Send alerts for new attention items
            for conv in attention_needed:
                await manager.send_personal(websocket, {
                    "type": "alert",
                    "data": {
                        "conversation_id": conv["id"],
                        "student_name": conv["student_name"],
                        "reason": "Needs attention"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            last_check = datetime.utcnow()
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Conversation push error: {e}")
            await asyncio.sleep(10)  # Back off on error


async def _handle_conversation_command(
    websocket: WebSocket,
    data: dict,
    db: AsyncSession
):
    """Handle commands from the client"""
    command = data.get("command")
    
    if command == "get_conversation":
        conv_id = data.get("conversation_id")
        if conv_id:
            service = ConversationMonitoringService(db)
            detail = await service.get_conversation_detail(
                conversation_id=UUID(conv_id)
            )
            await manager.send_personal(websocket, {
                "type": "conversation_detail",
                "data": detail,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    elif command == "search":
        query = data.get("query", "")
        service = ConversationMonitoringService(db)
        results = await service.search_conversations(query=query, limit=20)
        await manager.send_personal(websocket, {
            "type": "search_results",
            "data": results,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif command == "ping":
        await manager.send_personal(websocket, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })


# ============================================================================
# Competition Live Streaming WebSocket
# ============================================================================
@router.websocket("/competitions/{competition_id}/stream")
async def competition_stream(
    websocket: WebSocket,
    competition_id: UUID,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time competition monitoring.
    
    Streams:
    - Live leaderboard updates
    - Participant progress
    - Anomaly alerts
    - Time remaining updates
    
    Usage:
        ws://host/admin/competitions/{id}/stream?token=<admin_token>
    """
    # Verify admin authentication
    admin = await verify_admin_token(token, db)
    if not admin:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    room = str(competition_id)
    await manager.connect(websocket, "competitions", room, admin.id)
    
    try:
        # Start background task to push updates
        push_task = asyncio.create_task(
            _push_competition_updates(websocket, competition_id, db)
        )
        
        # Listen for client messages
        while True:
            try:
                data = await websocket.receive_json()
                await _handle_competition_command(
                    websocket, competition_id, data, db
                )
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal(websocket, {
                    "type": "error",
                    "message": "Invalid JSON"
                })
    
    finally:
        push_task.cancel()
        manager.disconnect(websocket)


async def _push_competition_updates(
    websocket: WebSocket,
    competition_id: UUID,
    db: AsyncSession
):
    """Background task to push competition updates"""
    service = CompetitionManagementService(db)
    
    while True:
        try:
            await asyncio.sleep(3)  # Update every 3 seconds for live competitions
            
            # Get live data
            live_data = await service.get_live_competition_data(competition_id)
            
            if not live_data:
                await manager.send_personal(websocket, {
                    "type": "error",
                    "message": "Competition not found",
                    "timestamp": datetime.utcnow().isoformat()
                })
                break
            
            # Send leaderboard update
            await manager.send_personal(websocket, {
                "type": "leaderboard_update",
                "data": {
                    "competition_id": str(competition_id),
                    "status": live_data["status"],
                    "time_remaining_seconds": live_data["time_remaining_seconds"],
                    "total_participants": live_data["total_participants"],
                    "active_participants": live_data["active_participants"],
                    "completed_participants": live_data["completed_participants"],
                    "leaderboard": live_data["leaderboard"][:20]  # Top 20
                },
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Send anomaly alerts
            for anomaly in live_data.get("anomalies", []):
                await manager.send_personal(websocket, {
                    "type": "anomaly_alert",
                    "data": anomaly,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Check if competition ended
            if live_data["status"] == "completed":
                await manager.send_personal(websocket, {
                    "type": "competition_ended",
                    "data": {"competition_id": str(competition_id)},
                    "timestamp": datetime.utcnow().isoformat()
                })
                break
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Competition push error: {e}")
            await asyncio.sleep(10)


async def _handle_competition_command(
    websocket: WebSocket,
    competition_id: UUID,
    data: dict,
    db: AsyncSession
):
    """Handle competition WebSocket commands"""
    command = data.get("command")
    
    if command == "get_full_leaderboard":
        service = CompetitionManagementService(db)
        leaderboard = await service.get_leaderboard(
            competition_id=competition_id,
            page=data.get("page", 1),
            page_size=data.get("page_size", 100)
        )
        await manager.send_personal(websocket, {
            "type": "full_leaderboard",
            "data": leaderboard,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif command == "get_participant":
        student_id = data.get("student_id")
        if student_id:
            # Get specific participant details
            service = CompetitionManagementService(db)
            leaderboard = await service.get_leaderboard(competition_id)
            participant = next(
                (p for p in leaderboard.get("entries", [])
                 if p["student_id"] == student_id),
                None
            )
            await manager.send_personal(websocket, {
                "type": "participant_detail",
                "data": participant,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    elif command == "ping":
        await manager.send_personal(websocket, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })


# ============================================================================
# Dashboard Real-time Updates WebSocket
# ============================================================================
@router.websocket("/dashboard/stream")
async def dashboard_stream(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time dashboard updates.
    
    Streams:
    - KPI updates every 30 seconds
    - Activity feed updates
    - System alerts
    """
    admin = await verify_admin_token(token, db)
    if not admin:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await manager.connect(websocket, "conversations", "dashboard", admin.id)
    
    try:
        from app.services.admin.dashboard_service import DashboardService
        
        while True:
            try:
                # Push dashboard stats every 30 seconds
                service = DashboardService(db)
                stats = await service.get_dashboard_stats()
                
                await manager.send_personal(websocket, {
                    "type": "stats_update",
                    "data": stats,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Get recent activity
                activity = await service.get_activity_feed(limit=10)
                await manager.send_personal(websocket, {
                    "type": "activity_update",
                    "data": activity,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                await asyncio.sleep(30)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Dashboard stream error: {e}")
                await asyncio.sleep(60)
    
    finally:
        manager.disconnect(websocket)