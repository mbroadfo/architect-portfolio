# Walking slice (U0, S1 to S3) targets, included by the root Makefile. Demonstration branch
# only; everything runs locally.

.PHONY: slice-setup slice-verify slice-check slice-down

# One-time project-local setup: npm packages and the Playwright browser (into web/node_modules).
slice-setup:
	npm --prefix web ci
	npm --prefix web/slice-renderer ci
	npm --prefix web/slice-studio ci
	cd web && PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install chromium

# Only the walking slice's registered checks (the U0-specific verification target).
slice-verify:
	$(PYTHON) scripts/verify.py --unit walking-slice --strict

# W6 on its own: create, save, preview and publish end to end in this checkout's isolated
# portfolio-verify-<checkout id> stack (tmpfs database, free ports chosen per run), then the
# public-output scan. It stops that stack afterwards with a plain `down` (containers and
# network only) and never removes volumes.
slice-check:
	$(PYTHON) local/slice_check.py

# Explicit, manual cleanup of the developer's own demo stack (local/compose.yaml, project
# portfolio-slice). This removes that stack's volumes; nothing runs it automatically.
slice-down:
	docker compose -f local/compose.yaml down -v
