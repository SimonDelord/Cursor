-- Create trucks database with location table and sample data
-- For testing Debezium MySQL connector

-- Create the trucks database
CREATE DATABASE IF NOT EXISTS trucks;
USE trucks;

-- Create location table for truck tracking
CREATE TABLE IF NOT EXISTS location (
    id INT AUTO_INCREMENT PRIMARY KEY,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_coords (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert 10 truck location entries (realistic coordinates around major cities)
INSERT INTO location (latitude, longitude) VALUES
(40.7128, -74.0060),   -- New York City
(34.0522, -118.2437),  -- Los Angeles
(41.8781, -87.6298),   -- Chicago
(29.7604, -95.3698),   -- Houston
(33.4484, -112.0740),  -- Phoenix
(39.9526, -75.1652),   -- Philadelphia
(32.7767, -96.7970),   -- Dallas
(37.7749, -122.4194),  -- San Francisco
(47.6062, -122.3321),  -- Seattle
(25.7617, -80.1918);   -- Miami

-- Grant permissions to debezium user for this database
GRANT ALL PRIVILEGES ON trucks.* TO 'debezium'@'%';
FLUSH PRIVILEGES;

-- Verify the data was inserted
SELECT 'Trucks database created successfully!' as status;
SELECT COUNT(*) as total_locations FROM location;
SELECT 'Sample truck locations:' as message;
SELECT id, latitude, longitude, created_at FROM location ORDER BY id LIMIT 5;
