UV := uv --config-file ./uv.toml

.PHONY: install test run

install:
	$(UV) sync

test:
	$(UV) run pytest -v

coverage:
	$(UV) run pytest --cov --cov-report=term-missing tests

run:
	$(UV) run python main.py

server:
	uvicorn api.app:app --reload

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format:
	$(UV) run ruff check --fix .
	$(UV) run ruff format .
