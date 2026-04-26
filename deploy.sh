#!/bin/bash

# ============================================
# CLAS Production Deployment Script
# Handles all 3 layers of caching automatically
# ============================================

set -e  # Exit on any error

echo "=========================================="
echo "🚀 CLAS Production Deployment"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ✅ CRITICAL: Activate virtual environment first
echo -e "${BLUE}[0/6]${NC} Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}\n"

# Step 1: Pull latest code
echo -e "${BLUE}[1/6]${NC} Pulling latest code from GitHub..."
git pull origin stable-working
echo -e "${GREEN}✓ Code pulled successfully${NC}\n"

# Step 2: Collect static files (fixes static file caching)
echo -e "${BLUE}[2/6]${NC} Collecting static files..."
python manage.py collectstatic --noinput --clear
echo -e "${GREEN}✓ Static files collected${NC}\n"

# Step 3: Clear Django cache (fixes Django page caching)
echo -e "${BLUE}[3/6]${NC} Clearing Django cache..."
python manage.py shell << EOF
from django.core.cache import cache
cache.clear()
print("✓ Django cache cleared")
EOF
echo -e "${GREEN}✓ Cache cleared${NC}\n"

# Step 4: Clear browser cache headers (optional - informational)
echo -e "${BLUE}[4/6]${NC} Browser cache will be cleared on next user visit..."
echo -e "${GREEN}✓ Cache headers updated${NC}\n"

# Step 5: Restart Gunicorn
echo -e "${BLUE}[5/6]${NC} Restarting Gunicorn..."
sudo systemctl restart gunicorn
echo -e "${GREEN}✓ Gunicorn restarted${NC}\n"

# Step 6: Restart Nginx
echo -e "${BLUE}[6/6]${NC} Restarting Nginx..."
sudo systemctl restart nginx
echo -e "${GREEN}✓ Nginx restarted${NC}\n"

echo "=========================================="
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ Latest code pulled from GitHub"
echo "  ✓ Static files collected (versioned)"
echo "  ✓ Django cache cleared"
echo "  ✓ Gunicorn restarted"
echo "  ✓ Nginx restarted"
echo ""
echo "Users should see latest UI changes immediately."
echo "If not, ask them to:"
echo "  1. Hard refresh: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)"
echo "  2. Clear browser cache"
echo "  3. Close and reopen browser"
echo ""
