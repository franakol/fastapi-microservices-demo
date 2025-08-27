# Orchestrating Python Microservices with FastAPI and Nginx: A Complete Guide

*Published on August 27, 2025*

## Introduction

Microservices architecture has become the gold standard for building scalable, maintainable applications. In this comprehensive guide, we'll explore how to build and orchestrate Python microservices using FastAPI for service development and Nginx as an API gateway, all containerized with Docker for seamless deployment.

## Why Microservices?

Traditional monolithic applications, while simple to develop initially, often become bottlenecks as they grow. Microservices offer several advantages:

- **Scalability**: Scale individual services based on demand
- **Independence**: Teams can develop and deploy services independently
- **Resilience**: Failure in one service doesn't bring down the entire system
- **Technology Diversity**: Use the best tool for each job

## The Technology Stack

Our microservices stack consists of:

- **FastAPI**: Modern, fast Python web framework with automatic API documentation
- **Nginx**: High-performance reverse proxy and API gateway
- **PostgreSQL**: Robust relational database with separate schemas per service
- **Redis**: In-memory cache for session management and performance
- **Docker**: Containerization for consistent deployment
- **Prometheus & Grafana**: Monitoring and observability

## Architecture Overview

Our demo system implements a simple e-commerce backend with three core services:

1. **User Service**: Handles user registration, authentication, and profile management
2. **Order Service**: Manages order placement, tracking, and status updates
3. **Payment Service**: Processes payments and handles transaction management

All services communicate through well-defined REST APIs and are fronted by an Nginx gateway that handles routing, SSL termination, and load balancing.

## Building the User Service

The User Service is the foundation of our system, handling authentication and user management:

```python
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from .models import User
from .schemas import UserCreate, UserResponse
from .auth import create_access_token, verify_password

app = FastAPI(title="User Service")

@app.post("/users", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    
    return db_user
```

Key features of our User Service:
- JWT-based authentication
- Password hashing with bcrypt
- Comprehensive input validation
- Prometheus metrics integration
- Health check endpoints

## Implementing the Order Service

The Order Service orchestrates the ordering process and communicates with other services:

```python
@app.post("/orders", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify user exists
    if not await verify_user_exists(user_id):
        raise HTTPException(status_code=400, detail="User not found")
    
    # Calculate total and create order
    total_amount = sum(item.price * item.quantity for item in order.items)
    db_order = Order(user_id=user_id, total_amount=total_amount)
    
    # Process payment
    payment_success = await process_payment(db_order.id, total_amount, user_id)
    db_order.status = "confirmed" if payment_success else "failed"
    
    return db_order
```

The Order Service demonstrates:
- Inter-service communication via HTTP
- Transaction management across services
- Comprehensive error handling
- Status tracking and updates

## Payment Service Implementation

The Payment Service simulates payment processing with proper transaction management:

```python
@app.post("/payments", response_model=PaymentResponse)
async def process_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    # Create payment record
    db_payment = Payment(
        order_id=payment.order_id,
        amount=payment.amount,
        status=PaymentStatus.PENDING
    )
    
    # Simulate payment processing
    payment_success = simulate_payment_processing()
    
    if payment_success:
        db_payment.status = PaymentStatus.COMPLETED
        db_payment.transaction_id = f"txn_{db_payment.id}_{int(time.time())}"
    else:
        db_payment.status = PaymentStatus.FAILED
        db_payment.failure_reason = "Payment declined"
    
    return db_payment
```

## Nginx as API Gateway

Nginx serves as our API gateway, providing:

```nginx
upstream user-service {
    server user-service:8000;
}

upstream order-service {
    server order-service:8000;
}

server {
    listen 80;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    # User Service routes
    location /users {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://user-service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Order Service routes
    location /orders {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://order-service;
    }
}
```

Benefits of using Nginx:
- **Load Balancing**: Distribute traffic across service instances
- **SSL Termination**: Handle HTTPS encryption/decryption
- **Rate Limiting**: Protect services from abuse
- **Caching**: Improve performance with response caching
- **Security**: Add security headers and CORS handling

## Docker Orchestration

Docker Compose ties everything together:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: microservices_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    
  user-service:
    build: ./services/user-service
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/user_db
    depends_on:
      - postgres
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - user-service
      - order-service
      - payment-service
```

## Monitoring and Observability

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
