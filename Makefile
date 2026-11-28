UV := uv --config-file ./uv.toml

.PHONY: install test run webapp

install:
	$(UV) sync

test:
	$(UV) run pytest -v

coverage:
	$(UV) run pytest --cov --cov-report=term-missing tests

run:
	uv --config-file ./uv.toml run python -m football_team_assistant.main

server:
	uvicorn api.app:app --reload

webapp:
	$(UV) run --locked uvicorn football_team_assistant.web_chat.app:app \
		--host 127.0.0.1 --port 8001 --workers 1 --no-proxy-headers --no-access-log

client:
	uv run python -m football_team_assistant.mcp_client

agent:
	uv run python -m football_team_assistant.mcp_agent
lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format:
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

db:
	docker compose up -d
