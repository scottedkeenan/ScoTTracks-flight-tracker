UPDATE daily_flights
INNER JOIN sites ON daily_flights.takeoff_airfield = sites.name
INNER JOIN airfields on sites.airfield_id = airfields.id
SET daily_flights.takeoff_airfield = airfields.id WHERE daily_flights.takeoff_airfield NOT REGEXP '^[0-9]+$';

UPDATE daily_flights
INNER JOIN sites ON daily_flights.landing_airfield = sites.name
INNER JOIN airfields on sites.airfield_id = airfields.id
SET daily_flights.landing_airfield = airfields.id WHERE daily_flights.landing_airfield NOT REGEXP '^[0-9]+$';

