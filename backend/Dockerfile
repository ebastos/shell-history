FROM python:3.11-slim

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy the entire workspace
COPY . .

# Sync dependencies for the whole workspace
RUN uv sync --no-dev --frozen

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run application using uv run from the backend member
CMD ["uv", "run", "--project", "backend", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
