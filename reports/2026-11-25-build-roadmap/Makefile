# Makefile — build roadmap deck (Slidev)
# Single source: slides.md  |  Slidev project: deck/  |  Output: build-roadmap-deck.pdf
#
#   make install   (once)
#   make pdf       -> regenerates build-roadmap-deck.pdf from slides.md
#   make dev       -> live preview + presenter mode

DECK := deck
PDF  := build-roadmap-deck.pdf

# npm comes from nvm, which only loads in interactive zsh; make runs
# /bin/sh. Append the newest nvm node bin dir so make works anywhere.
NODE_BIN := $(shell ls -d $(HOME)/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -1)
ifneq ($(NODE_BIN),)
export PATH := $(PATH):$(NODE_BIN)
endif

.DEFAULT_GOAL := help
.PHONY: help install dev build pdf clean

help:             ## Show this help
	@echo "Targets: make install | make dev | make build | make pdf | make clean"

install:          ## Install Slidev dependencies (once)
	cd $(DECK) && npm install

dev:              ## Live preview (localhost); 'p' opens Presenter Mode
	cd $(DECK) && npm run dev

build:            ## Compile to dist/ (validates slides and diagrams)
	cd $(DECK) && npm run build

pdf:              ## Generate/regenerate the PDF
	cd $(DECK) && npm run export
	@echo ">> PDF generated: $(PDF)"

clean:            ## Remove PDF and build output
	rm -rf $(DECK)/dist $(PDF)
