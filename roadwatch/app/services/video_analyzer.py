from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from time import perf_counter
from typing import Dict, Tuple

import cv2
from ultralytics import YOLO

from app.core.config import settings
from app.services.event_engine import EventEngine
from app.services.risk_engine import (
    MotionState,
    classify_pair_risk,
)


ROAD_USER_CLASSES = {
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "truck",
}

YOLO_CLASS_IDS = [0, 1, 2, 3, 5, 7]


class VideoAnalyzer:

    def __init__(self):
        self.model = YOLO(settings.YOLO_MODEL)
        self.device = settings.DEVICE

    # -------------------------------------------------
    # VELOCITY
    # -------------------------------------------------

    @staticmethod
    def _velocity(
        points,
        analyzed_fps: float,
    ) -> Tuple[float, float]:

        if len(points) < 3:
            return 0.0, 0.0

        # Lightweight smoothed velocity estimation.
        # Uses displacement over multiple observations
        # instead of expensive polynomial regression.
        lookback = min(
            len(points) - 1,
            4,
        )

        old_point = points[-(lookback + 1)]
        new_point = points[-1]

        elapsed_seconds = (
            lookback
            / max(analyzed_fps, 1.0)
        )

        if elapsed_seconds <= 0:
            return 0.0, 0.0

        vx = (
            new_point[0] - old_point[0]
        ) / elapsed_seconds

        vy = (
            new_point[1] - old_point[1]
        ) / elapsed_seconds

        return float(vx), float(vy)

    # -------------------------------------------------
    # VALID ROAD-USER PAIRS
    # -------------------------------------------------

    @staticmethod
    def _valid_pair(
        a: MotionState,
        b: MotionState,
    ) -> bool:

        # Pedestrian-pedestrian interactions are not
        # treated as traffic near-miss events.
        if (
            a.label == "person"
            and b.label == "person"
        ):
            return False

        return True

    # -------------------------------------------------
    # VIDEO ANALYSIS
    # -------------------------------------------------

    def process_video(
        self,
        input_path: Path,
        output_path: Path,
    ) -> Dict:

        start_time = perf_counter()

        # Reset only tracker state between videos.
        # Keeping the predictor alive avoids repeating model/predictor
        # initialization and warm-up on every request.
        predictor = getattr(self.model, "predictor", None)
        trackers = getattr(predictor, "trackers", None) if predictor else None
        if trackers:
            for tracker in trackers:
                reset = getattr(tracker, "reset", None)
                if callable(reset):
                    reset()

        cap = cv2.VideoCapture(str(input_path))

        if not cap.isOpened():
            raise ValueError(
                "Could not open video."
            )

        fps = cap.get(cv2.CAP_PROP_FPS)

        if not fps or fps <= 0:
            fps = 25.0

        width = int(
            cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        )

        height = int(
            cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )

        source_frame_count = int(
            cap.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        # -------------------------------------------------
        # HARDWARE-ADAPTIVE ANALYSIS
        # -------------------------------------------------

        if self.device == "cuda":
            frame_step = 1
            image_size = settings.GPU_IMAGE_SIZE

        else:
            frame_step = max(
                1,
                round(
                    fps
                    / settings.CPU_TARGET_ANALYSIS_FPS
                ),
            )

            image_size = settings.CPU_IMAGE_SIZE

        analyzed_fps = fps / frame_step

        # -------------------------------------------------
        # OUTPUT VIDEO
        # -------------------------------------------------
        # Risk analysis still uses the original-resolution frame.
        # Only the dashboard copy is capped at 1280 px wide, which
        # substantially reduces CPU video-encoding work without
        # changing detector input, tracking, TTC or CPA calculations.
        output_scale = min(1.0, 1280.0 / max(width, 1))
        output_width = max(2, int(round(width * output_scale)) // 2 * 2)
        output_height = max(2, int(round(height * output_scale)) // 2 * 2)

        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (output_width, output_height),
        )

        if not writer.isOpened():
            cap.release()

            raise ValueError(
                "Could not create output video."
            )

        # -------------------------------------------------
        # TRACKING STATE
        # -------------------------------------------------

        history = defaultdict(
            lambda: deque(
                maxlen=settings.HISTORY_LENGTH
            )
        )

        total_frames = 0
        analyzed_frames = 0

        events = []

        unique_tracks = set()
        class_tracks = defaultdict(set)

        diagonal = (
            width ** 2 + height ** 2
        ) ** 0.5

        max_pair_distance = (
            diagonal
            * settings.MAX_PAIR_DISTANCE_RATIO
        )

        max_pair_distance_squared = (
            max_pair_distance ** 2
        )

        cooldown_frames = max(
            int(
                settings.EVENT_COOLDOWN_SECONDS
                * fps
            ),
            1,
        )

        event_engine = EventEngine(
            confirmation_frames=(
                settings.EVENT_CONFIRMATION_FRAMES
            ),
            cooldown_frames=cooldown_frames,
        )

        last_annotations = []

        # -------------------------------------------------
        # PROCESS VIDEO
        # -------------------------------------------------

        try:

            while True:

                ok, frame = cap.read()

                if not ok:
                    break

                total_frames += 1

                should_analyze = (
                    (total_frames - 1)
                    % frame_step
                    == 0
                )

                # -----------------------------------------
                # NON-INFERENCE FRAME
                # -----------------------------------------

                if not should_analyze:

                    for annotation in last_annotations:

                        (
                            x1,
                            y1,
                            x2,
                            y2,
                            text,
                        ) = annotation

                        cv2.rectangle(
                            frame,
                            (x1, y1),
                            (x2, y2),
                            (255, 255, 255),
                            2,
                        )

                        cv2.putText(
                            frame,
                            text,
                            (
                                x1,
                                max(20, y1 - 8),
                            ),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (255, 255, 255),
                            2,
                        )

                    if output_scale < 1.0:
                        output_frame = cv2.resize(
                            frame,
                            (output_width, output_height),
                            interpolation=cv2.INTER_AREA,
                        )
                    else:
                        output_frame = frame
                    writer.write(output_frame)
                    continue

                analyzed_frames += 1

                # -----------------------------------------
                # YOLO + BYTETRACK
                # -----------------------------------------

                results = self.model.track(
                    source=frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    verbose=False,
                    classes=YOLO_CLASS_IDS,
                    conf=settings.YOLO_CONFIDENCE,
                    iou=settings.YOLO_IOU,
                    imgsz=image_size,
                    device=self.device,
                )

                states = []
                current_annotations = []

                if (
                    results
                    and results[0].boxes is not None
                    and len(results[0].boxes) > 0
                ):

                    boxes = results[0].boxes
                    names = results[0].names

                    for box in boxes:

                        if box.id is None:
                            continue

                        track_id = int(
                            box.id.item()
                        )

                        cls_id = int(
                            box.cls.item()
                        )

                        label = names[cls_id]

                        if (
                            label
                            not in ROAD_USER_CLASSES
                        ):
                            continue

                        (
                            x1,
                            y1,
                            x2,
                            y2,
                        ) = map(
                            float,
                            box.xyxy[0].tolist(),
                        )

                        box_width = max(
                            x2 - x1,
                            1.0,
                        )

                        box_height = max(
                            y2 - y1,
                            1.0,
                        )

                        # Bottom-centre point provides
                        # a better road-position estimate
                        # than bounding-box centre.
                        cx = (x1 + x2) / 2.0
                        road_y = y2

                        track_history = history[
                            track_id
                        ]

                        track_history.append(
                            (cx, road_y)
                        )

                        unique_tracks.add(
                            track_id
                        )

                        class_tracks[label].add(
                            track_id
                        )

                        velocity = self._velocity(
                            track_history,
                            analyzed_fps,
                        )

                        state = MotionState(
                            track_id=track_id,
                            label=label,
                            center=(cx, road_y),
                            velocity=velocity,
                            width=box_width,
                            height=box_height,
                            history_length=len(
                                track_history
                            ),
                        )

                        states.append(state)

                        ix1 = int(x1)
                        iy1 = int(y1)
                        ix2 = int(x2)
                        iy2 = int(y2)

                        text = (
                            f"{label} #{track_id}"
                        )

                        current_annotations.append(
                            (
                                ix1,
                                iy1,
                                ix2,
                                iy2,
                                text,
                            )
                        )

                        cv2.rectangle(
                            frame,
                            (ix1, iy1),
                            (ix2, iy2),
                            (255, 255, 255),
                            2,
                        )

                        cv2.putText(
                            frame,
                            text,
                            (
                                ix1,
                                max(20, iy1 - 8),
                            ),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (255, 255, 255),
                            2,
                        )

                last_annotations = (
                    current_annotations
                )

                # -----------------------------------------
                # RISK ANALYSIS
                # -----------------------------------------

                state_count = len(states)

                for i in range(state_count):

                    a = states[i]

                    if (
                        a.history_length
                        < settings.MIN_HISTORY_FOR_RISK
                    ):
                        continue

                    for j in range(
                        i + 1,
                        state_count,
                    ):

                        b = states[j]

                        if (
                            b.history_length
                            < settings.MIN_HISTORY_FOR_RISK
                        ):
                            continue

                        if not self._valid_pair(a, b):
                            continue

                        dx = (
                            b.center[0]
                            - a.center[0]
                        )

                        dy = (
                            b.center[1]
                            - a.center[1]
                        )

                        distance_squared = (
                            dx * dx
                            + dy * dy
                        )

                        # Cheap pre-filter before the
                        # more expensive risk calculation.
                        if (
                            distance_squared
                            > max_pair_distance_squared
                        ):
                            continue

                        risk = classify_pair_risk(
                            a,
                            b,
                            width,
                            height,
                            max_ttc_seconds=(
                                settings.MAX_TTC_SECONDS
                            ),
                            high_threshold=(
                                settings.HIGH_RISK_THRESHOLD
                            ),
                            critical_threshold=(
                                settings.CRITICAL_RISK_THRESHOLD
                            ),
                        )

                        if (
                            risk["risk_level"]
                            not in {
                                "HIGH",
                                "CRITICAL",
                            }
                        ):
                            continue

                        if not risk["approaching"]:
                            continue

                        ttc = risk.get(
                            "estimated_ttc"
                        )

                        closest = risk.get(
                            "closest_approach_px"
                        )

                        scale = risk.get(
                            "object_scale_px",
                            1.0,
                        )

                        if (
                            ttc is None
                            or closest is None
                        ):
                            continue

                        # ---------------------------------
                        # SCALE-AWARE CPA VALIDATION
                        # ---------------------------------

                        max_allowed_cpa = (
                            scale
                            * settings.MAX_CPA_SCALE
                        )

                        if (
                            closest
                            > max_allowed_cpa
                        ):
                            continue

                        # ---------------------------------
                        # TEMPORAL EVENT CONFIRMATION
                        # ---------------------------------

                        confirmed = event_engine.update(
                            a.track_id,
                            b.track_id,
                            total_frames,
                            risk,
                        )

                        if confirmed is None:
                            continue

                        event = {
                            "frame_index": (
                                total_frames
                            ),
                            "timestamp_seconds": round(
                                (total_frames - 1)
                                / fps,
                                2,
                            ),
                            "object_a": (
                                f"{a.label}"
                                f"#{a.track_id}"
                            ),
                            "object_b": (
                                f"{b.label}"
                                f"#{b.track_id}"
                            ),
                            **confirmed,
                        }

                        events.append(event)

                        # ---------------------------------
                        # EVENT VISUALIZATION
                        # ---------------------------------

                        p1 = (
                            int(a.center[0]),
                            int(a.center[1]),
                        )

                        p2 = (
                            int(b.center[0]),
                            int(b.center[1]),
                        )

                        cv2.line(
                            frame,
                            p1,
                            p2,
                            (255, 255, 255),
                            2,
                        )

                        label_x = int(
                            (p1[0] + p2[0])
                            / 2
                        )

                        label_y = int(
                            (p1[1] + p2[1])
                            / 2
                        )

                        cv2.putText(
                            frame,
                            (
                                f"{confirmed['risk_level']} "
                                f"{confirmed['risk_score']:.0f}"
                            ),
                            (
                                label_x,
                                label_y,
                            ),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.65,
                            (255, 255, 255),
                            2,
                        )

                if output_scale < 1.0:
                    output_frame = cv2.resize(
                        frame,
                        (output_width, output_height),
                        interpolation=cv2.INTER_AREA,
                    )
                else:
                    output_frame = frame
                writer.write(output_frame)

        finally:

            cap.release()
            writer.release()

        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        critical = sum(
            1
            for event in events
            if (
                event["risk_level"]
                == "CRITICAL"
            )
        )

        high = sum(
            1
            for event in events
            if (
                event["risk_level"]
                == "HIGH"
            )
        )

        if events:

            risk_scores = [
                event["risk_score"]
                for event in events
            ]

            max_risk = max(
                risk_scores
            )

            avg_risk = (
                sum(risk_scores)
                / len(risk_scores)
            )

            overall = min(
                100.0,
                (
                    0.70 * max_risk
                    + 0.20 * avg_risk
                    + min(
                        len(events),
                        10,
                    )
                ),
            )

        else:

            max_risk = 0.0
            avg_risk = 0.0
            overall = 0.0

        if overall >= 78:
            overall_level = "CRITICAL"

        elif overall >= 60:
            overall_level = "HIGH"

        elif overall >= 35:
            overall_level = "MEDIUM"

        else:
            overall_level = "LOW"

        processing_time = (
            perf_counter()
            - start_time
        )

        # -------------------------------------------------
        # FINAL RESPONSE
        # -------------------------------------------------

        return {
            "total_frames": (
                total_frames
            ),

            "analyzed_frames": (
                analyzed_frames
            ),

            "frame_step": (
                frame_step
            ),

            "source_frame_count": (
                source_frame_count
            ),

            "video_fps": round(
                fps,
                2,
            ),

            "analysis_fps": round(
                analyzed_fps,
                2,
            ),

            "device": (
                self.device
            ),

            "output_resolution": (
                f"{output_width}x{output_height}"
            ),

            "processing_time_seconds": round(
                processing_time,
                2,
            ),

            "processing_fps": (
                round(
                    total_frames
                    / processing_time,
                    2,
                )
                if processing_time > 0
                else 0.0
            ),

            "inference_fps": (
                round(
                    analyzed_frames
                    / processing_time,
                    2,
                )
                if processing_time > 0
                else 0.0
            ),

            "unique_road_users": (
                len(unique_tracks)
            ),

            "detected_by_class": {
                label: len(ids)
                for label, ids
                in sorted(
                    class_tracks.items()
                )
            },

            "output_video": str(
                output_path
            ),

            "output_video_url": (
                f"/outputs/"
                f"{output_path.name}"
            ),

            "events": events,

            "summary": {
                "total_near_miss_events": (
                    len(events)
                ),

                "critical_events": (
                    critical
                ),

                "high_risk_events": (
                    high
                ),

                "max_event_risk_score": round(
                    max_risk,
                    2,
                ),

                "average_event_risk_score": round(
                    avg_risk,
                    2,
                ),

                "overall_risk_score": round(
                    overall,
                    2,
                ),

                "overall_risk_level": (
                    overall_level
                ),
            },
        }