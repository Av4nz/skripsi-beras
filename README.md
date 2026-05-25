# Skripsi Prediksi Beras

This repository is a monorepo containing both the Next.js Frontend and the FastAPI Backend for the rice price prediction thesis project.

## Requirements
- [Bun](https://bun.sh/) (for the frontend)
- [Python 3](https://www.python.org/) (for the backend)
- Make (built-in on MacOS/Linux. Windows users can use Git Bash, WSL, or install Make)

## Quick Setup (Recommended)

This project includes a cross-platform `Makefile` that automatically handles dependencies and runs both servers simultaneously.

### 1. Install Dependencies
Run the following command at the root of the project. It will automatically run `bun install` for the frontend and set up a Python `.venv` for the backend.
```bash
make install
```

### 2. Run Development Servers
To start both the Next.js frontend and the FastAPI backend at the exact same time:
```bash
make dev
```
Press `Ctrl+C` to stop both servers.

---

## Manual Setup

If you prefer to run things manually or don't have `make` installed:

### Backend (FastAPI)
Create your own virtual environment and install the dependencies:

**For Windows:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**For MacOS/Linux:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**To run the backend manually:**
```bash
python -m uvicorn app.main:app --reload
```

### Frontend (Next.js)
Install the required packages:
```bash
cd frontend
bun install
```

**To run the frontend manually:**
```bash
bun run dev
```
