# RoadWatch AI

RoadWatch AI is a traffic video analysis project I built to detect potentially risky interactions between road users. It takes a traffic/CCTV video as input, detects and tracks vehicles and pedestrians, follows their movement across frames, and identifies interactions that may represent a near miss.

The project uses YOLO for object detection and ByteTrack for tracking. Risk is estimated using the relative motion of tracked objects along with Time to Closest Approach (TTC) and Closest Point of Approach (CPA).

I also built a FastAPI backend for video processing and a React dashboard for uploading videos, viewing results, checking detected risk events, and accessing previous analysis runs.

## How it works

The analysis pipeline is roughly:

```text
Traffic Video
     ↓
YOLO Detection
     ↓
ByteTrack Tracking
     ↓
Object Trajectories
     ↓
Relative Motion
     ↓
TTC / CPA Calculation
     ↓
Risk Scoring
     ↓
Near-Miss Confirmation
     ↓
Results + Annotated Video
```

Instead of treating every close pair of objects as a near miss, the system checks whether the objects are actually approaching each other and looks at their recent motion. High-risk interactions also need to persist across multiple analyzed frames before an event is recorded. This helped reduce noisy one-frame detections.

## Features

- Traffic video upload and analysis
- YOLO-based road-user detection
- Multi-object tracking with ByteTrack
- Trajectory history for tracked objects
- Relative-motion analysis
- TTC and CPA based risk estimation
- LOW, MEDIUM, HIGH and CRITICAL risk levels
- Temporal confirmation of near-miss events
- Annotated output video
- Analysis history stored in SQLite
- Separate dashboard, video analysis, risk events and history views
- FastAPI endpoints with Swagger documentation

## Tech Stack

**Computer Vision:** Python, YOLO, OpenCV, ByteTrack, NumPy, PyTorch

**Backend:** FastAPI, SQLAlchemy, SQLite, Uvicorn

**Frontend:** React, Vite, JavaScript, CSS

## Project Structure

```text
RoadWatch_AI/
│
├── roadwatch/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── video_analyzer.py
│   │   │   ├── risk_engine.py
│   │   │   └── event_engine.py
│   │   └── main.py
│   │
│   ├── sample_videos/
│   ├── uploads/
│   ├── outputs/
│   ├── tests/
│   └── requirements.txt
│
└── frontend/
    └── roadwatch_frontend/
        ├── src/
        ├── package.json
        └── vite.config.js
```

## Running the project

### Backend

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
cd roadwatch
python -m pip install -r requirements.txt
```

Start the FastAPI server:

```powershell
python -m uvicorn app.main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

Swagger documentation is available at:

```text
http://127.0.0.1:8000/docs
```

### Frontend

Open another terminal and move to the frontend directory:

```powershell
cd frontend\roadwatch_frontend
npm install
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

## Risk calculation

For each relevant pair of tracked road users, the system looks at factors such as their distance in the frame, relative velocity, whether they are approaching each other, estimated time to closest approach, and closest point of approach.

The resulting score is grouped into four levels:

| Score | Risk |
|---|---|
| 0–34 | LOW |
| 35–59 | MEDIUM |
| 60–77 | HIGH |
| 78–100 | CRITICAL |

Only confirmed HIGH or CRITICAL interactions are recorded as near-miss events.

## API

The main endpoints are:

```text
POST /api/v1/analyze/video
GET  /api/v1/runs
GET  /api/v1/runs/{run_id}
```

`POST /api/v1/analyze/video` processes an uploaded traffic video and returns the analysis result.

The other two endpoints are used by the dashboard to retrieve previous analysis runs and their event details.

## Dashboard

The frontend has four sections:

- **Dashboard** – overview of the system and latest analysis
- **Video Analysis** – upload a video and view the analysis results
- **Risk Events** – inspect detected near-miss events
- **Analysis History** – view previous analysis runs stored by the backend

## A note about TTC and CPA

The current project works with motion in video coordinates. The TTC and CPA values are therefore estimates based on movement in the image rather than calibrated real-world distance measurements.

Getting actual vehicle speed or distance in metres would require camera calibration and perspective information for the particular road/camera setup.

## Current limitations

The quality of the results depends on the video, camera angle, visibility and object detection/tracking quality. Occlusion can also affect track continuity.

Inference is currently CPU-based on my development system, so processing a video takes longer than real time. The analysis uses frame sampling on CPU to keep the processing practical while retaining enough temporal information for motion analysis.

## Possible improvements

Some things I would like to explore further are camera calibration for real-world measurements, lane-aware risk analysis, GPU deployment, background processing with live progress updates, and evaluation on a labelled near-miss dataset.

## Author

**Anshika Rawat**  
B.Tech – Artificial Intelligence & Machine Learning