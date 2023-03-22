CREATE TABLE aircraft_data (
device_type CHAR(1) NOT NULL,
device_id CHAR(6) NOT NULL PRIMARY KEY,
aircraft_model VARCHAR(50) NOT NULL,
registration VARCHAR(10) NOT NULL,
cn VARCHAR(10) NOT NULL,
tracked BOOLEAN NOT NULL,
identified BOOLEAN NOT NULL
);

CREATE INDEX device_id_index ON aircraft_data (DEVICE_ID);