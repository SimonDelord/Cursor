-- Add 10 more truck locations for real-time Debezium demo testing
-- These will be IDs 102-111 for the demo.trucks.location topic

USE trucks;

INSERT INTO location (id, latitude, longitude) VALUES
(102, 47.6062, -122.3321),  -- Seattle, WA
(103, 39.7392, -104.9903),  -- Denver, CO  
(104, 30.2672, -97.7431),   -- Austin, TX
(105, 33.7490, -84.3880),   -- Atlanta, GA
(106, 42.3601, -71.0589),   -- Boston, MA
(107, 25.7617, -80.1918),   -- Miami, FL
(108, 32.7767, -96.7970),   -- Dallas, TX
(109, 45.5152, -122.6784),  -- Portland, OR
(110, 39.9612, -82.9988),   -- Columbus, OH
(111, 36.1627, -86.7816);   -- Nashville, TN

