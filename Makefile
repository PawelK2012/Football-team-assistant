UV := uv --config-file ./uv.toml

.PHONY: install test run

install:
	$(UV) sync

test:
	$(UV) run pytest -v

run:
	$(UV) run python main.py