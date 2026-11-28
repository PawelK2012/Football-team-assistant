UV := uv --config-file ./uv.toml
CHAT_APP := football_team_assistant.web_chat.app:app
ADMIN_APP := football_team_assistant.web_admin.app:app
CHAT_PORT := 8001
ADMIN_PORT := 8002
WEB_FLAGS := --host 127.0.0.1 --workers 1 --no-proxy-headers --no-access-log

.PHONY: install test run webapp admin web

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
	$(UV) run --locked uvicorn $(CHAT_APP) --port $(CHAT_PORT) $(WEB_FLAGS)

admin:
	$(UV) run --locked uvicorn $(ADMIN_APP) --port $(ADMIN_PORT) $(WEB_FLAGS)

web:
	$(UV) run --locked python -m football_team_assistant.web \
		$(CHAT_APP) $(CHAT_PORT) $(ADMIN_APP) $(ADMIN_PORT) $(WEB_FLAGS)

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
