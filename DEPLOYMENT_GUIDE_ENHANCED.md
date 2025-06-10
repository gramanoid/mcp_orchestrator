# MCP Orchestrator Deployment Guide

## 🚀 Quick Start (Any Claude Code Instance)

### Option 1: Using Pre-built Docker Image (Recommended)

```bash
# 1. Clone the repository (or download deployment package)
git clone https://github.com/yourusername/mcp_orchestrator.git
cd mcp_orchestrator

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run deployment script
./deploy_mcp.sh
# Choose option 1 for full deployment
```

### Option 2: Manual Docker Setup

```bash
# 1. Pull or build the image
docker build -t mcp-orchestrator:enhanced .

# 2. Create .env file with your API keys
cat > .env << EOL
OPENROUTER_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
EOL

# 3. Add to Claude Code
claude mcp add mcp-orchestrator "docker run --rm -i --env-file $(pwd)/.env mcp-orchestrator:enhanced"
```

### Option 3: Using Docker Compose

```bash
# 1. Start the service
docker-compose -f docker-compose.mcp-enhanced.yml up -d

# 2. Add to Claude Code
claude mcp add mcp-orchestrator "docker-compose -f $(pwd)/docker-compose.mcp-enhanced.yml exec -T mcp-orchestrator python /app/src/mcp_server.py"
```

## 📦 Deployment Package

For easy sharing with team members:

```bash
# Create deployment package
./deploy_mcp.sh
# Choose option 4

# This creates mcp-orchestrator-deploy.tar.gz
# Share this file with your team
```

Team members can then:
```bash
# Extract package
tar -xzf mcp-orchestrator-deploy.tar.gz
cd mcp_orchestrator

# Deploy
./deploy_mcp.sh
```

## 🔧 Platform-Specific Instructions

### macOS
```bash
# Ensure Docker Desktop is running
open -a Docker

# Deploy
./deploy_mcp.sh
```

### Windows (WSL2)
```bash
# In WSL2 terminal
cd /home/username/mcp_orchestrator
./deploy_mcp.sh

# Note: Use WSL2 paths in Claude Code
```

### Linux
```bash
# Ensure Docker daemon is running
sudo systemctl start docker

# Add user to docker group (if needed)
sudo usermod -aG docker $USER

# Deploy
./deploy_mcp.sh
```

## 🐳 Docker Image Management

### Building Images

```bash
# Build with specific tag
docker build -t mcp-orchestrator:v1.0.0 .

# Build with multiple tags
docker build -t mcp-orchestrator:latest -t mcp-orchestrator:enhanced .

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t mcp-orchestrator:multi .
```

### Publishing Images

```bash
# Tag for registry
docker tag mcp-orchestrator:enhanced myregistry.com/mcp-orchestrator:enhanced

# Push to registry
docker push myregistry.com/mcp-orchestrator:enhanced

# For GitHub Container Registry
docker tag mcp-orchestrator:enhanced ghcr.io/username/mcp-orchestrator:enhanced
docker push ghcr.io/username/mcp-orchestrator:enhanced
```

### Using Published Images

```bash
# Pull from registry
docker pull ghcr.io/username/mcp-orchestrator:enhanced

# Add to Claude Code
claude mcp add mcp-orchestrator "docker run --rm -i --env-file .env ghcr.io/username/mcp-orchestrator:enhanced"
```

## 🔐 Security Best Practices

### 1. API Key Management

Never commit API keys! Use one of these methods:

**Docker Secrets (Swarm mode)**:
```bash
echo "your_api_key" | docker secret create openrouter_key -
docker service create --secret openrouter_key mcp-orchestrator:enhanced
```

**Environment File**:
```bash
# Create .env file (gitignored)
cat > .env << EOL
OPENROUTER_API_KEY=insert_your_api_key_here
OPENAI_API_KEY=insert_your_api_key_here
EOL

# Set restrictive permissions
chmod 600 .env
```

**HashiCorp Vault**:
```bash
# Store in Vault
vault kv put secret/mcp-orchestrator openrouter_key=insert_your_api_key_here

# Retrieve at runtime
export OPENROUTER_API_KEY=$(vault kv get -field=openrouter_key secret/mcp-orchestrator)
```

### 2. Container Security

```yaml
# docker-compose.mcp-enhanced.yml includes:
security_opt:
  - no-new-privileges:true
read_only: true
user: 1000:1000
```

## 🚨 Troubleshooting

### MCP Not Showing in Claude Code

1. **Check MCP registration**:
   ```bash
   claude mcp list
   ```

2. **Test Docker command**:
   ```bash
   docker run --rm -i mcp-orchestrator:enhanced --help
   ```

3. **Check logs**:
   ```bash
   docker logs mcp-orchestrator-enhanced
   ```

### API Key Issues

```bash
# Verify environment variables
docker run --rm --env-file .env mcp-orchestrator:enhanced env | grep API_KEY

# Test with inline env
docker run --rm -i -e OPENROUTER_API_KEY=test mcp-orchestrator:enhanced
```

### Permission Errors

```bash
# Fix ownership
sudo chown -R $(id -u):$(id -g) .

# Fix permissions
chmod 755 deploy_mcp.sh
chmod 600 .env
```

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Monitor resource usage
docker stats mcp-orchestrator-enhanced
```

### Logs

```bash
# View logs
docker logs -f mcp-orchestrator-enhanced

# Export logs
docker logs mcp-orchestrator-enhanced > mcp-logs-$(date +%Y%m%d).log
```

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild image
docker build -t mcp-orchestrator:enhanced .

# Restart service
docker-compose -f docker-compose.mcp-enhanced.yml restart
```

## 🌐 CI/CD Integration

### GitHub Actions

The repository includes `.github/workflows/docker-build.yml` for automated builds.

### GitLab CI

```yaml
# .gitlab-ci.yml
build:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

### Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'docker build -t mcp-orchestrator:${BUILD_NUMBER} .'
            }
        }
        stage('Deploy') {
            steps {
                sh './deploy_mcp.sh'
            }
        }
    }
}
```

## 📱 Mobile/Remote Access

### Using Claude Code Server

```bash
# Run Claude Code in server mode
claude code serve --port 8080

# Access from browser
# http://your-server:8080
```

### SSH Tunnel

```bash
# On remote server with MCP
ssh -L 8080:localhost:8080 user@server

# MCP tools available in local Claude Code
```

## 🎯 Best Practices

1. **Version Everything**: Tag Docker images with version numbers
2. **Test Before Deploy**: Run `test_enhanced_mcp.py` before deployment
3. **Monitor Costs**: Check orchestrator status regularly
4. **Update Regularly**: Pull latest enhancements and security fixes
5. **Document Changes**: Keep deployment logs and configuration history

## 🆘 Support

- **Issues**: Create GitHub issue with deployment logs
- **Discussions**: Use GitHub Discussions for questions
- **Security**: Report security issues privately

## 🎉 Success Checklist

- [ ] Docker installed and running
- [ ] API keys configured in .env
- [ ] MCP server added to Claude Code
- [ ] Test tool visible with `/` command
- [ ] First orchestration successful
- [ ] Costs monitored and acceptable

Happy Orchestrating! 🤖✨