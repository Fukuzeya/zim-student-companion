cat > /opt/zim-student-companion/scripts/rollback.sh << 'ROLLBACK_SCRIPT'
#!/bin/bash
# Rollback Script
# Usage: ./rollback.sh [previous_image_tag]

set -e

cd /opt/zim-student-companion

if [ -z "$1" ]; then
    echo "Usage: ./rollback.sh <previous_image_tag>"
    echo "Available tags:"
    docker images --format "{{.Repository}}:{{.Tag}}" | grep zim-student-companion
    exit 1
fi

ROLLBACK_TAG=$1

echo "⏪ Rolling back to: $ROLLBACK_TAG"

# Update docker-compose to use specific tag
export IMAGE_TAG=$ROLLBACK_TAG

docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

echo "⏳ Waiting for services..."
sleep 10

if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✅ Rollback successful!"
else
    echo "❌ Rollback health check failed!"
    exit 1
fi
ROLLBACK_SCRIPT

chmod +x /opt/zim-student-companion/scripts/rollback.sh

echo "✅ Rollback script created"