PYTHON ?= /usr/local/bin/python3
UV = uv --no-managed-python --no-python-downloads
RUN = PYTHONPATH=src .venv/bin/python
.PHONY: install doctor test-contracts test typecheck dev-replay assets demo service check-locks
install:
	$(UV) sync --locked --python $(PYTHON)
	npm ci --ignore-scripts --no-audit --no-fund
	npm run generate

doctor:
	$(RUN) -m scenescore.cli doctor

test-contracts:
	$(RUN) -m scenescore.cli test-contracts
	npm run test:contracts

test: test-contracts
	$(RUN) -m pytest -q
	.venv/bin/ruff check src tests tools/*.py
	npm run typecheck
	npm run build

typecheck:
	npm run typecheck

check-locks:
	$(UV) lock --locked --python $(PYTHON)
	uv pip check --python .venv/bin/python
	npm ls --all

dev-replay assets demo:
	$(RUN) -m scenescore.cli $@

service:
	PYTHONPATH=src .venv/bin/uvicorn scenescore.service:app --host 127.0.0.1 --port 8765
