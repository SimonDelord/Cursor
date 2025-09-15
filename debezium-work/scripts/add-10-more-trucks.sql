-- Add 10 more truck locations for real-time Debezium testing
-- These will be IDs 11-20 to continue from existing data

USE trucks;

INSERT INTO location (id, latitude, longitude) VALUES
(11, 37.7849, -122.4094),  -- San Francisco Financial District
(12, 34.0522, -118.2437),  -- Los Angeles Downtown
(13, 41.8781, -87.6298),   -- Chicago Loop
(14, 40.7589, -73.9851),   -- New York Times Square
(15, 25.7617, -80.1918),   -- Miami Downtown
(16, 39.7392, -104.9903),  -- Denver Downtown
(17, 47.6062, -122.3321),  -- Seattle Downtown
(18, 30.2672, -97.7431),   -- Austin Downtown
(19, 33.7490, -84.3880),   -- Atlanta Downtown
(20, 42.3601, -71.0589);   -- Boston Downtown
