docker:
	docker compose up -d

tests: 
	pytest -v