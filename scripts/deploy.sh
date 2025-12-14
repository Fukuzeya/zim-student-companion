# Save this as: /opt/zim-student-companion/scripts/deploy.sh

cat > /opt/zim-student-companion/scripts/deploy.sh << 'DEPLOY_SCRIPT'
#!/bin/bash
# Manual Deployment Script
# Usage: ./deploy.sh [image_tag]

set -e

cd /opt/zim-student-companion

IMAGE_TAG=${1:-latest}

echo "🚀 Deploying Zim Student Companion..."
echo "Image tag: $IMAGE_TAG"

# Pull latest images
echo "📥 Pulling images..."
docker-compose -f docker-compose.prod.yml pull

# Stop existing containers gracefully
echo "🛑 Stopping current containers..."
docker-compose -f docker-compose.prod.yml down --remove-orphans

# Start new containers
echo "🔄 Starting new containers..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 15

# Run migrations
echo "📊 Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head

# Health check
echo "🏥 Running health check..."
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✅ Deployment successful!"
else
    echo "❌ Health check failed!"
    docker-compose -f docker-compose.prod.yml logs --tail=50
    exit 1
fi

# Cleanup
echo "🧹 Cleaning up old images..."
docker image prune -af --filter "until=24h"

echo "🎉 Deployment complete!"
DEPLOY_SCRIPT

chmod +x /opt/zim-student-companion/scripts/deploy.sh

echo "✅ Deploy script created"