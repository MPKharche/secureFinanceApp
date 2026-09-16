# Deploy to money.planetfinance.cloud

## 🎉 Release v0.15.0 Created

**Release URL**: https://github.com/MPKharche/secureFinanceApp/releases/tag/v0.15.0

The release has been published to GitHub. The GitHub Actions workflow will automatically:
1. ✅ Build Docker images for backend, frontend, MCP server, celery workers
2. ✅ Push images to GitHub Container Registry (GHCR)
3. ✅ Package Helm chart and push to GHCR

## 📦 Deployment Options

### Option 1: Docker Compose (Recommended for Single Server)

If money.planetfinance.cloud runs on a single server with Docker:

```bash
# SSH into the production server
ssh user@your-production-server

# Navigate to the deployment directory
cd /path/to/secureFinanceApp

# Pull the latest code
git pull origin main

# Pull the new Docker images
docker compose -f docker-compose.prod.yml pull

# Restart services with new images
docker compose -f docker-compose.prod.yml up -d

# Run database migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Check services are running
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### Option 2: Kubernetes/Helm (For K8s Cluster)

If money.planetfinance.cloud runs on Kubernetes:

```bash
# Update to the new Helm chart version
helm upgrade securo oci://ghcr.io/mpkharche/charts/securo \
  --version 0.15.0 \
  --namespace securo \
  --values production-values.yaml

# Check rollout status
kubectl rollout status deployment/securo-backend -n securo
kubectl rollout status deployment/securo-frontend -n securo

# Run database migrations
kubectl exec -it deployment/securo-backend -n securo -- alembic upgrade head

# Check pods
kubectl get pods -n securo
```

### Option 3: Manual Docker Pull and Restart

If using systemd or other orchestration:

```bash
# Pull new images
docker pull ghcr.io/mpkharche/securo-backend:v0.15.0
docker pull ghcr.io/mpkharche/securo-frontend:v0.15.0

# Stop existing containers
docker stop securo-backend securo-frontend

# Start with new images
docker run -d --name securo-backend \
  --env-file .env.production \
  ghcr.io/mpkharche/securo-backend:v0.15.0

docker run -d --name securo-frontend \
  --env-file .env.production \
  ghcr.io/mpkharche/securo-frontend:v0.15.0

# Run migrations
docker exec securo-backend alembic upgrade head
```

## 🔍 Verify Deployment

After deployment, verify the new features:

1. **Check Version**
   ```bash
   curl https://money.planetfinance.cloud/api/version
   ```

2. **Test Budget Spreadsheet**
   - Navigate to https://money.planetfinance.cloud/budgets
   - Verify 12-month view loads
   - Test inline editing

3. **Check API Endpoints**
   ```bash
   curl https://money.planetfinance.cloud/api/budgets/multi-month?start_month=2026-01&end_month=2026-12
   ```

4. **Monitor Logs**
   ```bash
   # Docker Compose
   docker compose -f docker-compose.prod.yml logs -f backend frontend
   
   # Kubernetes
   kubectl logs -f deployment/securo-backend -n securo
   ```

## 🚨 Rollback Instructions

If issues occur:

### Docker Compose
```bash
# Revert to previous version
docker compose -f docker-compose.prod.yml down
git checkout v0.14.5
docker compose -f docker-compose.prod.yml up -d

# Rollback database if needed
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```

### Kubernetes
```bash
# Rollback Helm release
helm rollback securo -n securo

# Or specify previous version
helm upgrade securo oci://ghcr.io/mpkharche/charts/securo \
  --version 0.14.5 \
  --namespace securo
```

## 📊 Database Migration

The deployment includes migration **085_budget_spreadsheet_schema** which adds:
- `category_type` and `enable_rollover` columns to `categories`
- `linked_category_ids` column to `goals`
- New tables: `budget_templates`, `budget_scenarios`, `notifications`

**Migration is safe and backwards compatible** - existing data is preserved.

## 🔐 Important Notes

1. **Backup Database First**
   ```bash
   docker exec securo-db-1 pg_dump -U postgres securo > backup_$(date +%Y%m%d).sql
   ```

2. **Check GitHub Actions**
   - Visit: https://github.com/MPKharche/secureFinanceApp/actions
   - Verify "Build and Push Docker Images" workflow completed successfully
   - Images should be available at: https://github.com/MPKharche?tab=packages

3. **Environment Variables**
   - No new required environment variables for this release
   - All budget features work with existing configuration

## 📞 Need Help?

If you need specific deployment instructions for your server setup, please provide:
- How is money.planetfinance.cloud currently deployed? (Docker, K8s, etc.)
- Server access details
- Current deployment process

---

**Release Notes**: https://github.com/MPKharche/secureFinanceApp/releases/tag/v0.15.0
**Date**: September 16, 2026
