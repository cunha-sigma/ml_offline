# Tract op-coverage & parity test. See README.md.
#
#   make setup   (once)  venv + deps
#   make ops     phase 1: operator inventory (onnx package only)
#   make run     phases 2-5: tract load/type/parity/timing
#   make all     everything

PY := .venv/bin/python

.DEFAULT_GOAL := all
.PHONY: all setup ops run clean

all: ops run

setup:
	python3 -m venv .venv
	.venv/bin/pip -q install onnx numpy tract

ops:
	$(PY) inspect_ops.py

run:
	$(PY) run_tract.py

clean:
	rm -rf .venv __pycache__
