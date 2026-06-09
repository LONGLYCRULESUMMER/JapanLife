.PHONY: install serve ingest test clean

install:
	poetry install

serve:
	cd japan_life && poetry run adk web .

ingest:
	poetry run python -m rag.ingestion

test:
	poetry run pytest -v

clean:
	rm -rf chroma_db/ data/processed/ __pycache__/
