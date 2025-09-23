-- Add 20 more truck locations for real-time Debezium testing
-- These will be IDs 112-131 to continue from existing data

USE trucks;

INSERT INTO location (id, latitude, longitude) VALUES
(112, 44.9537, -93.0900),   -- Minneapolis, MN
(113, 39.7391, -104.9847),  -- Denver, CO (Downtown)
(114, 35.2271, -80.8431),   -- Charlotte, NC
(115, 41.2524, -95.9980),   -- Omaha, NE
(116, 36.7378, -119.7871),  -- Fresno, CA
(117, 43.0389, -87.9065),   -- Milwaukee, WI
(118, 35.7796, -78.6382),   -- Raleigh, NC
(119, 41.5868, -93.6250),   -- Des Moines, IA
(120, 42.9634, -85.6681),   -- Grand Rapids, MI
(121, 29.9511, -90.0715),   -- New Orleans, LA
(122, 32.0835, -81.0998),   -- Savannah, GA
(123, 47.0379, -122.9015),  -- Olympia, WA
(124, 39.1612, -75.5264),   -- Wilmington, DE
(125, 41.4993, -81.6944),   -- Cleveland, OH
(126, 36.1627, -86.7816),   -- Nashville, TN (Duplicate coordinate test)
(127, 38.2904, -92.6390),   -- Jefferson City, MO
(128, 44.2619, -72.5806),   -- Montpelier, VT
(129, 43.2081, -71.5376),   -- Concord, NH
(130, 44.3106, -69.7795),   -- Augusta, ME
(131, 58.3019, -134.4197);  -- Juneau, AK

