#!/bin/bash
# Start MCP Orchestrator with network access

echo "🚀 Starting MCP Orchestrator Network Services"
echo "============================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and add your API keys"
    exit 1
fi

# Export environment variables
export $(grep -v '^#' .env | xargs)

# Check API keys
if [ -z "$OPENROUTER_API_KEY" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Missing API keys in .env file!"
    echo "Please set OPENROUTER_API_KEY and OPENAI_API_KEY"
    exit 1
fi

# Stop any existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.network.yml down

# Build the image
echo "Building Docker image..."
docker-compose -f docker-compose.network.yml build

# Start services
echo "Starting services..."
docker-compose -f docker-compose.network.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Check service status
echo -e "\n📊 Service Status:"
docker-compose -f docker-compose.network.yml ps

# Test REST API
echo -e "\n🧪 Testing REST API..."
curl -s http://localhost:5050/health | jq '.' || echo "REST API not ready yet"

echo -e "\n✅ Services started!"
echo ""
echo "📡 Available endpoints:"
echo "  - REST API: http://localhost:5050"
echo "  - WebSocket: ws://localhost:8765"
echo ""
echo "📚 Examples:"
echo "  - curl http://localhost:5050/tools"
echo "  - wscat -c ws://localhost:8765"
echo ""
echo "📝 Run ./test_network_access.py for full test suite"
echo ""
echo "🛑 To stop: docker-compose -f docker-compose.network.yml down"