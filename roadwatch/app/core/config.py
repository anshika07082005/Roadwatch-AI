from dataclasses import dataclass
from pathlib import Path

import torch


BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    BASE_DIR: Path = BASE_DIR

    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"

    DATABASE_URL: str = (
        f"sqlite:///{BASE_DIR / 'traffic_risk.db'}"
    )

    YOLO_MODEL: str = "yolov8n.pt"

    # -------------------------------------------------
    # HARDWARE
    # -------------------------------------------------

    DEVICE: str = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    # -------------------------------------------------
    # YOLO
    # -------------------------------------------------

    YOLO_CONFIDENCE: float = 0.40
    YOLO_IOU: float = 0.50

    CPU_IMAGE_SIZE: int = 416
    GPU_IMAGE_SIZE: int = 640

    # CPU uses efficient temporal sampling.
    # GPU automatically processes the full stream.
    CPU_TARGET_ANALYSIS_FPS: float = 6.0

    # -------------------------------------------------
    # TRACKING
    # -------------------------------------------------

    HISTORY_LENGTH: int = 12
    MIN_HISTORY_FOR_RISK: int = 4

    # -------------------------------------------------
    # RISK ENGINE
    # -------------------------------------------------

    MAX_TTC_SECONDS: float = 4.0

    MAX_PAIR_DISTANCE_RATIO: float = 0.16

    HIGH_RISK_THRESHOLD: float = 60.0
    CRITICAL_RISK_THRESHOLD: float = 78.0

    # Predicted closest approach relative
    # to average object size.
    MAX_CPA_SCALE: float = 1.75

    # -------------------------------------------------
    # EVENT VALIDATION
    # -------------------------------------------------

    # Risk must persist across multiple analyzed
    # observations before becoming an event.
    EVENT_CONFIRMATION_FRAMES: int = 2

    EVENT_COOLDOWN_SECONDS: float = 2.5


settings = Settings()

settings.UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

settings.OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)