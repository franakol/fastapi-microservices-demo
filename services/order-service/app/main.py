"""
Order Service - FastAPI Microservice
Handles order placement, tracking, and management
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
import httpx
from typing import List

from .database import engine, SessionLocal, Base
from .models import Order, OrderItem
from .schemas import OrderCreate, OrderResponse, OrderItemCreate, OrderStatus
from .auth import verify_token
from .config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Order Service",
    description="Microservice for order management and tracking",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
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
REQUEST_COUNT = Counter('order_service_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('order_service_request_duration_seconds', 'Request duration')

# Security
security = HTTPBearer()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return payload.get("sub")

async def verify_user_exists(user_id: int) -> bool:
    """Verify user exists by calling user service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.user_service_url}/users/{user_id}")
            return response.status_code == 200
    except Exception as e:
        logger.error("Failed to verify user", user_id=user_id, error=str(e))
        return False

async def process_payment(order_id: int, amount: float, user_id: int) -> bool:
    """Process payment by calling payment service"""
    try:
        async with httpx.AsyncClient() as client:
            payment_data = {
                "order_id": order_id,
                "amount": amount,
                "user_id": user_id,
                "currency": "USD"
            }
            response = await client.post(f"{settings.payment_service_url}/payments", json=payment_data)
            return response.status_code == 201
    except Exception as e:
        logger.error("Failed to process payment", order_id=order_id, error=str(e))
        return False

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
    return {"status": "healthy", "service": "order-service"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order: OrderCreate,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new order"""
    user_id = int(current_user_id)
    logger.info("Creating new order", user_id=user_id)
    
    # Verify user exists
    if not await verify_user_exists(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Calculate total amount
    total_amount = sum(item.price * item.quantity for item in order.items)
    
    # Create order
    db_order = Order(
        user_id=user_id,
        total_amount=total_amount,
        status=OrderStatus.PENDING
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Create order items
    for item_data in order.items:
        db_item = OrderItem(
            order_id=db_order.id,
            product_name=item_data.product_name,
            quantity=item_data.quantity,
            price=item_data.price
        )
        db.add(db_item)
    
    db.commit()
    
    # Process payment
    payment_success = await process_payment(db_order.id, total_amount, user_id)
    
    if payment_success:
        db_order.status = OrderStatus.CONFIRMED
    else:
        db_order.status = OrderStatus.FAILED
    
    db.commit()
    db.refresh(db_order)
    
    logger.info("Order created", order_id=db_order.id, status=db_order.status)
    return db_order

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order by ID"""
    user_id = int(current_user_id)
    
    db_order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == user_id
    ).first()
    
    if db_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return db_order

@app.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    skip: int = 0,
    limit: int = 100,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List orders for current user"""
    user_id = int(current_user_id)
    
    orders = db.query(Order).filter(
        Order.user_id == user_id
    ).offset(skip).limit(limit).all()
    
    return orders

@app.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    new_status: OrderStatus,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update order status"""
    user_id = int(current_user_id)
    
    db_order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == user_id
    ).first()
    
    if db_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    db_order.status = new_status
    db.commit()
    
    logger.info("Order status updated", order_id=order_id, status=new_status)
    return {"message": "Order status updated successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
