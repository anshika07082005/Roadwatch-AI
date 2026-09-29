from fastapi import FastAPI

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from fastapi.staticfiles import (
    StaticFiles,
)

from app.api.routes import router

from app.core.config import settings

from app.db.database import (
    Base,
    engine,
)


Base.metadata.create_all(
    bind=engine
)


app = FastAPI(
    title="RoadWatch AI",

    version="2.0.0",

    description=(
        "Computer-vision traffic safety "
        "intelligence platform for road-user "
        "detection, multi-object tracking, "
        "trajectory modelling, video-space TTC, "
        "closest-point-of-approach analysis and "
        "explainable near-miss risk detection."
    ),
)


app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "*",
    ],

    allow_credentials=True,

    allow_methods=[
        "*",
    ],

    allow_headers=[
        "*",
    ],
)


# Allows frontend to play generated
# annotated videos directly.
app.mount(
    "/outputs",

    StaticFiles(
        directory=str(
            settings.OUTPUT_DIR
        )
    ),

    name="outputs",
)


app.include_router(
    router,
    prefix="/api/v1",
)


@app.get("/")
def root():

    return {
        "project": (
            "RoadWatch AI"
        ),

        "version": (
            "2.0.0"
        ),

        "status": (
            "running"
        ),

        "device": (
            settings.DEVICE
        ),

        "docs": (
            "/docs"
        ),
    }


@app.get("/health")
def health():

    return {
        "status": (
            "healthy"
        ),

        "service": (
            "RoadWatch AI API"
        ),

        "version": (
            "2.0.0"
        ),

        "inference_device": (
            settings.DEVICE
        ),

        "model": (
            settings.YOLO_MODEL
        ),
    }