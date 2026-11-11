"""Hardware-independent flexor carpi radialis EMG window processing.

An acquisition adapter supplies batches of flexor carpi radialis samples and
monotonic timestamps. Each reader instance has its own calibration and output
state. This module does not choose a sensor, ADC range, sample rate, or robot
interface.
"""

from biceps_emg import BicepsEmgReader


class FlexorCarpiRadialisEmgReader(BicepsEmgReader):
    """Convert calibrated flexor carpi radialis EMG windows to a fail-inactive level.

    The signal conditioning, calibration, hysteresis, debounce, stale-data,
    and shutdown behavior is shared with :class:`BicepsEmgReader`. This is a
    separate reader instance with independent FCR calibration and output
    state; it does not combine or map any other muscle input.
    """
