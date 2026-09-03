#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."
python3 -m unittest tests.test_credential_states -v
