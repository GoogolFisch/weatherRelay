#!/env/bin/env bash

# ai told me
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Change to that directory
cd "$SCRIPT_DIR" || exit

source ./bin/activate

./main.py

deactivate
