# Multi-stage build for efficient image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN useradd -m -u 1000 mcp && \
    mkdir -p /home/mcp/.config/mcp_orchestrator && \
    chown -R mcp:mcp /home/mcp

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=mcp:mcp . /app/

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R mcp:mcp /app

# Switch to non-root user
USER mcp

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# MCP servers communicate via stdio
# Use the enhanced MCP server with all features
ENTRYPOINT ["python", "/app/src/mcp_server.py"]