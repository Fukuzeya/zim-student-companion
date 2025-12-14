# ============================================================================
# Payment API Endpoints
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.payment import PaymentMethod
from app.services.payments.subscription_manager import SubscriptionManager

router = APIRouter(prefix="/payments", tags=["payments"])

class InitiatePaymentRequest(BaseModel):
    plan_id: UUID
    payment_method: PaymentMethod
    phone: Optional[str] = None
    email: Optional[str] = None

class PaymentStatusResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None

@router.get("/plans")
async def get_subscription_plans(
    db: AsyncSession = Depends(get_db)
):
    """Get all available subscription plans"""
    manager = SubscriptionManager(db)
    plans = await manager.get_available_plans()
    return {"plans": plans}

@router.post("/subscribe")
async def initiate_subscription(
    request: InitiatePaymentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Initiate a subscription payment"""
    manager = SubscriptionManager(db)
    result = await manager.initiate_subscription(
        user_id=current_user.id,
        plan_id=request.plan_id,
        payment_method=request.payment_method,
        phone=request.phone or current_user.phone_number,
        email=request.email or current_user.email
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result

@router.get("/status/{payment_id}")
async def check_payment_status(
    payment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Check payment status"""
    manager = SubscriptionManager(db)
    result = await manager.check_payment_status(payment_id)
    return result

@router.get("/subscription")
async def get_subscription_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current subscription status"""
    manager = SubscriptionManager(db)
    return await manager.check_subscription_status(current_user.id)

@router.post("/webhook/paynow")
async def paynow_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handle Paynow payment webhook"""
    try:
        data = await request.form()
        data_dict = dict(data)
        
        manager = SubscriptionManager(db)
        background_tasks.add_task(manager.handle_paynow_callback, data_dict)
        
        return {"status": "received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel subscription renewal"""
    manager = SubscriptionManager(db)
    result = await manager.cancel_subscription(current_user.id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result