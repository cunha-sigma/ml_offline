# Makefile — ML offline design, compiled PDF (design_docs 00-09 + annex)
# Requires: pandoc on PATH (brew install pandoc). Node deps installed locally.

.DEFAULT_GOAL := help
.PHONY: help install pdf clean

help:             ## Show this help
	@echo "Targets: make install | make pdf | make clean"

install:          ## Install Node dependencies (once)
	npm install

pdf:               ## Build ml-offline-design.pdf from design_docs/ + annex
	@command -v pandoc >/dev/null 2>&1 || { echo "pandoc not found — brew install pandoc"; exit 1; }
	node build/render.mjs

clean:             ## Remove build output
	rm -rf build/out ml-offline-design.pdf
