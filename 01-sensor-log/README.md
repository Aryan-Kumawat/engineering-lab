# Sensor Log

A dependency-free C++17 command-line tool for validating sensor CSV files and calculating statistics in a single pass with constant memory.

## Build and run

From this directory, with a C++17 compiler installed:

```sh
g++ -std=c++17 -Wall -Wextra -Wpedantic -O2 main.cpp -o sensor-log
./sensor-log samples.csv
```

Expected output:

```text
accepted=5 rejected=0
min=20.0000 max=28.0000 mean=24.0000
population_stddev=2.8284
```

## Data contract

The exact header is `timestamp,value`. Each subsequent row contains two finite numbers. Timestamps must be nonnegative and strictly increase relative to the last accepted sample. Values may be negative. Invalid rows are reported to stderr and excluded. This intentionally supports simple numeric CSV, without quoted fields or units.

Exit codes: 0 for a clean file, 1 for rejected rows or no accepted samples, 2 for usage, header, or file errors.

## Engineering decisions

Welford's algorithm computes the mean and population variance without storing all samples. Timestamp validation prevents accidental double counting of duplicate or reordered readings. A rejected sample does not advance the accepted timestamp.

## Limits and next steps

Input values use double precision. Extreme numeric magnitudes can overflow intermediate statistics. This version handles a single sensor channel. Useful extensions include configurable physical bounds, multiple channels, and JSON summaries.
