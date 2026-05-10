.PHONY: install run lint test

install:
	pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check .

test:
	pytest -q
