CREATE TABLE IF NOT EXISTS user (
  id TEXT PRIMARY KEY UNIQUE NOT NULL,  -- VMS user UUID stored as text (no UUID support in SQLITE)
  username TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS event (
  id TEXT PRIMARY KEY UNIQUE NOT NULL,  -- UUID stored as text (no UUID support in SQLITE)
  user_id TEXT,
  name TEXT NOT NULL,
  start TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finish TIMESTAMP,  -- If NULL event is in progress
  comment TEXT,
  FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE IF NOT EXISTS camera (
  id TEXT PRIMARY KEY UNIQUE NOT NULL,  -- VMS camera UUID stored as text (no UUID support in SQLITE)
  name TEXT NOT NULL,
  comment TEXT,
  threshold FLOAT DEFAULT 0.5
);

CREATE TABLE If NOT EXISTS event_cameras (
  event_id TEXT,
  camera_id TEXT,
  FOREIGN KEY (event_id) REFERENCES event (id),
  FOREIGN KEY (camera_id) REFERENCES camera (id),
  PRIMARY KEY (event_id, camera_id)
);

CREATE TABLE If NOT EXISTS camera_engagement_rate (
  timestamp_ INT NOT NULL,  -- Store milliseconds since epoch. Don't convert.
  rate FLOAT NOT NULL,
  camera_id TEXT,
  FOREIGN KEY (camera_id) REFERENCES camera (id),
  PRIMARY KEY (timestamp_, camera_id)
);
