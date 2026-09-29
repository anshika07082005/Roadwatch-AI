from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Dict, Optional, Tuple


@dataclass
class MotionState:
    track_id: int
    label: str

    # Bottom-centre road contact point.
    center: Tuple[float, float]

    # Pixels per second.
    velocity: Tuple[float, float]

    width: float
    height: float

    history_length: int


def euclidean(
    a: Tuple[float, float],
    b: Tuple[float, float],
) -> float:

    return hypot(
        a[0] - b[0],
        a[1] - b[1],
    )


def magnitude(
    vector: Tuple[float, float],
) -> float:

    return hypot(
        vector[0],
        vector[1],
    )


def relative_motion(
    a: MotionState,
    b: MotionState,
):

    rx = b.center[0] - a.center[0]
    ry = b.center[1] - a.center[1]

    rvx = b.velocity[0] - a.velocity[0]
    rvy = b.velocity[1] - a.velocity[1]

    return rx, ry, rvx, rvy


def are_approaching(
    a: MotionState,
    b: MotionState,
) -> bool:

    rx, ry, rvx, rvy = relative_motion(
        a,
        b,
    )

    return (
        rx * rvx +
        ry * rvy
    ) < 0


def estimate_ttc(
    a: MotionState,
    b: MotionState,
) -> Optional[float]:
    """
    Video-space time to closest approach.

    Velocity is measured in pixels/second,
    therefore TTC is expressed in seconds.
    """

    rx, ry, rvx, rvy = relative_motion(
        a,
        b,
    )

    relative_speed_squared = (
        rvx * rvx +
        rvy * rvy
    )

    if relative_speed_squared < 1e-6:
        return None

    dot_product = (
        rx * rvx +
        ry * rvy
    )

    if dot_product >= 0:
        return None

    ttc = (
        -dot_product /
        relative_speed_squared
    )

    if ttc <= 0:
        return None

    return float(ttc)


def closest_approach_distance(
    a: MotionState,
    b: MotionState,
    ttc: Optional[float],
) -> Optional[float]:

    if ttc is None:
        return None

    rx, ry, rvx, rvy = relative_motion(
        a,
        b,
    )

    future_rx = rx + rvx * ttc
    future_ry = ry + rvy * ttc

    return hypot(
        future_rx,
        future_ry,
    )


def object_scale(
    a: MotionState,
    b: MotionState,
) -> float:
    """
    Approximate visual scale of the interaction.
    """

    scale_a = (
        a.width +
        a.height
    ) / 2.0

    scale_b = (
        b.width +
        b.height
    ) / 2.0

    return max(
        (
            scale_a +
            scale_b
        ) / 2.0,
        1.0,
    )


def classify_pair_risk(
    a: MotionState,
    b: MotionState,
    frame_width: int,
    frame_height: int,
    max_ttc_seconds: float = 4.0,
    high_threshold: float = 60.0,
    critical_threshold: float = 78.0,
) -> Dict:

    frame_diagonal = hypot(
        frame_width,
        frame_height,
    )

    current_distance = euclidean(
        a.center,
        b.center,
    )

    normalized_distance = (
        current_distance /
        max(frame_diagonal, 1.0)
    )

    approaching = are_approaching(
        a,
        b,
    )

    ttc = None

    if approaching:
        ttc = estimate_ttc(
            a,
            b,
        )

    if (
        ttc is not None
        and ttc > max_ttc_seconds
    ):
        ttc = None

    closest_distance = (
        closest_approach_distance(
            a,
            b,
            ttc,
        )
    )

    scale = object_scale(
        a,
        b,
    )

    # -------------------------------------------------
    # PROXIMITY
    # -------------------------------------------------

    proximity_score = max(
        0.0,
        1.0 - min(
            normalized_distance / 0.16,
            1.0,
        ),
    )

    # -------------------------------------------------
    # TTC
    # -------------------------------------------------

    if ttc is None:

        ttc_score = 0.0

    else:

        ttc_score = max(
            0.0,
            1.0 - min(
                ttc /
                max_ttc_seconds,
                1.0,
            ),
        )

    # -------------------------------------------------
    # COLLISION COURSE / CPA
    # -------------------------------------------------

    if closest_distance is None:

        collision_course_score = 0.0

    else:

        normalized_cpa = (
            closest_distance /
            max(scale * 2.0, 1.0)
        )

        collision_course_score = max(
            0.0,
            1.0 - min(
                normalized_cpa,
                1.0,
            ),
        )

    # -------------------------------------------------
    # MOTION
    # -------------------------------------------------

    speed_a = magnitude(
        a.velocity
    )

    speed_b = magnitude(
        b.velocity
    )

    combined_speed = (
        speed_a +
        speed_b
    )

    motion_score = min(
        combined_speed / 500.0,
        1.0,
    )

    # -------------------------------------------------
    # RISK
    # -------------------------------------------------

    risk_score = 100.0 * (
        0.25 * proximity_score +
        0.40 * ttc_score +
        0.25 * collision_course_score +
        0.10 * motion_score
    )

    # Non-approaching objects should not create
    # severe near-miss alerts.
    if not approaching:
        risk_score *= 0.25

    risk_score = round(
        min(
            max(
                risk_score,
                0.0,
            ),
            100.0,
        ),
        2,
    )

    if risk_score >= critical_threshold:

        risk_level = "CRITICAL"

    elif risk_score >= high_threshold:

        risk_level = "HIGH"

    elif risk_score >= 35:

        risk_level = "MEDIUM"

    else:

        risk_level = "LOW"

    return {
        "risk_score": risk_score,

        "risk_level": risk_level,

        "estimated_ttc": (
            round(
                ttc,
                2,
            )
            if ttc is not None
            else None
        ),

        "distance_px": round(
            current_distance,
            2,
        ),

        "closest_approach_px": (
            round(
                closest_distance,
                2,
            )
            if closest_distance is not None
            else None
        ),

        "object_scale_px": round(
            scale,
            2,
        ),

        "approaching": approaching,
    }