.PHONY: install install-frontend install-backend dev dev-frontend dev-backend

install: install-frontend install-backend
	@echo "All dependencies installed successfully!"

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && bun install

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

dev:
	@echo "Starting both servers concurrently. Press Ctrl+C to stop both."
	@make -j2 dev-frontend dev-backend

dev-frontend:
	cd frontend && bun run dev

dev-backend:
	cd backend && .venv/bin/python -m uvicorn app.main:app --reload
