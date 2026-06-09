.PHONY: install up down ingest eval test test-all

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
