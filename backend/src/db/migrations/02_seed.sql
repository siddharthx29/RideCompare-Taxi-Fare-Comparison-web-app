-- Migration 02: Seed initial mock data for testing

-- Seed mock user
INSERT INTO users (name, email)
VALUES ('Demo User', 'demo@ridecompare.com')
ON CONFLICT (email) DO NOTHING;

-- Seed some mock searches for the past 7 days to populate the dashboard charts
INSERT INTO searches (source, destination, source_lat, source_lng, dest_lat, dest_lng, distance_km, duration_min, cheapest_provider, fastest_provider, best_provider, selected_provider, savings, created_at)
VALUES
('Indiranagar, Bengaluru', 'Koramangala, Bengaluru', 12.971891, 77.641151, 12.935192, 77.624480, 5.8, 18.0, 'Rapido', 'Uber', 'Ola', 'Rapido', 35.0, NOW() - INTERVAL '6 days'),
('Whitefield, Bengaluru', 'Electronic City, Bengaluru', 12.9698, 77.7499, 12.8399, 77.6770, 24.5, 52.0, 'Rapido', 'Uber', 'Uber', 'Uber', 15.0, NOW() - INTERVAL '5 days'),
('Majestic, Bengaluru', 'Kempegowda International Airport', 12.9779, 77.5724, 13.1986, 77.7066, 36.2, 45.0, 'Ola', 'Uber', 'Ola', 'Ola', 50.0, NOW() - INTERVAL '4 days'),
('HSR Layout, Bengaluru', 'Jayanagar, Bengaluru', 12.9116, 77.6388, 12.9298, 77.5833, 8.1, 24.0, 'Rapido', 'Ola', 'Ola', 'Ola', 20.0, NOW() - INTERVAL '3 days'),
('Malleswaram, Bengaluru', 'MG Road, Bengaluru', 12.9960, 77.5712, 12.9733, 77.6117, 7.2, 22.0, 'Rapido', 'Uber', 'Rapido', 'Rapido', 40.0, NOW() - INTERVAL '2 days'),
('Koramangala, Bengaluru', 'Indiranagar, Bengaluru', 12.9351, 77.6244, 12.9718, 77.6411, 6.0, 20.0, 'Rapido', 'Ola', 'Ola', 'Ola', 25.0, NOW() - INTERVAL '1 day'),
('MG Road, Bengaluru', 'Indiranagar, Bengaluru', 12.9733, 77.6117, 12.9718, 77.6411, 4.2, 12.0, 'Rapido', 'Uber', 'Uber', 'Uber', 10.0, NOW());

-- Seed some mock analytics logs
INSERT INTO analytics (provider, clicks, redirects, fare, created_at)
VALUES
('Uber', 25, 20, 320.0, NOW() - INTERVAL '3 days'),
('Ola', 30, 25, 290.0, NOW() - INTERVAL '2 days'),
('Rapido', 45, 40, 120.0, NOW() - INTERVAL '1 day'),
('Uber', 15, 12, 280.0, NOW()),
('Ola', 18, 15, 260.0, NOW()),
('Rapido', 22, 20, 110.0, NOW());
