# Project-wide targets. Checks are registered in scripts/verify-checks.toml; units add their
# entries there, and any extra make targets in their own fragment included below.
# PYTHON can point at the project virtual environment, e.g. `make verify PYTHON=.venv/bin/python`.
PYTHON ?= python

.PHONY: verify verify-list

# Every applicable check (format, lint, types, tests with coverage, contracts, guard,
# integration and end-to-end when Docker is available, audits). Non-zero exit on any failure,
# or when a required check is skipped. It never deletes Docker volumes or developer data.
verify:
	$(PYTHON) scripts/verify.py --strict

verify-list:
	$(PYTHON) scripts/verify.py --list

# Unit-specific targets (present only on branches that carry the unit).
-include local/slice.mk
