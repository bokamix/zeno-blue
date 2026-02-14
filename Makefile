CONTAINER_NAME := zeno

build:
	docker build -t user-container \
		--build-arg BUILD_VERSION=$$(git describe --tags --always 2>/dev/null || echo "dev") \
		--build-arg GIT_HASH=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
		--build-arg BUILD_TIME=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
		.

# Start with docker-compose
up:
	BUILD_VERSION=$$(git describe --tags --always 2>/dev/null || echo "dev") \
	GIT_HASH=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
	BUILD_TIME=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
	docker compose up --build

# Start in detached mode
up-d:
	BUILD_VERSION=$$(git describe --tags --always 2>/dev/null || echo "dev") \
	GIT_HASH=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
	BUILD_TIME=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
	docker compose up --build -d

# Stop docker compose
down:
	docker compose down

# View logs
logs:
	docker compose logs -f app

# Alias for 'up' (legacy compatibility)
dev: up

run:
	docker run --rm -it \
	  --name $(CONTAINER_NAME) \
	  -p 18000:8000 \
	  -v "$$(pwd)/workspace:/workspace" \
	  -v "$$(pwd)/data:/data" \
	  --env-file .env \
	  user-container

# Execute Python code in running container (interactive, for humans)
# Usage: make exec CMD="from agent.llm_client import LLMClient; print(LLMClient.default().model)"
exec:
	docker exec -it $(CONTAINER_NAME) python -c "import sys; sys.path.insert(0, '/app/user_container'); $(CMD)"

# Execute Python code in running container (non-interactive, for AI agents/scripts)
# Usage: make py CMD="from jobs.job import Job; print(Job(conversation_id='test', message='hi').id)"
py:
	@docker exec $(CONTAINER_NAME) python -c "import sys; sys.path.insert(0, '/app/user_container'); $(CMD)"

# Interactive Python shell in container
shell:
	docker exec -it $(CONTAINER_NAME) bash -c "cd /app/user_container && python"

# Bash shell in container (interactive, for humans)
bash:
	docker exec -it $(CONTAINER_NAME) bash

# Run bash command in container (non-interactive, for AI agents/scripts)
# Usage: make sh CMD="ls -la /workspace"
sh:
	@docker exec $(CONTAINER_NAME) bash -c "$(CMD)"

test:
	docker run --rm -it \
	  -v "$$(pwd)/workspace:/workspace" \
	  -v "$$(pwd)/data:/data" \
	  -v "$$(pwd)/user_container:/app/user_container" \
	  -v "$$(pwd)/tests:/app/tests" \
	  --env-file .env \
	  user-container \
	  python -m tests.test_agent_integration

# Frontend development (runs on host, proxies to container backend)
frontend-dev:
	cd frontend && npm run dev

# Install frontend dependencies (on host)
frontend-install:
	cd frontend && npm install

# Build frontend (on host)
frontend-build:
	cd frontend && npm run build
