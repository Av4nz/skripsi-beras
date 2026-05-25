.PHONY: install install-frontend install-backend dev dev-frontend dev-backend

ifeq ($(OS),Windows_NT)
    PYTHON = python
    VENV_BIN = .venv/Scripts
else
    PYTHON = python3
    VENV_BIN = .venv/bin
endif

install: install-frontend install-backend
	@echo "All dependencies installed successfully!"

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && bun install

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && $(PYTHON) -m venv .venv && $(VENV_BIN)/pip install -r requirements.txt

dev:
	@echo "Starting both servers concurrently. Press Ctrl+C to stop both."
	@make -j2 dev-frontend dev-backend

dev-frontend:
	cd frontend && bun run dev

dev-backend:
	cd backend && $(VENV_BIN)/python -m uvicorn app.main:app --reload
