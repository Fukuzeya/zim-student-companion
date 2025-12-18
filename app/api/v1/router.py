# ============================================================================
# Main API Router
# ============================================================================
from fastapi import APIRouter

from app.api.v1 import admin, admin_content, admin_operations, admin_websocket

api_router = APIRouter()

# Import and include route modules - with error handling
try:
    from app.api.v1 import auth
    api_router.include_router(auth.router)
except ImportError:
    print("⚠️ auth routes not found")

try:
    from app.api.v1 import students
    api_router.include_router(students.router)
except ImportError:
    print("⚠️ students routes not found")

try:
    from app.api.v1 import parents
    api_router.include_router(parents.router)
except ImportError:
    print("⚠️ parents routes not found")

try:
    from app.api.v1 import practice
    api_router.include_router(practice.router)
except ImportError:
    print("⚠️ practice routes not found")

try:
    from app.api.v1 import competitions
    api_router.include_router(competitions.router)
except ImportError:
    print("⚠️ competitions routes not found")

try:
    from app.api.v1 import payments
    api_router.include_router(payments.router)
except ImportError:
    print("⚠️ payments routes not found")

try:
    from app.api.v1 import admin
    api_router.include_router(admin.router)
except ImportError:
    print("⚠️ admin routes not found")

try:
    from app.api.v1 import webhooks
    api_router.include_router(webhooks.router)
except ImportError:
    print("⚠️ webhooks routes not found")
    
try:
    from app.api.v1 import rag_test
    api_router.include_router(rag_test.router)
except ImportError:
    print("⚠️ rag_test routes not found")
    
# Add a test endpoint
@api_router.get("/test")
async def test_endpoint():
    return {"message": "API is working!", "version": "v1"}

# Dashboard, Users, Students endpoints
api_router.include_router(admin.router)
# Content (Subjects, Topics, Questions), Documents, Conversations
api_router.include_router(admin_content.router)
# Competitions, Payments, Analytics, Notifications, System
api_router.include_router(admin_operations.router)
# WebSocket endpoints for real-time features
api_router.include_router(admin_websocket.router)
