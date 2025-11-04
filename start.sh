#!/usr/bin/env bash

# ai told me
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Change to that directory
cd "$SCRIPT_DIR" || exit

source ./bin/activate

python3 ./sensor-bme280.py &
./main.py

deactivate
