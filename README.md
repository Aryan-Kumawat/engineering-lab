# Engineering Lab

Practical projects in robotics, control systems and software engineering by **Aryan Kumawat**. Each folder contains runnable code, setup instructions, examples and documented limits.

Start with a small command-line tool, explore simulations, then inspect the more substantial visual tools. These are initial learning releases with specific supported workflows; individual READMEs describe what has and has not been verified.

## Project catalog

| # | Project | What it does | Run / requirements |
|---|---|---|---|
| 01 | [Sensor Log](01-sensor-log/) | Validates sensor CSV and computes statistics in constant memory | C++17 compiler; terminal |
| 02 | [PID Playground](02-pid-playground/) | Simulates controller tuning, actuator saturation and load disturbances | Python 3.10+; optional Tkinter GUI |
| 03 | [Compact Anomaly Detector](03-tinyml-anomaly-detector/) | Trains a quantized statistical sensor model and evaluates synthetic faults | Python 3.10+; terminal |
| 04 | [Robot Telemetry](04-robot-telemetry/) | Collects JSONL over localhost TCP and replays acknowledged records | Python 3.10+; two terminals |
| 05 | [Local Codebase Explorer](05-local-codebase-intelligence/) | Searches source code locally with ranked excerpts and line citations | Python 3.10+ with SQLite FTS5 |
| 06 | [ArmLab](06-armlab/) | Plans and animates a two-joint planar arm; exports joint paths | Python 3.10+; Tkinter for GUI |
| 07 | [ControlCanvas](07-controlcanvas/) | Connects control blocks visually, simulates responses and saves models | Desktop browser; Node.js for checks |
| 08 | [TaskTree Studio](08-tasktree-studio/) | Edits task JSON, steps through behavior trees and inspects execution traces | Python 3.10+; Tkinter for GUI |
| 09 | [CalibLab](09-caliblab/) | Fits tool offsets and rigid frame transforms with held-out validation | Python 3.10+ and NumPy; optional Tkinter GUI |

## Quick start

Download this repository with **Code → Download ZIP**, extract it, and open a terminal in the extracted folder. Or use Git:

```sh
git clone https://github.com/Aryan-Kumawat/engineering-lab.git
cd engineering-lab
```

**Visual control simulation:** open `07-controlcanvas/index.html` directly in your desktop browser. Keep its files together; no server or installation is required.

**Robot arm planning:**

```sh
cd 06-armlab
python armlab.py
```

**Task execution debugger:** from the repository root:

```sh
cd 08-tasktree-studio
python tasktree.py
```

**Calibration demo:** from the repository root:

```sh
cd 09-caliblab
python -m pip install -r requirements.txt
python caliblab.py demo demo-results
python caliblab.py
```

On systems using `python3`, substitute that command for `python`. Tkinter may need a separate OS package on Linux. Desktop interfaces need a graphical display; CLI examples work without one. No paid API is required. CalibLab is the first project here with a pip dependency: NumPy.

## Checks

Run the following from the repository root after installing CalibLab's requirements:

```sh
python check_projects.py
python -m unittest discover -s 02-pid-playground -v
python -m unittest discover -s 06-armlab -v
node 07-controlcanvas/test.cjs
python -m unittest discover -s 08-tasktree-studio -v
python -m unittest discover -s 09-caliblab -v
```

Sensor Log can be compiled separately:

```sh
g++ -std=c++17 -Wall -Wextra -Wpedantic -O2 01-sensor-log/main.cpp -o sensor-log
./sensor-log 01-sensor-log/samples.csv
```

Telemetry checks create a temporary localhost TCP listener. Tests cover selected numerical and execution behavior, not every user interaction. Desktop and browser interfaces still need visual verification. No hardware deployment has been validated.

## Current scope

- The anomaly detector is a compact statistical baseline evaluated on synthetic data.
- Codebase Explorer returns source excerpts; it does not generate AI answers.
- ArmLab models two planar joints in free space.
- ControlCanvas supports a small, documented block library and solver contract.
- TaskTree Studio uses JSON authoring and simulated synchronous actions.
- CalibLab supports TCP and rigid registration; it does not perform hand-eye calibration or drive a robot.

## Next planned tools

| Project | Intended first workflow | Status |
|---|---|---|
| CloudLabel | Local point-cloud viewing and 3D annotations | Planned; no implementation yet |
| CellSketch | Workcell layouts and discrete-event process simulation | Planned; no implementation yet |

See [ROADMAP.md](ROADMAP.md) for project milestones. Improve existing workflows and collect evidence before treating an initial implementation as production software.

## Licensing

Original code in this repository is available under the [MIT license](LICENSE). Some folders also carry a copy of the license for standalone use. Third-party dependencies retain their own licenses.
