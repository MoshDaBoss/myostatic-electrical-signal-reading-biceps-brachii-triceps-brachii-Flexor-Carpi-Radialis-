# Biceps, triceps, and flexor carpi radialis EMG reading

This repository provides **hardware-independent biceps brachii, triceps
brachii, and flexor carpi radialis (FCR) signal readers**.
`BicepsEmgReader`, `TricepsEmgReader`, and
`FlexorCarpiRadialisEmgReader` each accept batches of their own raw EMG samples
from an acquisition adapter, remove each batch mean, measure its RMS
amplitude, and return a momentary `active` level. Each instance has independent
per-muscle calibration and output state. The readers process adapter-provided
samples; they do not read physical sensors or send commands to a robot.

## Use

```python
from biceps_emg import BicepsEmgReader
from triceps_emg import TricepsEmgReader
from flexor_carpi_radialis_emg import FlexorCarpiRadialisEmgReader

biceps = BicepsEmgReader()
triceps = TricepsEmgReader()  # same configurable processing defaults
fcr = FlexorCarpiRadialisEmgReader()  # same configurable processing defaults

# Calibrate from representative sample windows supplied by your acquisition
# layer: first relaxed, then a deliberate contraction. These are sample units.
biceps.calibrate_rest(biceps_relaxed_samples)
biceps.calibrate_contraction(biceps_contracted_samples)
triceps.calibrate_rest(triceps_relaxed_samples)
triceps.calibrate_contraction(triceps_contracted_samples)
fcr.calibrate_rest(fcr_relaxed_samples)
fcr.calibrate_contraction(fcr_contracted_samples)

# Supply one window and its monotonic timestamp per acquisition update.
# Pass signal_valid=False when upstream connection or signal-quality checks fail.
biceps_control = biceps.read(biceps_samples, timestamp_s, signal_valid=True)
triceps_control = triceps.read(triceps_samples, timestamp_s, signal_valid=True)
fcr_control = fcr.read(fcr_samples, timestamp_s, signal_valid=True)

# Poll this level in the output loop to make stale data fail inactive.
biceps_control = biceps.output(monotonic_now_s)
triceps_control = triceps.output(monotonic_now_s)
fcr_control = fcr.output(monotonic_now_s)
```

`read()` needs at least two finite samples by default and requires successful
per-session rest/contraction calibration. The activation and release thresholds
are fractions of the calibrated amplitude span, with hysteresis and consecutive
window debounce (defaults: 0.60/0.35 and two windows). The default stale timeout
is 0.5 seconds. Configure these values to suit the actual acquisition cadence;
they are software defaults, not hardware specifications.

The mappings implemented here are **biceps brachii input → biceps control
level**, **triceps brachii input → triceps control level**, and **flexor carpi
radialis input → FCR control level**. These are separate momentary levels, not
toggles. Startup, uncalibrated/invalid input, a signal-quality failure,
out-of-order timestamps, stale readings, and `shutdown()` all leave the
corresponding level inactive. The acquisition adapter must provide monotonic
timestamps and meaningful connection/quality checks. No sampling rate, sensor,
ADC range, transport, pinout, actuator, or robot is assumed.

This is experimental control logic, not clinically validated signal analysis.
Before connecting actuators, confirm the sensor interface, units, window size
and cadence, quality checks, stale timeout, and system-specific safe state.
Test the output logic in simulation first; software tests do not establish
hardware or live-robot safety.

Run the focused tests with:

```sh
python -m unittest -v test_biceps_emg.py test_triceps_emg.py test_flexor_carpi_radialis_emg.py
```
