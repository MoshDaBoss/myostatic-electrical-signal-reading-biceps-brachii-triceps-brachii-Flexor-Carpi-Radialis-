import math
import unittest

from biceps_emg import BicepsEmgReader
from flexor_carpi_radialis_emg import FlexorCarpiRadialisEmgReader
from triceps_emg import TricepsEmgReader


def window(amplitude):
    return [-amplitude, amplitude, -amplitude, amplitude]


class FlexorCarpiRadialisEmgReaderTests(unittest.TestCase):
    def make_reader(self, **kwargs):
        reader = FlexorCarpiRadialisEmgReader(**kwargs)
        self.assertTrue(reader.calibrate_rest(window(0.5)))
        self.assertTrue(reader.calibrate_contraction(window(4.0)))
        return reader

    def test_calibration_activation_and_release(self):
        reader = FlexorCarpiRadialisEmgReader()
        self.assertFalse(reader.active)
        self.assertFalse(reader.read(window(4), 0.0))
        self.assertTrue(reader.calibrate_rest(window(0.5)))
        self.assertFalse(reader.calibrate_contraction(window(0.4)))
        self.assertTrue(reader.calibrate_contraction(window(4.0)))

        self.assertFalse(reader.read(window(4.0), 0.0))
        self.assertTrue(reader.read(window(4.0), 0.01))
        self.assertTrue(reader.read(window(0.5), 0.02))
        self.assertFalse(reader.read(window(0.5), 0.03))

    def test_invalid_signal_and_bad_samples_fail_inactive(self):
        reader = self.make_reader(activation_windows=1)
        self.assertTrue(reader.read(window(4.0), 1.0))
        self.assertFalse(reader.read(window(4.0), 1.01, signal_valid=False))
        self.assertFalse(reader.active)
        self.assertTrue(reader.read(window(4.0), 1.02))
        self.assertFalse(reader.read([0, math.nan, 0, 0], 1.03))
        self.assertFalse(reader.active)
        self.assertIsNone(reader.rms)

    def test_stale_data_and_shutdown_fail_inactive(self):
        reader = self.make_reader(activation_windows=1, stale_after_s=0.1)
        self.assertTrue(reader.read(window(4.0), 2.0))
        self.assertFalse(reader.output(2.11))
        self.assertFalse(reader.active)

        self.assertTrue(reader.read(window(4.0), 3.0))
        reader.shutdown()
        self.assertFalse(reader.output(3.0))
        self.assertFalse(reader.read(window(4.0), 3.01))

    def test_all_three_muscles_have_independent_calibration_and_state(self):
        biceps = BicepsEmgReader(activation_windows=1, release_windows=1)
        triceps = TricepsEmgReader(activation_windows=1, release_windows=1)
        fcr = FlexorCarpiRadialisEmgReader(
            activation_windows=1, release_windows=1
        )

        self.assertTrue(biceps.calibrate_rest(window(0.5)))
        self.assertTrue(biceps.calibrate_contraction(window(4.0)))
        self.assertTrue(triceps.calibrate_rest(window(1.0)))
        self.assertTrue(triceps.calibrate_contraction(window(10.0)))
        self.assertTrue(fcr.calibrate_rest(window(2.0)))
        self.assertTrue(fcr.calibrate_contraction(window(8.0)))

        # 5 exceeds the biceps threshold, but not the independently calibrated
        # triceps or FCR threshold.
        self.assertTrue(biceps.read(window(5.0), 0.0))
        self.assertFalse(triceps.read(window(5.0), 0.0))
        self.assertFalse(fcr.read(window(5.0), 0.0))
        self.assertTrue(biceps.active)
        self.assertFalse(triceps.active)
        self.assertFalse(fcr.active)

        # Invalidating FCR clears only its output; biceps state is unaffected.
        self.assertFalse(fcr.read(window(8.0), 0.01, signal_valid=False))
        self.assertTrue(biceps.active)
        self.assertFalse(triceps.active)
        self.assertFalse(fcr.active)
        self.assertTrue(triceps.read(window(10.0), 0.02))
        self.assertTrue(fcr.read(window(8.0), 0.02))
        self.assertTrue(biceps.active)
        self.assertTrue(triceps.active)
        self.assertTrue(fcr.active)


if __name__ == "__main__":
    unittest.main()
