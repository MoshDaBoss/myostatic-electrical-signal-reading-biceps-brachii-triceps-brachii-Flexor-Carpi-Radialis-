"""Hardware-independent biceps EMG window processing and momentary output logic.

An acquisition adapter supplies batches of raw samples and monotonic timestamps.
This module deliberately does not choose a sensor, ADC range, sample rate, or
robot interface.
"""

from __future__ import annotations

import math
from typing import Iterable


class BicepsEmgReader:
    """Convert calibrated biceps EMG sample windows to a fail-inactive level.

    Calibration and thresholds are expressed in the same units as the supplied
    samples. Each call to :meth:`read` represents one window; debounce counts
    windows, so the acquisition layer controls their duration and cadence.
    """

    def __init__(
        self,
        *,
        stale_after_s: float = 0.5,
        min_samples: int = 2,
        activation_fraction: float = 0.6,
        release_fraction: float = 0.35,
        activation_windows: int = 2,
        release_windows: int = 2,
    ) -> None:
        if not math.isfinite(stale_after_s) or stale_after_s <= 0:
            raise ValueError("stale_after_s must be finite and positive")
        if min_samples < 2:
            raise ValueError("min_samples must be at least 2")
        if not 0 < release_fraction < activation_fraction < 1:
            raise ValueError(
                "fractions must satisfy 0 < release < activation < 1"
            )
        if activation_windows < 1 or release_windows < 1:
            raise ValueError("debounce window counts must be positive")

        self.stale_after_s = stale_after_s
        self.min_samples = min_samples
        self.activation_fraction = activation_fraction
        self.release_fraction = release_fraction
        self.activation_windows = activation_windows
        self.release_windows = release_windows

        self._rest_rms: float | None = None
        self._contract_rms: float | None = None
        self._active = False
        # Keep the timestamp watermark even when an invalid window clears the
        # output, so a later regressing timestamp cannot be mistaken for fresh
        # input. The separate freshness timestamp tracks the active level.
        self._last_timestamp: float | None = None
        self._fresh_timestamp: float | None = None
        self._rms: float | None = None
        self._on_count = 0
        self._off_count = 0
        self._closed = False

    @staticmethod
    def _measure(samples: Iterable[float], min_samples: int) -> float | None:
        try:
            values = [float(sample) for sample in samples]
        except (TypeError, ValueError, OverflowError):
            return None
        if len(values) < min_samples or not all(math.isfinite(x) for x in values):
            return None
        try:
            mean = math.fsum(values) / len(values)
            # Removing the window mean attenuates a constant electrode/ADC
            # offset before calculating the window's EMG amplitude.
            rms = math.hypot(*(value - mean for value in values)) / math.sqrt(
                len(values)
            )
        except (OverflowError, ValueError):
            return None
        return rms if math.isfinite(rms) else None

    def calibrate_rest(self, samples: Iterable[float]) -> bool:
        """Record a representative relaxed-muscle window; returns success."""
        measurement = self._measure(samples, self.min_samples)
        if measurement is None or self._closed:
            return False
        self._rest_rms = measurement
        self._contract_rms = None
        self._reset_output()
        return True

    def calibrate_contraction(self, samples: Iterable[float]) -> bool:
        """Record a representative deliberate-contraction window.

        A rest window must be recorded first, and the contraction amplitude
        must exceed it. This is signal calibration, not clinical assessment.
        """
        measurement = self._measure(samples, self.min_samples)
        if (
            measurement is None
            or self._closed
            or self._rest_rms is None
            or measurement <= self._rest_rms
        ):
            return False
        self._contract_rms = measurement
        self._reset_output()
        return True

    @property
    def calibrated(self) -> bool:
        return self._rest_rms is not None and self._contract_rms is not None

    @property
    def active(self) -> bool:
        """Current biceps control level (false until calibrated/valid)."""
        return self._active

    @property
    def rms(self) -> float | None:
        """Most recent valid mean-removed window RMS, or None if unavailable."""
        return self._rms

    def _reset_output(self) -> None:
        self._active = False
        self._fresh_timestamp = None
        self._rms = None
        self._on_count = 0
        self._off_count = 0

    def _invalidate(self) -> bool:
        self._reset_output()
        return False

    def read(
        self,
        samples: Iterable[float],
        timestamp_s: float,
        *,
        signal_valid: bool = True,
    ) -> bool:
        """Process one window and return the biceps momentary output level.

        ``timestamp_s`` must use a monotonic clock. The upstream acquisition
        layer must set ``signal_valid=False`` when its connection/quality checks
        fail. Invalid, out-of-order, or uncalibrated input immediately clears
        the output. The output also clears after the configured stale timeout.
        """
        if self._closed:
            return False
        try:
            timestamp = float(timestamp_s)
        except (TypeError, ValueError, OverflowError):
            return self._invalidate()
        if (
            not math.isfinite(timestamp)
            or (
                self._last_timestamp is not None
                and timestamp <= self._last_timestamp
            )
        ):
            return self._invalidate()
        if not self.calibrated:
            return self._invalidate()
        self._last_timestamp = timestamp
        if not signal_valid:
            return self._invalidate()
        if (
            self._fresh_timestamp is not None
            and timestamp - self._fresh_timestamp > self.stale_after_s
        ):
            # Do not carry an old contraction through a gap in acquisition.
            self._reset_output()

        measurement = self._measure(samples, self.min_samples)
        if measurement is None:
            return self._invalidate()

        assert self._rest_rms is not None
        assert self._contract_rms is not None
        span = self._contract_rms - self._rest_rms
        on_threshold = self._rest_rms + self.activation_fraction * span
        off_threshold = self._rest_rms + self.release_fraction * span

        if measurement >= on_threshold:
            self._on_count += 1
            self._off_count = 0
            if self._on_count >= self.activation_windows:
                self._active = True
        elif measurement <= off_threshold:
            self._off_count += 1
            self._on_count = 0
            if self._off_count >= self.release_windows:
                self._active = False
        else:
            # Hysteresis deadband: retain the current level, but require a new
            # consecutive run if the signal moves out of the deadband.
            self._on_count = 0
            self._off_count = 0

        self._rms = measurement
        self._fresh_timestamp = timestamp
        return self._active

    def output(self, now_s: float) -> bool:
        """Return the momentary level, clearing it if the last window is stale."""
        if self._closed or self._last_timestamp is None:
            return False
        if self._fresh_timestamp is None:
            return False
        try:
            now = float(now_s)
        except (TypeError, ValueError, OverflowError):
            return self._invalidate()
        if (
            not math.isfinite(now)
            or now < self._fresh_timestamp
            or now - self._fresh_timestamp > self.stale_after_s
        ):
            return self._invalidate()
        return self._active

    def shutdown(self) -> None:
        """Clear the output and permanently disable this reader."""
        self._reset_output()
        self._closed = True
