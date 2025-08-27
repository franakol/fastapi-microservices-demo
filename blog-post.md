# Orchestrating Python Microservices with FastAPI and Nginx: A Complete Guide

*Published on August 27, 2025*

## Introduction

Microservices architecture has become the gold standard for building scalable, maintainable applications. In this comprehensive guide, we'll explore how to build and orchestrate Python microservices using FastAPI for service development and Nginx as an API gateway, all containerized with Docker for seamless deployment.

This tutorial provides two paths: **building from scratch** for learning purposes, and **cloning the repository** for quick setup. Both approaches will result in a fully functional microservices system with proper API documentation routing.

## Why Microservices?

Traditional monolithic applications, while simple to develop initially, often become bottlenecks as they grow. Microservices offer several advantages:

- **Scalability**: Scale individual services based on demand
- **Independence**: Teams can develop and deploy services independently
- **Resilience**: Failure in one service doesn't bring down the entire system
- **Technology Diversity**: Use the best tool for each job

## Quick Start Options

### Option 1: Clone the Repository (Recommended for Quick Setup)

```bash
# Clone the repository
git clone https://github.com/franakol/fastapi-microservices-demo.git
cd fastapi-microservices-demo

# Start all services
docker-compose up --build

# Access the services
# - Gateway: http://localhost
# - User Service Docs: http://localhost/users/docs
# - Order Service Docs: http://localhost/orders/docs
# - Payment Service Docs: http://localhost/payments/docs
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

### Option 2: Build from Scratch (Learning Path)

Follow the detailed step-by-step instructions below to understand each component and build the system from the ground up.

## The Technology Stack

Our microservices stack consists of:

- **FastAPI**: Modern, fast Python web framework with automatic API documentation
- **Nginx**: High-performance reverse proxy and API gateway
- **PostgreSQL**: Robust relational database with separate schemas per service
- **Redis**: In-memory cache for session management and performance
- **Docker**: Containerization for consistent deployment
- **Prometheus & Grafana**: Monitoring and observability

## Project Structure Overview

```
fastapi-microservices-demo/
├── services/                    # Microservices directory
│   ├── user-service/           # User management service
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py         # FastAPI application
│   │   │   ├── models.py       # SQLAlchemy models
│   │   │   ├── schemas.py      # Pydantic schemas
│   │   │   ├── database.py     # Database configuration
│   │   │   ├── auth.py         # Authentication logic
│   │   │   └── config.py       # Service configuration
│   │   ├── Dockerfile          # Service containerization
│   │   └── requirements.txt    # Python dependencies
│   ├── order-service/          # Order management service
│   │   └── [same structure as user-service]
│   └── payment-service/        # Payment processing service
│       └── [same structure as user-service]
├── nginx/                      # API Gateway configuration
│   ├── nginx.conf             # Main Nginx configuration
│   ├── conf.d/
│   │   └── locations.conf     # Service routing configuration
│   └── ssl/                   # SSL certificates (auto-generated)
├── monitoring/                 # Observability stack
│   ├── prometheus.yml         # Prometheus configuration
│   └── grafana/              # Grafana dashboards
├── docker-compose.yml         # Service orchestration
├── .env.example              # Environment variables template
├── README.md                 # Project documentation
└── blog-post.md             # This comprehensive guide
```

## Architecture Overview

Our demo system implements a simple e-commerce backend with three core services:

1. **User Service**: Handles user registration, authentication, and profile management
2. **Order Service**: Manages order placement, tracking, and status updates
3. **Payment Service**: Processes payments and handles transaction management

All services communicate through well-defined REST APIs and are fronted by an Nginx gateway that handles routing, SSL termination, and load balancing.

## Step-by-Step Implementation Guide

### Prerequisites

Before starting, ensure you have:
- Docker and Docker Compose installed
- Python 3.9+ (for local development)
- Git (for version control)
- A code editor (VS Code recommended)

### Step 1: Project Setup

```bash
# Create project directory
mkdir fastapi-microservices-demo
cd fastapi-microservices-demo

# Create directory structure
mkdir -p services/{user-service,order-service,payment-service}/app
mkdir -p nginx/{conf.d,ssl}
mkdir -p monitoring/grafana

# Initialize git repository
git init
```

### Step 2: Environment Configuration

Create `.env` file:
```bash
# Database configuration
POSTGRES_DB=microservices_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# JWT configuration
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis configuration
REDIS_URL=redis://redis:6379
```

### Step 3: Building the User Service

The User Service is the foundation of our system, handling authentication and user management.

#### Create User Service Structure

```bash
cd services/user-service
```

**requirements.txt**:
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pydantic==2.5.0
prometheus-client==0.19.0
structlog==23.2.0
httpx==0.25.2
```

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**app/main.py** (User Service):

```python
"""
User Service - FastAPI Microservice
Handles user registration, authentication, and profile management
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
from typing import List

from .database import engine, SessionLocal, Base
from .models import User
from .schemas import UserCreate, UserResponse, UserLogin, Token
from .auth import verify_token, create_access_token, get_password_hash, verify_password
from .config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="User Service",
    description="Microservice for user management and authentication",
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

# Prometheus metrics
REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')

# Security
security = HTTPBearer()

# Logger
logger = structlog.get_logger()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Middleware for metrics
@app.middleware("http")
async def add_metrics(request, call_next):
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
    return {"status": "healthy", "service": "user-service"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    logger.info("Registering new user", email=user.email)
    
    # Check if user already exists
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info("User registered successfully", user_id=db_user.id)
    return db_user

@app.post("/users/login", response_model=Token)
async def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    logger.info("User login attempt", email=user_credentials.username)
    
    # Find user by email
    user = db.query(User).filter(User.email == user_credentials.username).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    logger.info("User logged in successfully", user_id=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all users (paginated)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@app.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    user_id = verify_token(credentials.credentials)
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
```

Key features of our User Service:
- JWT-based authentication
- Password hashing with bcrypt
- Comprehensive input validation
- Prometheus metrics integration
- Health check endpoints

### Step 4: Building the Order Service

The Order Service orchestrates the ordering process and communicates with other services.

```python
"""
Order Service - FastAPI Microservice
Handles order placement, tracking, and management
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
import httpx
from typing import List

from .database import engine, SessionLocal, Base
from .models import Order, OrderItem
from .schemas import OrderCreate, OrderResponse, OrderItemCreate, OrderItemResponse
from .auth import verify_token
from .config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app with custom docs
app = FastAPI(
    title="Order Service",
    description="Microservice for order management and tracking",
    version="1.0.0",
    docs_url=None,  # Disable default docs
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

# Prometheus metrics
REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')

# Security
security = HTTPBearer()
logger = structlog.get_logger()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.middleware("http")
async def add_metrics(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(process_time)
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI that works with nginx proxy"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css">
<link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
<title>{app.title} - Swagger UI</title>
</head>
<body>
<div id="swagger-ui">
</div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
<script>
const ui = SwaggerUIBundle({{
    url: '/orders/openapi.json',
    dom_id: '#swagger-ui',
    layout: 'BaseLayout',
    deepLinking: true,
    showExtensions: true,
    showCommonExtensions: true,
    oauth2RedirectUrl: window.location.origin + '/docs/oauth2-redirect',
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
    ],
}})
</script>
</body>
</html>"""
    return HTMLResponse(content=html)

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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Create a new order"""
    user_id = verify_token(credentials.credentials)
    logger.info("Creating order", user_id=user_id, items_count=len(order.items))
    
    # Verify user exists by calling user service
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"http://user-service:8000/users/{user_id}",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User not found"
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User service unavailable"
            )
    
    # Calculate total amount
    total_amount = sum(item.price * item.quantity for item in order.items)
    
    # Create order
    db_order = Order(
        user_id=user_id,
        total_amount=total_amount,
        status="pending"
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Create order items
    for item in order.items:
        db_item = OrderItem(
            order_id=db_order.id,
            product_name=item.product_name,
            quantity=item.quantity,
            price=item.price
        )
        db.add(db_item)
    
    db.commit()
    
    # Process payment
    try:
        async with httpx.AsyncClient() as client:
            payment_data = {
                "order_id": db_order.id,
                "user_id": user_id,
                "amount": total_amount
            }
            payment_response = await client.post(
                "http://payment-service:8000/payments",
                json=payment_data,
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            
            if payment_response.status_code == 201:
                db_order.status = "confirmed"
            else:
                db_order.status = "failed"
                
    except httpx.RequestError:
        db_order.status = "failed"
        logger.error("Payment service unavailable", order_id=db_order.id)
    
    db.commit()
    db.refresh(db_order)
    
    logger.info("Order created", order_id=db_order.id, status=db_order.status)
    return db_order

@app.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    skip: int = 0,
    limit: int = 100,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """List orders for current user"""
    user_id = verify_token(credentials.credentials)
    orders = db.query(Order).filter(Order.user_id == user_id).offset(skip).limit(limit).all()
    return orders

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get order by ID"""
    user_id = verify_token(credentials.credentials)
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == user_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order
```

The Order Service demonstrates:
- Inter-service communication via HTTP
- Transaction management across services
- Comprehensive error handling
- Status tracking and updates

### Step 5: Building the Payment Service

The Payment Service simulates payment processing with proper transaction management.

```python
"""
Payment Service - FastAPI Microservice
Handles payment processing and transaction management
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
from typing import List, Optional

from .database import engine, SessionLocal, Base
from .models import Payment
from .schemas import PaymentCreate, PaymentResponse, PaymentStatus
from .auth import verify_token
from .config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app with custom docs
app = FastAPI(
    title="Payment Service",
    description="Microservice for payment processing and transaction management",
    version="1.0.0",
    docs_url=None,  # Disable default docs
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

# Prometheus metrics
REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')

# Security
security = HTTPBearer()
logger = structlog.get_logger()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.middleware("http")
async def add_metrics(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(process_time)
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI that works with nginx proxy"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css">
<link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
<title>{app.title} - Swagger UI</title>
</head>
<body>
<div id="swagger-ui">
</div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
<script>
const ui = SwaggerUIBundle({{
    url: '/payments/openapi.json',
    dom_id: '#swagger-ui',
    layout: 'BaseLayout',
    deepLinking: true,
    showExtensions: true,
    showCommonExtensions: true,
    oauth2RedirectUrl: window.location.origin + '/docs/oauth2-redirect',
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
    ],
}})
</script>
</body>
</html>"""
    return HTMLResponse(content=html)

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
            detail="Payment amount must be greater than 0"
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
    
    # Simulate payment processing (80% success rate)
    import random
    payment_success = random.random() > 0.2
    
    if payment_success:
        db_payment.status = PaymentStatus.COMPLETED
        db_payment.transaction_id = f"txn_{db_payment.id}_{int(time.time())}"
        logger.info("Payment processed successfully", payment_id=db_payment.id)
    else:
        db_payment.status = PaymentStatus.FAILED
        db_payment.failure_reason = "Payment declined by processor"
        logger.warning("Payment failed", payment_id=db_payment.id)
    
    db.commit()
    db.refresh(db_payment)
    
    return db_payment

@app.get("/payments", response_model=List[PaymentResponse])
async def list_payments(
    skip: int = 0,
    limit: int = 100,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """List payments for current user"""
    user_id = verify_token(credentials.credentials)
    payments = db.query(Payment).filter(Payment.user_id == user_id).offset(skip).limit(limit).all()
    return payments

@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get payment by ID"""
    user_id = verify_token(credentials.credentials)
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.user_id == user_id
    ).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return payment

@app.post("/payments/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(
    payment_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Refund a payment"""
    user_id = verify_token(credentials.credentials)
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.user_id == user_id
    ).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.status != PaymentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed payments can be refunded"
        )
    
    payment.status = PaymentStatus.REFUNDED
    db.commit()
    
    logger.info("Payment refunded", payment_id=payment.id)
    return payment
```

The Payment Service demonstrates:
- Payment processing simulation with realistic success/failure rates
- Transaction management and status tracking
- Refund functionality for completed payments
- Custom Swagger UI for proper documentation routing
- Comprehensive error handling and validation

### Step 6: Nginx Configuration for API Gateway

Nginx serves as our API gateway, providing routing, load balancing, and SSL termination. The configuration includes special handling for API documentation routing.

**nginx/nginx.conf**:

```nginx
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;
    
    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    # Upstream definitions
    upstream user-service {
        server user-service:8000;
    }
    
    upstream order-service {
        server order-service:8000;
    }
    
    upstream payment-service {
        server payment-service:8000;
    }
    
    # Main server block
    server {
        listen 80;
        server_name localhost;
        
        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        
        # Include location blocks
        include /etc/nginx/conf.d/locations.conf;
        
        # Default error pages
        error_page 404 /404.html;
        error_page 500 502 503 504 /50x.html;
        
        location = /50x.html {
            root /usr/share/nginx/html;
        }
    }
}
```

**nginx/conf.d/locations.conf** - Critical for API Documentation Routing:

```nginx
# Health check endpoint
location /health {
    access_log off;
    return 200 "healthy\n";
    add_header Content-Type text/plain;
}

# Exact match for documentation routes (highest priority)
location = /users/docs {
    proxy_pass http://user-service/docs;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location = /orders/docs {
    proxy_pass http://order-service/docs;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location = /payments/docs {
    proxy_pass http://payment-service/docs;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# OpenAPI JSON endpoints
location = /users/openapi.json {
    proxy_pass http://user-service/openapi.json;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location = /orders/openapi.json {
    proxy_pass http://order-service/openapi.json;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location = /payments/openapi.json {
    proxy_pass http://payment-service/openapi.json;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# User service routes
location /users/ {
    proxy_pass http://user-service/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Order service routes  
location /orders/ {
    proxy_pass http://order-service/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Payment service routes
location /payments/ {
    proxy_pass http://payment-service/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Key Nginx Configuration Points:**

1. **Exact Match Location Blocks**: Using `location = /service/docs` ensures highest priority routing for documentation endpoints
2. **OpenAPI JSON Routing**: Separate exact match blocks for `/service/openapi.json` endpoints
3. **Custom Swagger UI**: Each service serves custom HTML that points to the correct OpenAPI JSON URL
4. **Proxy Headers**: Proper forwarding of client information to backend services
5. **Rate Limiting**: Protection against abuse with configurable burst limits

### Step 7: Docker Compose Orchestration

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  # Database
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: microservices_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Services
  user-service:
    build: ./services/user-service
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/user_db
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET_KEY=your-secret-key-here
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  order-service:
    build: ./services/order-service
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/order_db
      - USER_SERVICE_URL=http://user-service:8000
      - PAYMENT_SERVICE_URL=http://payment-service:8000
    depends_on:
      postgres:
        condition: service_healthy
      user-service:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  payment-service:
    build: ./services/payment-service
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/payment_db
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # API Gateway
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - user-service
      - order-service
      - payment-service
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning

volumes:
  postgres_data:
  grafana_data:
```

## Running the Application

### Quick Start

1. **Clone the repository**:
```bash
git clone https://github.com/franakol/fastapi-microservices-demo.git
cd fastapi-microservices-demo
```

2. **Copy environment variables**:
```bash
cp .env.example .env
# Edit .env with your preferred values
```

3. **Start all services**:
```bash
docker-compose up --build
```

4. **Access the services**:
- **API Gateway**: http://localhost
- **User Service Docs**: http://localhost/users/docs
- **Order Service Docs**: http://localhost/orders/docs  
- **Payment Service Docs**: http://localhost/payments/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Testing the API

**Register a user**:
```bash
curl -X POST "http://localhost/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

**Login to get JWT token**:
```bash
curl -X POST "http://localhost/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

**Create an order** (use the JWT token from login):
```bash
curl -X POST "http://localhost/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "items": [
      {"name": "Product 1", "quantity": 2, "price": 29.99},
      {"name": "Product 2", "quantity": 1, "price": 49.99}
    ]
  }'
```

## Troubleshooting

### Common Issues

1. **Documentation shows wrong service**: Clear browser cache or use incognito mode
2. **Services not starting**: Check Docker logs with `docker-compose logs [service-name]`
3. **Database connection errors**: Ensure PostgreSQL is healthy before services start
4. **Port conflicts**: Modify ports in docker-compose.yml if needed

### Debugging Tips

- **Check service health**: `curl http://localhost/health`
- **View logs**: `docker-compose logs -f [service-name]`
- **Restart specific service**: `docker-compose restart [service-name]`
- **Rebuild after changes**: `docker-compose up --build [service-name]`

## Architecture Benefits

This microservices architecture provides:

- **Scalability**: Each service can be scaled independently
- **Fault Isolation**: Failure in one service doesn't affect others
- **Technology Diversity**: Different services can use different tech stacks
- **Team Independence**: Teams can work on services independently
- **Deployment Flexibility**: Services can be deployed separately

## Production Considerations

For production deployment, consider:

- **Security**: Implement proper authentication, HTTPS, and secrets management
- **Monitoring**: Enhanced logging, distributed tracing, and alerting
- **Scalability**: Load balancing, auto-scaling, and resource optimization
- **Data Management**: Database per service, event sourcing, CQRS patterns
- **CI/CD**: Automated testing, building, and deployment pipelines
- **Infrastructure**: Kubernetes, service mesh, and cloud-native tools

## Next Steps

Potential enhancements:

1. **API Versioning**: Implement versioning strategy for backward compatibility
2. **Event-Driven Architecture**: Use message queues for async communication
3. **Distributed Tracing**: Add OpenTelemetry for request tracing
4. **Circuit Breakers**: Implement resilience patterns
5. **API Rate Limiting**: Per-user and per-endpoint rate limiting
6. **Caching Strategy**: Redis caching for frequently accessed data
7. **Database Optimization**: Connection pooling, read replicas, sharding

## Conclusion

This FastAPI microservices demo showcases a production-ready architecture with proper API gateway routing, comprehensive monitoring, and scalable design patterns. The key innovation is the custom Swagger UI implementation that ensures correct API documentation routing through the Nginx gateway.

The project demonstrates modern microservices best practices while maintaining simplicity for educational purposes. Each component is containerized, monitored, and designed for independent scaling and deployment.

The setup includes comprehensive monitoring with Prometheus and Grafana:

### Prometheus Configuration
- **Metrics Collection**: Scrapes metrics from all FastAPI services on `/metrics` endpoints
- **Service Discovery**: Automatically discovers services via Docker DNS
- **Retention**: Stores metrics with configurable retention periods
- **Alerting**: Can be extended with AlertManager for notifications

### Grafana Dashboards
- **Service Metrics**: Request rates, response times, error rates
- **Infrastructure**: CPU, memory, disk usage
- **Custom Dashboards**: Business metrics and KPIs
- **Access**: http://localhost:3000 (admin/admin)

### Available Metrics
Each FastAPI service exposes Prometheus metrics:
```bash
# View service metrics
curl http://localhost:9090/targets  # Prometheus targets
curl http://localhost/users/metrics  # Direct service access (if exposed)
```

### Setting Up Custom Dashboards
1. Access Grafana at http://localhost:3000
2. Login with admin/admin
3. Import pre-built dashboards or create custom ones
4. Configure data sources to point to Prometheus
5. Set up alerts and notifications

### Prometheus Metrics Implementation
Each service exposes metrics:
```python
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time

REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')

@app.middleware("http")
async def add_metrics(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(time.time() - start_time)
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### Monitoring Best Practices
- **Health Checks**: Each service implements `/health` endpoints
- **Structured Logging**: Use structured logs for better observability
- **Distributed Tracing**: Consider adding OpenTelemetry for request tracing
- **Error Tracking**: Monitor error rates and types across services

### Health Checks
Every service implements health checks:
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user-service"}
```

## Deployment Strategies

### Local Development
```bash
# Start all services
docker-compose up --build

# Scale specific services
docker-compose up --scale user-service=3
```

### Production Deployment
```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d

# Rolling updates
docker-compose -f docker-compose.prod.yml up -d --no-deps user-service
```

## Best Practices

### 1. Service Design
- **Single Responsibility**: Each service should have one clear purpose
- **Database per Service**: Avoid shared databases between services
- **API Versioning**: Plan for API evolution from the start

### 2. Communication
- **Async Where Possible**: Use async/await for I/O operations
- **Circuit Breakers**: Implement fallback mechanisms for service failures
- **Timeouts**: Set appropriate timeouts for inter-service calls

### 3. Security
- **Authentication**: Centralize authentication in the API gateway
- **Authorization**: Implement fine-grained permissions per service
- **Input Validation**: Validate all inputs at service boundaries

### 4. Monitoring
- **Distributed Tracing**: Track requests across service boundaries
- **Centralized Logging**: Aggregate logs from all services
- **Alerting**: Set up alerts for critical metrics

## Common Challenges and Solutions

### Service Discovery
**Challenge**: Services need to find and communicate with each other.
**Solution**: Use Docker's built-in DNS resolution or external service discovery tools like Consul.

### Data Consistency
**Challenge**: Maintaining consistency across distributed data.
**Solution**: Implement eventual consistency patterns and saga patterns for distributed transactions.

### SSL Configuration

The nginx gateway includes SSL/TLS support with self-signed certificates:

```bash
# SSL certificates are automatically generated in the nginx/ssl/ directory
# Access via HTTPS (accept browser security warning for self-signed cert)
curl -k https://localhost/

# Test SSL configuration
openssl s_client -connect localhost:443 -servername localhost
```

### Testing
**Challenge**: Testing interactions between multiple services.
**Solution**: Use contract testing, integration tests, and test containers.

## Testing the Setup

### Browser Access
Access the API documentation through your browser:
- **Gateway Overview**: http://localhost/
- **User Service Docs**: http://localhost/user-docs
- **Order Service Docs**: http://localhost/order-docs  
- **Payment Service Docs**: http://localhost/payment-docs

### API Testing with curl

Once everything is running, you can test the services:

```bash
# Test gateway health
curl http://localhost/health

# Register a new user
curl -X POST http://localhost/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "username": "demo",
    "full_name": "Demo User",
    "password": "password123"
  }'

# Login and get JWT token
curl -X POST http://localhost/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "password123"
  }'

# Use the JWT token for authenticated requests
TOKEN="your-jwt-token-here"

# Create an order (requires authentication)
curl -X POST http://localhost/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "items": [
      {"name": "Product 1", "quantity": 2, "price": 29.99}
    ],
    "total_amount": 59.98
  }'

# Process payment (requires authentication)
curl -X POST http://localhost/payments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "order_id": 1,
    "amount": 59.98,
    "payment_method": "credit_card"
  }'
```

### SSL Testing

```bash
# Test HTTPS endpoint (accept self-signed certificate warning)
curl -k https://localhost/

# Verify SSL certificate details
openssl s_client -connect localhost:443 -servername localhost -brief

# Test SSL with specific cipher
curl -k --tlsv1.2 https://localhost/health
```

## Performance Optimization

### Database Optimization
- Use connection pooling
- Implement proper indexing
- Consider read replicas for read-heavy services

### Caching Strategy
- Cache frequently accessed data in Redis
- Implement cache invalidation strategies
- Use CDN for static content

### Load Balancing
- Distribute traffic across service instances
- Implement health checks for load balancers
- Use sticky sessions when necessary

## Conclusion

Building microservices with FastAPI and Nginx provides a robust, scalable foundation for modern applications. Key takeaways:

1. **Start Simple**: Begin with a few well-defined services
2. **Plan for Growth**: Design services to be independently scalable
3. **Monitor Everything**: Implement comprehensive monitoring from day one
4. **Automate Deployment**: Use Docker and CI/CD for consistent deployments
5. **Security First**: Implement security at every layer

The complete source code for this tutorial is available on GitHub, including all configuration files, Docker setups, and deployment scripts. This foundation can be extended with additional services, advanced monitoring, and production-grade security features.

## Next Steps

- Implement API versioning strategies
- Add distributed tracing with Jaeger
- Set up CI/CD pipelines
- Implement advanced security features
- Add comprehensive test suites
- Explore Kubernetes deployment

---

*This blog post accompanies the workshop "Orchestrating Python Microservices with FastAPI and Nginx" presented at GIZ Digital Transformation Center, Kigali on August 27, 2025.*
