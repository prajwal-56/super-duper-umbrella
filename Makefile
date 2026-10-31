PY ?= .venv/bin/python
PIP ?= .venv/bin/pip

export DATABASE_URL ?= postgresql://postgres:postgres@localhost:5432/brightloop
export TEST_DATABASE_URL ?= postgresql://postgres:postgres@localhost:5432/brightloop_test
export SECRET_KEY ?= dev-only-change-me
export APP_BASE_URL ?= http://localhost:8000

.PHONY: setup db-up db-down migrate seed seed-scale dev test lint style-lint \
	check-stubs check invariants perf reset-demo status

setup:
	python3 -m venv .venv
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -r requirements.txt
	@echo "setup: dependencies installed in .venv"

db-up:
	docker compose up -d db
	@printf "db-up: waiting for postgres"
	@until docker compose exec -T db pg_isready -U postgres -d brightloop >/dev/null 2>&1; do \
		printf "."; sleep 1; done
	@echo " ready"

db-down:
	docker compose down
	@echo "db-down: postgres stopped (data volume kept)"

migrate:
	$(PY) -m app.migrate

seed:
	$(PY) scripts/seed_demo.py

seed-scale:
	$(PY) scripts/seed_scale.py

dev:
	$(PY) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check .

style-lint:
	$(PY) scripts/style_lint.py

check-stubs:
	$(PY) scripts/check_stubs.py

check: lint style-lint
	@$(PY) scripts/check_stubs.py --report
	$(PY) -m pytest -q

invariants:
	@$(PY) -c "from app.db import conn; from app.services.invariants import run_all; c = conn().__enter__(); results = run_all(c); [print(('PASS' if r.ok else 'FAIL'), r.id, r.name, f'violations={r.violations}') for r in results]; failed = [r.id for r in results if not r.ok]; print(f'invariants: {len(results)} checks, {len(failed)} failing'); raise SystemExit(1 if failed else 0)"

perf:
	$(PY) scripts/perf_check.py

reset-demo:
	$(PY) scripts/seed_demo.py --reset

status:
	@for f in docs/log/*.md; do echo "== $$f"; tail -n 12 "$$f"; echo; done
	@gh issue list --state open 2>/dev/null || echo "(gh unavailable - logs only)"
