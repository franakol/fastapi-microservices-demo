"""
Payment Service - FastAPI Microservice
Handles payment processing and transaction management
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
import random
from typing import List

from .database import engine, SessionLocal, Base
from .models import Payment
from .schemas import PaymentCreate, PaymentResponse, PaymentStatus
from .auth import verify_token
from .config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Payment Service",
    description="Microservice for payment processing and transaction management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logging
logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter('payment_service_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('payment_service_request_duration_seconds', 'Request duration')
PAYMENT_COUNT = Counter('payments_processed_total', 'Total payments processed', ['status'])

# Security
security = HTTPBearer(auto_error=False)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get current user (optional for some endpoints)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return payload.get("sub")

def simulate_payment_processing() -> bool:
    """Simulate payment processing with random success/failure"""
    # 90% success rate for demo purposes
    return random.random() < 0.9

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Update metrics
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(process_time)
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "payment-service"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def process_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_db)
):
    """Process a payment transaction"""
    logger.info("Processing payment", order_id=payment.order_id, amount=payment.amount)
    
    # Validate payment amount
    if payment.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be greater than zero"
        )
    
    # Create payment record
    db_payment = Payment(
        order_id=payment.order_id,
        user_id=payment.user_id,
        amount=payment.amount,
        currency=payment.currency,
        payment_method=payment.payment_method,
        status=PaymentStatus.PENDING
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    # Simulate payment processing
    payment_success = simulate_payment_processing()
    
    if payment_success:
        db_payment.status = PaymentStatus.COMPLETED
        db_payment.transaction_id = f"txn_{db_payment.id}_{int(time.time())}"
        PAYMENT_COUNT.labels(status="success").inc()
        logger.info("Payment processed successfully", payment_id=db_payment.id)
    else:
        db_payment.status = PaymentStatus.FAILED
        db_payment.failure_reason = "Payment declined by provider"
        PAYMENT_COUNT.labels(status="failed").inc()
        logger.warning("Payment processing failed", payment_id=db_payment.id)
    
    db.commit()
    db.refresh(db_payment)
    
    return db_payment

@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payment by ID"""
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if db_payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Check if user has access to this payment
    if current_user_id and str(db_payment.user_id) != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return db_payment

@app.get("/payments", response_model=List[PaymentResponse])
async def list_payments(
    skip: int = 0,
    limit: int = 100,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List payments for current user"""
    if current_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    user_id = int(current_user_id)
    payments = db.query(Payment).filter(
        Payment.user_id == user_id
    ).offset(skip).limit(limit).all()
    
    return payments

@app.post("/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refund a payment"""
    if current_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if db_payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if str(db_payment.user_id) != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if db_payment.status != PaymentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed payments can be refunded"
        )
    
    # Process refund
    db_payment.status = PaymentStatus.REFUNDED
    db.commit()
    
    logger.info("Payment refunded", payment_id=payment_id)
    return {"message": "Payment refunded successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
