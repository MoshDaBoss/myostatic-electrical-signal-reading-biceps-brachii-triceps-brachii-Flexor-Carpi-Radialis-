"""Hardware-independent triceps EMG window processing.

An acquisition adapter supplies batches of triceps samples and monotonic
timestamps. Each reader instance has its own calibration and output state.
This module does not choose a sensor, ADC range, sample rate, or robot
interface.
"""

from __future__ import annotations

from biceps_emg import BicepsEmgReader


class TricepsEmgReader(BicepsEmgReader):
    """Convert calibrated triceps EMG windows to a fail-inactive level.

    The signal conditioning, calibration, hysteresis, debounce, stale-data,
    and shutdown behavior is shared with :class:`BicepsEmgReader`. This is a
    separate reader instance with independent triceps calibration and state;
    it does not combine or map the biceps input.
    """

