# PID Playground

An interactive Python speed-controller simulator with a reproducible CSV mode. Compare P, PI and PID control, actuator saturation and recovery from a load disturbance. No pip packages are needed.

## Run

Python 3.10 or newer:

```sh
python playground.py --gui
```

Edit Kp, Ki and Kd, then click **Simulate**. Yellow is the target, green is measured speed, and the pink marker introduces load at 6 seconds. The GUI needs Tkinter and a desktop display; on some Linux installations Tkinter is a separate OS package. All simulations also work without a GUI:

```sh
python playground.py --kp 2 --ki 0 --kd 0 --output p.csv
python playground.py --kp 2 --ki 1 --kd 0 --output pi.csv
python playground.py --kp 2 --ki 1 --kd 0.1 --output pid.csv
python playground.py --help
```

GUI controls use the default plant and experiment settings. CLI flags allow changing the plant time constant, sample interval, duration, target, actuator limit and disturbance.

## Model and controller

The normalized motor-speed model is `tau * dy/dt = command - load - y`. Its exact interval update assumes the command and load are constant within each sample. This avoids Euler integration error for the plant, although the controller is still sampled and sampling affects behavior.

The controller adds proportional error, integrated error, and a filtered derivative of measured speed. Derivative on measurement avoids a setpoint derivative kick. Conditional integration freezes the integral when saturation and the error push in the same direction. Command is limited to ±3 by default. This is a simplified teaching model, not hardware control software.

## Experiments

1. Set Ki and Kd to zero. Observe the remaining error under a constant load.
2. Add Ki. Observe whether error decreases and how the transient changes.
3. Add a little Kd. Compare peak response and absolute error; derivative is not guaranteed to help every plant.
4. Lower `--limit` below the target plus load. Explain why the target becomes physically unreachable.
5. Halve `--dt` and compare results to understand sampling sensitivity.

Reported metrics are signed final tracking error, peak speed, and the left-rectangle integral of absolute error over the simulation. They cover the whole experiment, including load recovery, and do not claim a settling time.

## Validation and limits

Run `python -m unittest -v`. Checks cover the analytical zero-control response, actuator bounds, PI load rejection, invalid parameters and sampling consistency. GUI rendering requires a desktop and is not covered by these checks.

The plant omits noise, communication delay, nonlinear friction and motor electrical dynamics. Time steps must be no larger than tau/10; at most 200,000 intervals are accepted. Extreme finite inputs may still overflow and are rejected when detected.
