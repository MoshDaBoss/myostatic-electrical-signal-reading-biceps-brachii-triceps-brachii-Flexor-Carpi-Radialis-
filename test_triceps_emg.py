import math
import unittest

from biceps_emg import BicepsEmgReader
from triceps_emg import TricepsEmgReader


def window(amplitude):
    return [-amplitude, amplitude, -amplitude, amplitude]


class TricepsEmgReaderTests(unittest.TestCase):
    def make_reader(self, **kwargs):
        reader = TricepsEmgReader(**kwargs)
        self.assertTrue(reader.calibrate_rest(window(0.5)))
        self.assertTrue(reader.calibrate_contraction(window(4.0)))
        return reader

    def test_independent_calibration_and_momentary_reading(self):
        reader = self.make_reader(activation_windows=1, release_windows=1)
        self.assertTrue(reader.read(window(4), 0.0))
        self.assertTrue(reader.read(window(4), 0.01))
        self.assertTrue(reader.active)
        self.assertFalse(reader.read(window(0.5), 0.02))

    def test_invalid_signal_stale_data_and_shutdown_fail_inactive(self):
        reader = self.make_reader(activation_windows=1, stale_after_s=0.1)
        self.assertTrue(reader.read(window(4), 1.0))
        self.assertFalse(reader.read(window(4), 1.01, signal_valid=False))
        self.assertFalse(reader.active)
        self.assertFalse(reader.read([0, math.nan, 0, 0], 1.02))
        self.assertFalse(reader.active)

        self.assertTrue(reader.read(window(4), 2.0))
        self.assertFalse(reader.output(2.11))
        self.assertFalse(reader.active)
        reader.shutdown()
        self.assertFalse(reader.read(window(4), 3.0))
        self.assertFalse(reader.output(3.0))

    def test_biceps_and_triceps_calibration_and_state_are_independent(self):
        biceps = BicepsEmgReader(activation_windows=1, release_windows=1)
        triceps = TricepsEmgReader(activation_windows=1, release_windows=1)
        self.assertTrue(biceps.calibrate_rest(window(0.5)))
        self.assertTrue(biceps.calibrate_contraction(window(4)))
        self.assertTrue(triceps.calibrate_rest(window(1)))
        self.assertTrue(triceps.calibrate_contraction(window(10)))

        # This amplitude exceeds the biceps threshold, but not the independently
        # calibrated triceps threshold.
        self.assertTrue(biceps.read(window(5), 0.0))
        self.assertFalse(triceps.read(window(5), 0.0))
        self.assertTrue(biceps.active)
        self.assertFalse(triceps.active)

        # Invalidating triceps clears only the triceps output.
        self.assertFalse(triceps.read(window(5), 0.01, signal_valid=False))
        self.assertTrue(biceps.active)
        self.assertFalse(triceps.active)
        self.assertTrue(triceps.read(window(10), 0.02))
        self.assertTrue(biceps.active)


if __name__ == "__main__":
    unittest.main()
