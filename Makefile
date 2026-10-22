docker:
	docker compose up -d

tests: 
	pytest -v

integration:
	pytest tests/integration -v