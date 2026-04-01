# Multi-stage build
FROM node:20 AS frontend-build
WORKDIR /app/finguard-ui
COPY finguard-ui/package*.json ./
RUN npm install
COPY finguard-ui/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

# Install system dependencies (for building some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Copy built frontend
COPY --from=frontend-build /app/finguard-ui/dist /app/finguard-ui/dist

# Expose port
EXPOSE 8000

# Run API (api.py will be modified to mount StaticFiles mapping to finguard-ui/dist at root level)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
