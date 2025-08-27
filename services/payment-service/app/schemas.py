"""
Pydantic schemas for Payment Service
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentCreate(BaseModel):
    """Schema for creating a payment"""
    order_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    payment_method: str = Field(default="credit_card", max_length=50)


class PaymentResponse(BaseModel):
    """Schema for payment response"""
    id: int
    order_id: int
    user_id: int
    amount: float
    currency: str
    payment_method: str
    status: PaymentStatus
    transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
