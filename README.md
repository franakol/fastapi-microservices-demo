# FastAPI Microservices with Nginx Gateway

A comprehensive demonstration of microservices architecture using FastAPI for service development and Nginx as an API gateway, orchestrated with Docker Compose.

## 🏗️ Architecture Overview

This project demonstrates a microservices architecture with:

- **User Service**: User registration and management
- **Order Service**: Order placement and tracking
- **Payment Service**: Payment processing simulation
- **Nginx Gateway**: API routing, load balancing, and SSL termination
- **PostgreSQL**: Database for each service
- **Docker Compose**: Service orchestration

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Python 3.9+ (for local development)
- Git

### Running the Application

```bash
# Clone the repository
git clone https://github.com/your-username/fastapi-microservices-demo.git
cd fastapi-microservices-demo

# Start all services
docker-compose up --build

# Access the services
# API Gateway: http://localhost
# User Service: http://localhost/users
# Order Service: http://localhost/orders  
# Payment Service: http://localhost/payments
```

## 📋 API Endpoints

### User Service (`/users`)
- `POST /users` - Register a new user
- `GET /users/{user_id}` - Get user details
- `GET /users` - List all users

### Order Service (`/orders`)
- `POST /orders` - Place a new order
- `GET /orders/{order_id}` - Get order details
- `GET /orders` - List orders for a user

### Payment Service (`/payments`)
- `POST /payments` - Process a payment
- `GET /payments/{payment_id}` - Get payment status
- `GET /payments` - List payments

## 🏢 Project Structure

```
fastapi-microservices-demo/
├── services/
│   ├── user-service/
│   ├── order-service/
│   └── payment-service/
├── nginx/
│   ├── nginx.conf
│   └── ssl/
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
├── docker-compose.yml
├── docker-compose.prod.yml
└── README.md
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

The Nginx gateway is configured for:
- API routing to microservices
- SSL termination
- Rate limiting
- CORS handling
- Health checks

## 📊 Monitoring

The project includes monitoring setup with:
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **Health checks**: Service availability monitoring

Access monitoring:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

## 🚀 Production Deployment

### Using Docker Compose

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

Kubernetes manifests are available in the `k8s/` directory:

```bash
kubectl apply -f k8s/
```

## 🔐 Security

- JWT-based authentication
- Rate limiting via Nginx
- Input validation and sanitization
- CORS configuration
- SSL/TLS encryption

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
- Microservices architecture patterns
- FastAPI best practices
- Nginx as API gateway
- Docker containerization
- Service communication
- Database design for microservices
- Monitoring and observability
- Production deployment strategies
