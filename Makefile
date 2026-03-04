.PHONY: install dev test db-migrate seed snowflake-schema deploy lint clean help

# Default target
help:
	@echo "Portfolio Intelligence Hub - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install              Install dependencies"
	@echo "  make dev                  Run development server"
	@echo "  make test                 Run test suite"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate           Run database migrations"
	@echo "  make seed                 Seed database with sample data"
	@echo "  make snowflake-schema     Initialize Snowflake schemas"
	@echo ""
	@echo "Maintenance:"
	@echo "  make lint                 Run linters and formatters"
	@echo "  make clean                Clean up temporary files"
	@echo "  make deploy               Deploy to production"

install:
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	cd frontend && npm install || true

dev:
	@echo "Starting development environment..."
	docker-compose up -d
	@echo "Waiting for services to start..."
	sleep 3
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	@echo "Running test suite..."
	pytest tests/ -v --cov=src --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

db-migrate:
	@echo "Running database migrations..."
	alembic upgrade head

seed:
	@echo "Seeding database with sample data..."
	python scripts/seed_database.py

snowflake-schema:
	@echo "Initializing Snowflake schemas and objects..."
	python scripts/init_snowflake.py

deploy:
	@echo "Deploying to production..."
	vercel deploy --prod
	@echo "Deployment complete!"

lint:
	@echo "Running linters..."
	black src/ tests/ scripts/ --line-length=100
	isort src/ tests/ scripts/ --profile black
	flake8 src/ tests/ scripts/ --max-line-length=100
	mypy src/ --ignore-missing-imports
	@echo "Linting complete!"

clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete
	rm -rf dist/ build/ *.egg-info/
	@echo "Cleanup complete!"

.PHONY: docker-build docker-push
docker-build:
	@echo "Building Docker image..."
	docker build -t portfolio-intelligence-hub:latest .

docker-push: docker-build
	@echo "Pushing Docker image..."
	docker push portfolio-intelligence-hub:latest
