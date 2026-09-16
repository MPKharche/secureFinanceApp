#!/bin/bash
# Deploy to production script for money.planetfinance.cloud

set -e

echo "🚀 Deploying Securo v0.15.0 to Production"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.prod.yml not found${NC}"
    echo "Please run this script from the secureFinanceApp root directory"
    exit 1
fi

echo -e "${YELLOW}📋 Pre-deployment Checklist${NC}"
echo "1. Backup database? (Recommended)"
echo "2. All services will be restarted"
echo ""
read -p "Continue with deployment? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo -e "${GREEN}✓${NC} Starting deployment..."

# Step 1: Pull latest code
echo -e "\n${YELLOW}Step 1/6:${NC} Pulling latest code from GitHub..."
git fetch origin
git checkout main
git pull origin main

# Step 2: Pull Docker images
echo -e "\n${YELLOW}Step 2/6:${NC} Pulling Docker images..."
docker compose -f docker-compose.prod.yml pull

# Step 3: Stop services
echo -e "\n${YELLOW}Step 3/6:${NC} Stopping services..."
docker compose -f docker-compose.prod.yml down

# Step 4: Start services
echo -e "\n${YELLOW}Step 4/6:${NC} Starting services with new images..."
docker compose -f docker-compose.prod.yml up -d

# Step 5: Wait for services to be ready
echo -e "\n${YELLOW}Step 5/6:${NC} Waiting for services to be ready..."
sleep 10

# Step 6: Run migrations
echo -e "\n${YELLOW}Step 6/6:${NC} Running database migrations..."
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# Check status
echo -e "\n${YELLOW}Checking service status...${NC}"
docker compose -f docker-compose.prod.yml ps

echo ""
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo ""
echo "🌐 Website: https://money.planetfinance.cloud"
echo "📊 Budget Spreadsheet: https://money.planetfinance.cloud/budgets"
echo ""
echo "📝 To view logs:"
echo "   docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🔄 To rollback if needed:"
echo "   git checkout v0.14.5"
echo "   docker compose -f docker-compose.prod.yml up -d --force-recreate"
echo ""
