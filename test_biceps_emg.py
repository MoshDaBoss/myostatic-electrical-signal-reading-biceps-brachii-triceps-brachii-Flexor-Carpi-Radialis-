import math
import unittest

from biceps_emg import BicepsEmgReader


def window(amplitude):
    return [-amplitude, amplitude, -amplitude, amplitude]


class BicepsEmgReaderTests(unittest.TestCase):
    def make_reader(self, **kwargs):
        reader = BicepsEmgReader(**kwargs)
        self.assertTrue(reader.calibrate_rest(window(0.5)))
        self.assertTrue(reader.calibrate_contraction(window(4.0)))
        return reader

    def test_startup_calibration_and_contraction_are_inactive_until_debounced(self):
        reader = BicepsEmgReader()
        self.assertFalse(reader.active)
        self.assertFalse(reader.read(window(4), 0.0))
        self.assertTrue(reader.calibrate_rest(window(0.5)))
        self.assertFalse(reader.calibrate_contraction(window(0.4)))
        self.assertTrue(reader.calibrate_contraction(window(4)))
        self.assertFalse(reader.read(window(4), 0.0))
        self.assertTrue(reader.read(window(4), 0.01))

    def test_hysteresis_holds_in_deadband_and_debounces_release(self):
        reader = self.make_reader()
        self.assertFalse(reader.read(window(4), 0.0))
        self.assertTrue(reader.read(window(4), 0.01))
        self.assertTrue(reader.read(window(2), 0.02))  # hysteresis deadband
        self.assertTrue(reader.read(window(1), 0.03))
        self.assertFalse(reader.read(window(1), 0.04))

    def test_independent_activation_boundaries_do_not_toggle(self):
        reader = self.make_reader(activation_windows=1, release_windows=1)
        on_threshold = 0.5 + 0.6 * (4.0 - 0.5)
        self.assertFalse(reader.read(window(on_threshold - 0.01), 0.0))
        self.assertTrue(reader.read(window(on_threshold), 0.01))
        self.assertTrue(reader.read(window(on_threshold), 0.02))
        self.assertFalse(reader.read(window(0.5), 0.03))

    def test_invalid_quality_and_nonfinite_samples_clear_output(self):
        reader = self.make_reader(activation_windows=1)
        self.assertTrue(reader.read(window(4), 1.0))
        self.assertFalse(reader.read(window(4), 1.01, signal_valid=False))
        self.assertFalse(reader.active)
        self.assertTrue(reader.read(window(4), 1.02))
        self.assertFalse(reader.read([0, math.nan, 0, 0], 1.03))
        self.assertIsNone(reader.rms)
        self.assertFalse(reader.active)

    def test_stale_data_and_gaps_clear_previous_level(self):
        reader = self.make_reader(activation_windows=1, stale_after_s=0.1)
        self.assertTrue(reader.read(window(4), 2.0))
        self.assertFalse(reader.output(2.11))
        self.assertFalse(reader.active)
        self.assertTrue(reader.read(window(4), 3.0))
        # A fresh window after a gap must not inherit the prior active state.
        reader.activation_windows = 2
        self.assertFalse(reader.read(window(4), 3.2))
        self.assertTrue(reader.read(window(4), 3.21))

    def test_invalid_and_stale_windows_preserve_timestamp_ordering(self):
        reader = self.make_reader(activation_windows=1, stale_after_s=0.1)
        self.assertTrue(reader.read(window(4), 1.0))

        # Even when a bad-quality window clears the level, it advances the
        # timestamp watermark; subsequent regressing windows remain rejected.
        self.assertFalse(reader.read(window(4), 1.1, signal_valid=False))
        self.assertFalse(reader.read(window(4), 1.05))
        self.assertTrue(reader.read(window(4), 1.11))

        # Polling a stale level clears it, and timestamps older than the last
        # accepted window still cannot become fresh again.
        self.assertFalse(reader.output(1.22))
        self.assertFalse(reader.read(window(4), 1.1))
        self.assertTrue(reader.read(window(4), 1.23))

    def test_bad_windows_timestamps_and_shutdown_fail_inactive(self):
        reader = self.make_reader()
        self.assertFalse(reader.read([1], 0))
        self.assertFalse(reader.read(window(4), 0))
        self.assertFalse(reader.read(window(4), 0))  # repeated timestamp
        self.assertFalse(reader.active)
        reader.shutdown()
        self.assertFalse(reader.read(window(4), 1))
        self.assertFalse(reader.output(1))


if __name__ == "__main__":
    unittest.main()
