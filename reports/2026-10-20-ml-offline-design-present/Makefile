# Makefile — ML offline design deck (Slidev)
# Single source: slides.md  |  Slidev project: deck/  |  Output: ml-offline-design-deck.pdf
#
#   make install   (once)
#   make pdf       -> regenerates ml-offline-design-deck.pdf from slides.md
#   make dev       -> live preview + presenter mode

DECK := deck
PDF  := ml-offline-design-deck.pdf

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
