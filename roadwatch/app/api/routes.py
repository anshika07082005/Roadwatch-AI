from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import (
    AnalysisRun,
    RiskEvent,
)
from app.services.video_analyzer import (
    VideoAnalyzer,
)


router = APIRouter()


# -------------------------------------------------
# Load YOLO ONCE
# -------------------------------------------------
#
# Previously VideoAnalyzer() was created inside
# every request. That meant the YOLO model could
# be initialized repeatedly.
#
# Now it is created once when the application starts
# and reused for subsequent video analyses.

video_analyzer = VideoAnalyzer()


SUPPORTED_VIDEO_TYPES = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
}


@router.post("/analyze/video")
async def analyze_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    original_filename = (
        file.filename
        or "uploaded_video.mp4"
    )

    suffix = Path(
        original_filename
    ).suffix.lower()

    if (
        suffix
        not in SUPPORTED_VIDEO_TYPES
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Upload a supported video "
                "file: MP4, AVI, MOV or MKV."
            ),
        )

    run_id = str(
        uuid4()
    )

    input_path = (
        settings.UPLOAD_DIR
        / f"{run_id}{suffix}"
    )

    output_path = (
        settings.OUTPUT_DIR
        / f"{run_id}_annotated.mp4"
    )

    # Stream uploaded file directly to disk
    # instead of loading the complete video
    # into RAM with await file.read().
    try:

        with input_path.open(
            "wb"
        ) as buffer:

            copyfileobj(
                file.file,
                buffer,
            )

    finally:

        await file.close()

    run = AnalysisRun(
        id=run_id,
        filename=original_filename,
        status="processing",
    )

    db.add(
        run
    )

    db.commit()

    try:

        result = (
            video_analyzer.process_video(
                input_path=input_path,
                output_path=output_path,
            )
        )

        run.status = (
            "completed"
        )

        run.total_frames = (
            result["total_frames"]
        )

        run.total_events = len(
            result["events"]
        )

        run.risk_score = (
            result["summary"]
            ["overall_risk_score"]
        )

        run.output_path = str(
            output_path
        )

        for event in result["events"]:

            db.add(
                RiskEvent(
                    run_id=run_id,

                    frame_index=(
                        event[
                            "frame_index"
                        ]
                    ),

                    object_a=(
                        event[
                            "object_a"
                        ]
                    ),

                    object_b=(
                        event[
                            "object_b"
                        ]
                    ),

                    risk_level=(
                        event[
                            "risk_level"
                        ]
                    ),

                    risk_score=(
                        event[
                            "risk_score"
                        ]
                    ),

                    estimated_ttc=(
                        event[
                            "estimated_ttc"
                        ]
                    ),
                )
            )

        db.commit()

        return {

            "run_id": (
                run_id
            ),

            "filename": (
                original_filename
            ),

            **result,
        }

    except Exception as exc:

        db.rollback()

        failed_run = (
            db.query(
                AnalysisRun
            )
            .filter(
                AnalysisRun.id
                == run_id
            )
            .first()
        )

        if failed_run:

            failed_run.status = (
                "failed"
            )

            db.commit()

        # Remove incomplete output file
        if output_path.exists():

            try:
                output_path.unlink()
            except OSError:
                pass

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@router.get("/runs")
def list_runs(
    db: Session = Depends(
        get_db
    ),
):

    runs = (
        db.query(
            AnalysisRun
        )
        .order_by(
            AnalysisRun
            .created_at
            .desc()
        )
        .all()
    )

    return [

        {
            "id": run.id,

            "filename": (
                run.filename
            ),

            "status": (
                run.status
            ),

            "total_frames": (
                run.total_frames
            ),

            "total_events": (
                run.total_events
            ),

            "risk_score": (
                run.risk_score
            ),

            "created_at": (
                run.created_at
            ),
        }

        for run in runs
    ]


@router.get(
    "/runs/{run_id}"
)
def get_run(
    run_id: str,
    db: Session = Depends(
        get_db
    ),
):

    run = (
        db.query(
            AnalysisRun
        )
        .filter(
            AnalysisRun.id
            == run_id
        )
        .first()
    )

    if not run:

        raise HTTPException(
            status_code=404,
            detail=(
                "Analysis run "
                "not found."
            ),
        )

    events = (
        db.query(
            RiskEvent
        )
        .filter(
            RiskEvent.run_id
            == run_id
        )
        .order_by(
            RiskEvent.frame_index
        )
        .all()
    )

    return {

        "id": run.id,

        "filename": (
            run.filename
        ),

        "status": (
            run.status
        ),

        "total_frames": (
            run.total_frames
        ),

        "total_events": (
            run.total_events
        ),

        "risk_score": (
            run.risk_score
        ),

        "output_path": (
            run.output_path
        ),

        "events": [

            {
                "frame_index": (
                    event.frame_index
                ),

                "object_a": (
                    event.object_a
                ),

                "object_b": (
                    event.object_b
                ),

                "risk_level": (
                    event.risk_level
                ),

                "risk_score": (
                    event.risk_score
                ),

                "estimated_ttc": (
                    event.estimated_ttc
                ),
            }

            for event in events
        ],
    }