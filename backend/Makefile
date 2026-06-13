.PHONY: install dev run lint format test typecheck precommit-install docker-build docker-up docker-down

install:  ## Install runtime + dev dependencies into the current environment
	pip install -e ".[dev]"

dev:  ## Run the API with autoreload (honours PORT, defaults 8000)
	uvicorn app.main:app --reload --host 127.0.0.1 --port $${PORT:-8000}

run:  ## Run the API (no reload; honours PORT, defaults 8000)
	uvicorn app.main:app --host 0.0.0.0 --port $${PORT:-8000}

lint:  ## Lint with ruff (check + format verification)
	ruff check .
	ruff format --check .

format:  ## Auto-format and auto-fix with ruff
	ruff format .
	ruff check --fix .

test:  ## Run the test suite with coverage (offline; live LLM eval is skipped)
	pytest

eval:  ## Run the live LLM output-quality eval against the real Groq model
	pytest -m llm_eval -p no:cacheprovider

typecheck:  ## Run mypy static type checking
	mypy app/

precommit-install:  ## Install the git pre-commit hooks
	pre-commit install

docker-build:  ## Build the stack via docker compose
	docker compose -f ../docker-compose.yml build

docker-up:  ## Start the full stack (backend + frontend)
	docker compose -f ../docker-compose.yml up -d

docker-down:  ## Stop the stack
	docker compose -f ../docker-compose.yml down
