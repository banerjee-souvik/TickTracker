.PHONY: dev backend frontend kill

dev: kill
	@echo "Starting backend and frontend..."
	@trap 'kill 0' SIGINT; \
	(cd backend && venv/bin/uvicorn main:app --reload --port 8000) & \
	(cd frontend && yarn dev) & \
	wait

backend:
	cd backend && venv/bin/uvicorn main:app --reload --port 8000

frontend:
	cd frontend && yarn dev

kill:
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@lsof -ti:3000 | xargs kill -9 2>/dev/null || true
