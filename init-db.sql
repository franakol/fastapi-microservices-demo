-- Create databases for each microservice
CREATE DATABASE user_db;
CREATE DATABASE order_db;
CREATE DATABASE payment_db;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE user_db TO postgres;
GRANT ALL PRIVILEGES ON DATABASE order_db TO postgres;
GRANT ALL PRIVILEGES ON DATABASE payment_db TO postgres;
