# Architecture

## 1. Input
Traffic video uploaded through FastAPI.

## 2. Detection & Tracking
Ultralytics YOLO detects common road users:
- person
- bicycle
- car
- motorcycle
- bus
- truck

YOLO's tracking mode assigns persistent IDs.

## 3. Motion Features
For each tracked object:
- center point
- short trajectory history
- approximate pixel velocity

## 4. Risk Engine
For every nearby object pair:
- normalized distance
- relative motion
- approximate time-to-collision
- combined risk score

## 5. Event Engine
High and critical interactions are stored as near-miss / road-risk events.

## 6. Persistence
SQLite stores:
- analysis runs
- event counts
- overall risk
- individual risk events

## 7. Output
- annotated MP4
- JSON event report
- REST API endpoints

## Future upgrades
- camera calibration
- real-world meters / km/h
- lane detection
- perspective transform
- ByteTrack-specific configuration
- heatmaps
- accident-zone clustering
- pedestrian-specific safety rules
- React dashboard
