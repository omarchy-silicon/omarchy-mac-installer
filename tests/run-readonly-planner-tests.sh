#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=src python3 -m unittest tests.test_readonly_installer_planner -v
