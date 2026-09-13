PYTHON ?= /usr/local/bin/python3
UV = uv --no-managed-python --no-python-downloads
RUN = PYTHONPATH=.:src .venv/bin/python
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
	$(RUN) -m pytest -q services/bridge/tests
	$(RUN) -m pytest -q services/training/tests
	.venv/bin/ruff check src tests modules tools/*.py
	node --import tsx --test packages/audio/tests/*.test.ts apps/web/src/muse/tests/*.test.ts apps/training/tests/*.test.ts
	node_modules/.bin/tsc -p apps/training/tsconfig.json
	npm run typecheck
	npm run build

typecheck:
	npm run typecheck

check-locks:
	$(UV) lock --locked --python $(PYTHON)
	uv pip check --python .venv/bin/python
	npm ls --all

assets:
	$(RUN) -m scenescore.cli $@

demo dev-replay:
	$(RUN) tools/demo.py

service:
	PYTHONPATH=.:src .venv/bin/uvicorn scenescore.service:app --host 127.0.0.1 --port 8765

.PHONY: muse-demo muse-diagnose muse-readiness
muse-demo:
	$(RUN) tools/muse_demo.py

muse-diagnose:
	$(RUN) -m modules.muse.acquisition diagnose

muse-readiness:
	$(RUN) -m modules.muse.training --data-root private_data/02A --output reports/muse-vertical/detector/readiness.json

.PHONY: muse-train
muse-train:
	$(RUN) tools/muse_training.py

.PHONY: music-demo
music-demo:
	$(RUN) tools/music_demo.py
