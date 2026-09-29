from __future__ import annotations

from collections import defaultdict
from typing import Dict, Optional, Tuple


class EventEngine:
    """
    Temporal validation layer for near-miss events.

    A single noisy frame should not immediately create
    a near-miss alert. Risk must persist across multiple
    analyzed observations.
    """

    def __init__(
        self,
        confirmation_frames: int = 2,
        cooldown_frames: int = 1,
    ):
        self.confirmation_frames = max(
            confirmation_frames,
            1,
        )

        self.cooldown_frames = max(
            cooldown_frames,
            1,
        )

        self._candidate_counts = defaultdict(int)
        self._last_seen_frame = {}
        self._last_event_frame = {}

    @staticmethod
    def pair_key(
        track_a: int,
        track_b: int,
    ) -> Tuple[int, int]:

        return tuple(
            sorted(
                (
                    track_a,
                    track_b,
                )
            )
        )

    def reset(self):
        self._candidate_counts.clear()
        self._last_seen_frame.clear()
        self._last_event_frame.clear()

    def update(
        self,
        track_a: int,
        track_b: int,
        frame_index: int,
        risk: Dict,
    ) -> Optional[Dict]:

        pair = self.pair_key(
            track_a,
            track_b,
        )

        risk_level = risk.get(
            "risk_level",
            "LOW",
        )

        if risk_level not in {
            "HIGH",
            "CRITICAL",
        }:
            self._candidate_counts[pair] = 0
            return None

        previous_seen = self._last_seen_frame.get(
            pair
        )

        # If the pair disappeared for too long,
        # restart temporal confirmation.
        if (
            previous_seen is not None
            and frame_index - previous_seen
            > self.cooldown_frames
        ):
            self._candidate_counts[pair] = 0

        self._last_seen_frame[pair] = frame_index

        self._candidate_counts[pair] += 1

        if (
            self._candidate_counts[pair]
            < self.confirmation_frames
        ):
            return None

        previous_event = self._last_event_frame.get(
            pair
        )

        if (
            previous_event is not None
            and frame_index - previous_event
            < self.cooldown_frames
        ):
            return None

        self._last_event_frame[pair] = frame_index

        # Reset confirmation after an accepted event.
        self._candidate_counts[pair] = 0

        return risk