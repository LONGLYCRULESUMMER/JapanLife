.PHONY: install web-install web-dev web-build up down ingest eval answer-eval answer-eval-stub ingest-job-demo cache-test test test-all serve build logs ingest-docker demo

install:
	poetry install

web-install:
	cd web && npm install

web-dev:
	cd web && npm run dev

web-build:
	cd web && npm run build

up:
	docker compose up -d --build

down:
	docker compose down

ingest:
	poetry run python -m rag.ingest

eval:
	poetry run python -m eval.run_eval

answer-eval:
	poetry run python -m eval.run_answer_eval

answer-eval-stub:
	poetry run python -m eval.run_answer_eval --stub

ingest-job-demo:
	@JOB=$$(curl -s -X POST localhost:8000/admin/ingest | poetry run python -c "import sys,json;print(json.load(sys.stdin)['id'])"); \
	echo "submitted job: $$JOB"; sleep 2; \
	curl -s localhost:8000/admin/ingest/jobs/$$JOB

cache-test:
	poetry run pytest -q tests/test_cache.py

test:
	poetry run pytest -v -m "not integration"

test-all:
	poetry run pytest -v

serve:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

build:
	docker compose build

logs:
	docker compose logs -f api

ingest-docker:
	docker compose run --rm api python -m rag.ingest

demo:
	poetry run streamlit run streamlit_app.py
