SHELL := /bin/bash

.PHONY: stop
stop:
	@set -euo pipefail; \
	echo "Stopping Chainlit and FastAPI (uvicorn) if running..."; \
	pkill -f "chainlit" 2>/dev/null || true; \
	pkill -f "uvicorn" 2>/dev/null || true; \
	pkill -f "fastapi_backend.py" 2>/dev/null || true; \
	pkill -f "python.*chainlit" 2>/dev/null || true; \
	pkill -f "python.*uvicorn" 2>/dev/null || true; \
	for PORT in 8080 8001; do \
	  PID=$$(lsof -t -i:$$PORT || true); \
	  if [ -n "$$PID" ]; then \
	    echo "Port $$PORT in use by PID(s): $$PID. Sending TERM..."; \
	    kill -TERM $$PID 2>/dev/null || true; \
	    sleep 1; \
	    PID_AFTER=$$(lsof -t -i:$$PORT || true); \
	    if [ -n "$$PID_AFTER" ]; then \
	      echo "PID(s) $$PID_AFTER still holding port $$PORT. Forcing kill..."; \
	      kill -9 $$PID_AFTER 2>/dev/null || true; \
	    fi; \
	  fi; \
	done; \
	echo "Verifying..."; \
	for PORT in 8080 8001; do \
	  if lsof -nP -iTCP:$$PORT -sTCP:LISTEN >/dev/null 2>&1; then \
	    echo "⚠️ Port $$PORT still in use" >&2; \
	  else \
	    echo "✅ Port $$PORT free"; \
	  fi; \
	done; \
	echo "Done.";


