#!/usr/bin/env bash

# ai told me
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Change to that directory
cd "$SCRIPT_DIR" || exit

python3 ./sensor-bme280.py &
source ./bin/activate

./main.py

deactivate
