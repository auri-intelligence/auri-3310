#!/bin/sh
cd "$(dirname "$0")" && exec .venv/bin/python auri_bridge.py "$@"
