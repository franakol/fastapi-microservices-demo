# FastAPI Microservices Demo with Nginx Gateway

A production-ready demonstration of microservices architecture using FastAPI, Nginx as an API gateway, and comprehensive monitoring with Prometheus and Grafana.

## 🏗️ Architecture Overview

This project showcases a complete microservices ecosystem with:

- **User Service**: JWT authentication, user registration and profile management
- **Order Service**: Order processing with inter-service communication
- **Payment Service**: Payment processing with transaction management and refunds
- **Nginx Gateway**: API routing, rate limiting, SSL termination, and documentation routing
- **PostgreSQL**: Separate databases per service with health checks
- **Redis**: Caching and session management
- **Prometheus & Grafana**: Comprehensive monitoring and observability
- **Docker Compose**: Full service orchestration with health checks

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Python 3.9+ (for local development)
- Git

### Running the Application

```bash
# Clone the repository
git clone https://github.com/franakol/fastapi-microservices-demo.git
cd fastapi-microservices-demo

# Copy environment variables
cp .env.example .env
# Edit .env with your preferred values

# Generate SSL certificates (required for HTTPS support)
./scripts/generate-ssl.sh

# Start all services
docker-compose up --build

# Access the services
# API Gateway: http://localhost (HTTP) or https://localhost (HTTPS)
# User Service API: http://localhost/users/
# Order Service API: http://localhost/orders/  
# Payment Service API: http://localhost/payments/
```

### SSL Certificate Setup

The application supports both HTTP and HTTPS. SSL certificates are required for HTTPS functionality but are gitignored for security reasons.

#### Option 1: Generate Self-Signed Certificates (Recommended for Development)

```bash
# Create SSL directory if it doesn't exist
mkdir -p nginx/ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/nginx.key \
  -out nginx/ssl/nginx.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

#### Option 2: Use the Provided Script

```bash
# Make the script executable and run it
chmod +x scripts/generate-ssl.sh
./scripts/generate-ssl.sh
```

#### Option 3: Use Your Own Certificates

If you have your own SSL certificates, place them in the `nginx/ssl/` directory:
- `nginx/ssl/nginx.crt` - SSL certificate
- `nginx/ssl/nginx.key` - Private key

**Note**: The `nginx/ssl/` directory and its contents are gitignored to prevent accidental commit of private keys.

## 📋 API Endpoints

### User Service (`/users/`)
- `POST /users/register` - Register a new user
- `POST /users/login` - Authenticate and get JWT token
- `GET /users/me` - Get current user profile (requires auth)
- `GET /users/{user_id}` - Get user details (requires auth)
- `GET /users/` - List all users (requires auth)

### Order Service (`/orders/`)
- `POST /orders/` - Place a new order (requires auth)
- `GET /orders/{order_id}` - Get order details (requires auth)
- `GET /orders/` - List orders for current user (requires auth)
- `PATCH /orders/{order_id}/status` - Update order status (requires auth)

### Payment Service (`/payments/`)
- `POST /payments/` - Process a payment
- `GET /payments/{payment_id}` - Get payment status (requires auth)
- `GET /payments/` - List payments for current user (requires auth)
- `POST /payments/{payment_id}/refund` - Refund a payment (requires auth)

## 🌐 Browser Access

### API Documentation
- **User Service Docs**: http://localhost/users/docs
- **Order Service Docs**: http://localhost/orders/docs
- **Payment Service Docs**: http://localhost/payments/docs
- **Health Check**: http://localhost/health

### Gateway Endpoints
- **HTTP**: http://localhost (port 80)
- **HTTPS**: https://localhost (port 443, self-signed cert)
- **Health Check**: http://localhost/health

### Monitoring Dashboards
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

### Testing the API

```bash
# Check health
curl http://localhost/health

# Register a user
curl -X POST "http://localhost/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123"
  }'

# Login and get JWT token
curl -X POST "http://localhost/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'

# Create an order (use JWT token from login)
curl -X POST "http://localhost/orders/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "items": [
      {"name": "Product 1", "quantity": 2, "price": 29.99},
      {"name": "Product 2", "quantity": 1, "price": 49.99}
    ]
  }'
```

## 🏢 Project Structure

```
fastapi-microservices-demo/
├── services/                   # Microservices
│   ├── user-service/
│   │   ├── app/
│   │   │   ├── main.py        # FastAPI app with custom Swagger UI
│   │   │   ├── models.py      # SQLAlchemy models
│   │   │   ├── schemas.py     # Pydantic schemas
│   │   │   ├── auth.py        # JWT authentication
│   │   │   ├── database.py    # Database configuration
│   │   │   └── config.py      # Service configuration
│   │   ├── Dockerfile         # Service containerization
│   │   └── requirements.txt   # Python dependencies
│   ├── order-service/         # Same structure as user-service
│   └── payment-service/       # Same structure as user-service
├── nginx/                     # API Gateway
│   ├── nginx.conf            # Main Nginx configuration
│   ├── conf.d/
│   │   └── locations.conf    # Critical routing configuration
│   └── ssl/                  # SSL certificates
├── monitoring/               # Observability
│   ├── prometheus.yml       # Metrics collection config
│   └── grafana/            # Dashboards and provisioning
├── docker-compose.yml       # Service orchestration
├── .env.example            # Environment template
├── init.sql                # Database initialization
├── README.md               # This documentation
└── blog-post.md           # Comprehensive tutorial
```

## 🛠️ Development

### Local Development Setup

```bash
# Set up virtual environment for each service
cd services/user-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run service locally
uvicorn app.main:app --reload --port 8001
```

### Running Tests

```bash
# Run tests for all services
docker-compose -f docker-compose.test.yml up --build

# Run tests for specific service
cd services/user-service
pytest
```

## 🔧 Configuration

### Environment Variables

Each service uses environment variables for configuration:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection for caching
- `JWT_SECRET`: Secret key for JWT tokens
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Nginx Configuration

The Nginx gateway provides advanced routing and features:

**API Documentation Routing** (Key Innovation):
- **Exact Match Routes**: `/users/docs`, `/orders/docs`, `/payments/docs`
- **Custom Swagger UI**: Each service serves custom HTML pointing to correct OpenAPI JSON
- **OpenAPI JSON Routes**: Service-specific `/service/openapi.json` endpoints
- **Browser Cache Handling**: Proper headers to prevent stale documentation

**Core Features**:
- **API Routing**: Clean paths to microservices (`/users/`, `/orders/`, `/payments/`)
- **Rate Limiting**: 10 requests/second with burst of 20
- **Load Balancing**: Ready for multiple service instances
- **SSL/TLS Support**: Self-signed certificates for HTTPS
- **Security Headers**: XSS protection, content type sniffing prevention
- **Health Checks**: Gateway and service health monitoring
- **Error Handling**: Consistent JSON error responses

## 📊 Monitoring & Observability

Comprehensive monitoring stack included:

**Prometheus Metrics**:
- Request counts and duration histograms
- Service health and availability
- Custom business metrics per service
- Automatic service discovery via Docker DNS

**Grafana Dashboards**:
- Service performance visualization
- Request rate and error tracking
- Database connection monitoring
- System resource utilization

**Health Checks**:
- Individual service health endpoints (`/health`)
- Database connectivity verification
- Redis cache availability
- Gateway health monitoring

**Access Points**:
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Health Check**: http://localhost/health

## 🚀 Production Deployment

### Docker Compose Production

```bash
# Production deployment with optimized settings
docker-compose -f docker-compose.yml up -d

# Scale services as needed
docker-compose up -d --scale user-service=3 --scale order-service=2
```

### Production Considerations

**Security Enhancements**:
- Replace self-signed certificates with valid SSL certificates
- Use proper secrets management (Docker secrets, HashiCorp Vault)
- Implement proper CORS policies for your domain
- Enable Nginx access logs and security monitoring

**Performance Optimization**:
- Configure PostgreSQL connection pooling
- Implement Redis caching strategies
- Set up database read replicas for scaling
- Configure Nginx worker processes based on CPU cores

**Monitoring & Alerting**:
- Set up Grafana alerting rules
- Configure Prometheus alert manager
- Implement distributed tracing with OpenTelemetry
- Set up log aggregation (ELK stack or similar)

## 🔐 Security Features

**Authentication & Authorization**:
- JWT-based authentication with secure token handling
- Protected endpoints requiring valid bearer tokens
- User-specific data access controls

**Network Security**:
- Rate limiting (10 req/s with burst of 20) via Nginx
- SSL/TLS encryption with certificate management
- Security headers (XSS protection, content type sniffing prevention)
- CORS configuration for cross-origin requests

**Data Protection**:
- Input validation and sanitization using Pydantic schemas
- SQL injection prevention via SQLAlchemy ORM
- Environment-based secrets management
- Database connection security

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

For questions and support:
- Create an issue on GitHub
- Contact: fakol@podgh.com
- Python Rwanda Community

## 🎯 Learning Objectives

This project demonstrates:

**Microservices Architecture**:
- Service decomposition and bounded contexts
- Inter-service communication patterns
- Database per service pattern
- API gateway pattern implementation

**FastAPI Best Practices**:
- Custom Swagger UI for proxy environments
- Pydantic schemas for data validation
- SQLAlchemy ORM integration
- JWT authentication implementation
- Prometheus metrics integration

**Infrastructure & DevOps**:
- Nginx as API gateway with advanced routing
- Docker containerization and multi-stage builds
- Docker Compose orchestration with health checks
- Monitoring with Prometheus and Grafana
- Production deployment considerations

**Key Innovation**: Custom Swagger UI implementation that solves the common problem of incorrect API documentation routing in microservices behind an API gateway.
