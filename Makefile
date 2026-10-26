UV := uv --config-file ./uv.toml

.PHONY: install test run

install:
	$(UV) sync

test:
	$(UV) run pytest -v

run:
	$(UV) run python main.py

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format:
	$(UV) run ruff check --fix .
	$(UV) run ruff format .