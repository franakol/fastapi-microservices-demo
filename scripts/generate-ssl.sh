#!/bin/bash

# SSL Certificate Generation Script for FastAPI Microservices Demo
# This script generates self-signed SSL certificates for development use

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}FastAPI Microservices Demo - SSL Certificate Generator${NC}"
echo "=================================================="

# Create SSL directory if it doesn't exist
SSL_DIR="nginx/ssl"
if [ ! -d "$SSL_DIR" ]; then
    echo -e "${YELLOW}Creating SSL directory: $SSL_DIR${NC}"
    mkdir -p "$SSL_DIR"
fi

# Check if certificates already exist
if [ -f "$SSL_DIR/nginx.crt" ] && [ -f "$SSL_DIR/nginx.key" ]; then
    echo -e "${YELLOW}SSL certificates already exist. Do you want to regenerate them? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Using existing SSL certificates.${NC}"
        exit 0
    fi
fi

echo -e "${YELLOW}Generating self-signed SSL certificate...${NC}"

# Generate private key and certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/nginx.key" \
    -out "$SSL_DIR/nginx.crt" \
    -subj "/C=US/ST=Development/L=Local/O=FastAPI-Microservices-Demo/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1,IP:::1"

# Set appropriate permissions
chmod 600 "$SSL_DIR/nginx.key"
chmod 644 "$SSL_DIR/nginx.crt"

echo -e "${GREEN}✓ SSL certificates generated successfully!${NC}"
echo -e "${GREEN}✓ Certificate: $SSL_DIR/nginx.crt${NC}"
echo -e "${GREEN}✓ Private Key: $SSL_DIR/nginx.key${NC}"
echo ""
echo -e "${YELLOW}Note: These are self-signed certificates for development use only.${NC}"
echo -e "${YELLOW}Your browser will show a security warning - this is expected.${NC}"
echo ""
echo -e "${GREEN}You can now start the application with: docker-compose up --build${NC}"
