# Engineering Lab

A growing portfolio of practical projects in programming, embedded systems, machine learning, and software systems. Each project is designed to teach a concept, demonstrate engineering decisions, and provide a reproducible way to run the result.

## Learning path

| Level | Project | Focus |
|---|---|---|
| Beginner | `01-sensor-log` | C++ basics, sensor data, CSV logging |
| Beginner+ | `02-pid-playground` | Control theory, simulation, visualization |
| Intermediate | `03-tinyml-anomaly-detector` | Feature engineering, model evaluation, edge constraints |
| Advanced | `04-robot-telemetry` | Protocol design, reliability, observability |
| Pro | `05-local-codebase-intelligence` | Indexing, retrieval, evaluation, privacy |

## Repository principles

- Every project has its own README, setup steps, example input, and expected output.
- Results include measurements where useful; claims are backed by reproducible runs.
- No API keys or personal data belong in committed files.
- Projects grow in difficulty and reuse ideas from earlier work.

## Status

Six projects are implemented:

1. [Sensor Log](01-sensor-log/) — C++ CSV validation and streaming statistics.
2. [PID Playground](02-pid-playground/) — desktop gain tuning and CSV simulation.
3. [Compact Anomaly Detector](03-tinyml-anomaly-detector/) — quantized statistical model, synthetic training and held-out evaluation.
4. [Robot Telemetry](04-robot-telemetry/) — local collector, bounded ingestion and acknowledged replay.
5. [Local Codebase Explorer](05-local-codebase-intelligence/) — SQLite FTS search with source citations.

These are scoped learning implementations. Each README explains assumptions, limitations and ways to extend the project. The advanced topics are foundations for deeper work rather than claims of production readiness.

## Check the projects

Python 3.10+ with SQLite FTS5, plus a C++17 compiler for Sensor Log:

```sh
python check_projects.py
python -m unittest discover -s 02-pid-playground -v
g++ -std=c++17 -Wall -Wextra -Wpedantic -O2 01-sensor-log/main.cpp -o sensor-log
./sensor-log 01-sensor-log/samples.csv
```

No paid APIs or pip dependencies are required. PID GUI mode needs Tkinter and a desktop display. Integration checks start a temporary localhost TCP server.

6. [ArmLab](06-armlab/) — planar robot arm planning, animation and CSV export.
