.PHONY: install dev dev-api dev-worker dev-frontend build test clean generate

# Install all dependencies
install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

# Run everything in development mode
dev:
	make dev-api & make dev-worker & make dev-frontend

# Backend API server
dev-api:
	cd backend && uvicorn app.main:app --reload --port 8000

# Background scheduler worker
dev-worker:
	cd backend && python worker.py

# Frontend dev server
dev-frontend:
	cd frontend && npm run dev

# Database migrations
db-upgrade:
	cd backend && alembic upgrade head

db-migrate:
	cd backend && alembic revision --autogenerate -m "$(msg)"

# Run backend tests
test:
	cd backend && pytest -v

# Build frontend for production
build:
	cd frontend && npm run build

# Generate daily briefing (fetch news + export HTML)
generate:
	cd backend && python generate_briefing.py

# Clean generated files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/dist
	rm -rf backend/.pytest_cache
