# AnythingToMarkdown — common developer tasks.
# Usage: `make <target>`. Run `make help` (or just `make`) to list targets.

# ---- Configuration ---------------------------------------------------------
VENV        := .venv
PYTHON      := $(VENV)/bin/python
PIP         := $(PYTHON) -m pip
APP_NAME    := AnythingToMarkdown
SPEC        := packaging/$(APP_NAME).spec

# Python interpreter used to *create* the venv (must be 3.10+).
# Override with: make venv BOOTSTRAP_PY=python3.13
BOOTSTRAP_PY ?= $(shell for p in python3.13 python3.12 python3.11 python3.10 python3; do \
	command -v $$p >/dev/null 2>&1 && v=$$($$p -c 'import sys;print(sys.version_info>=(3,10))' 2>/dev/null) && [ "$$v" = "True" ] && { echo $$p; break; }; done)

# Arguments forwarded to the CLI, e.g. `make cli ARGS="file.pdf --stdout"`.
ARGS ?=

.DEFAULT_GOAL := help

# ---- Help ------------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@echo "$(APP_NAME) — available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ---- Environment -----------------------------------------------------------
$(VENV): ## (internal) create the virtual environment
	@if [ -z "$(BOOTSTRAP_PY)" ]; then \
		echo "Error: no Python 3.10+ found. Set BOOTSTRAP_PY=/path/to/python" >&2; exit 1; fi
	@echo "Creating venv with $(BOOTSTRAP_PY)…"
	$(BOOTSTRAP_PY) -m venv $(VENV)
	$(PIP) install --upgrade pip

.PHONY: venv
venv: $(VENV) ## Create the virtual environment (if missing)

# Stamp file: re-installs only when requirements.txt changes (keeps runs quiet).
$(VENV)/.installed: requirements.txt | $(VENV)
	$(PIP) install -r requirements.txt
	@touch $@

.PHONY: install
install: $(VENV)/.installed ## Install runtime dependencies into the venv

.PHONY: dev
dev: install ## Editable install so the `anytomd` command is available
	$(PIP) install -e .

# ---- Run -------------------------------------------------------------------
.PHONY: run gui
run gui: install ## Launch the GUI
	$(PYTHON) -m anytomd

.PHONY: cli
cli: install ## Run the CLI, e.g. make cli ARGS="file.pdf -o out/"
	$(PYTHON) -m anytomd $(ARGS)

# ---- Build (macOS app) -----------------------------------------------------
.PHONY: app
app: install ## Build the clickable macOS .app (dist/$(APP_NAME).app)
	$(PIP) install --quiet pyinstaller
	cd packaging && ../$(PYTHON) -m PyInstaller $(APP_NAME).spec \
		--noconfirm --clean --distpath ../dist --workpath ../build
	@echo "Built: dist/$(APP_NAME).app  (open it with: make open-app)"

.PHONY: dmg
dmg: ## Build a distributable macOS .dmg (builds the app first if needed)
	packaging/build_dmg.sh

.PHONY: notarize
notarize: ## Sign, notarize & staple the app + dmg (needs Apple Developer ID; see packaging/notarize.sh)
	packaging/notarize.sh

.PHONY: open-app
open-app: ## Open the built macOS app
	open dist/$(APP_NAME).app

.PHONY: icon
icon: install ## Regenerate the macOS app icon (packaging/AppIcon.icns)
	$(PYTHON) packaging/make_icon.py
	iconutil -c icns packaging/AppIcon.iconset -o packaging/AppIcon.icns
	@echo "Wrote packaging/AppIcon.icns"

# ---- Housekeeping ----------------------------------------------------------
.PHONY: clean
clean: ## Remove build/dist artifacts (keeps the venv)
	rm -rf build dist *.egg-info anytomd.egg-info packaging/AppIcon.iconset
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

.PHONY: clean-all
clean-all: clean ## Remove everything, including the virtual environment
	rm -rf $(VENV)
