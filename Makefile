.PHONY: install up down ingest eval test test-all serve build logs ingest-docker demo

install:
	poetry install

up:
	docker compose up -d --build

down:
	docker compose down

ingest:
	poetry run python -m rag.ingest

eval:
	poetry run python -m eval.run_eval

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
