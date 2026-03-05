#!/bin/bash
# Render.com Deployment Setup Script
# Prepares the project for deployment on Render

set -e

echo "=========================================="
echo "Resume Verification - Render Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

if ! command -v git &> /dev/null; then
    echo -e "${RED}✗ Git not found. Please install Git first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Git found${NC}"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ npm not found. Please install Node.js first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ npm found${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

echo ""
echo -e "${YELLOW}Step 2: Validating project structure...${NC}"

files=(
    "render.yaml"
    "backend/requirements.txt"
    "frontend/package.json"
    ".github/workflows"
)

for file in "${files[@]}"; do
    if [ -f "$file" ] || [ -d "$file" ]; then
        echo -e "${GREEN}✓ $file exists${NC}"
    else
        echo -e "${YELLOW}⚠ $file not found (optional)${NC}"
    fi
done

echo ""
echo -e "${YELLOW}Step 3: Checking environment configuration...${NC}"

if [ ! -f ".env.render.production" ]; then
    echo -e "${YELLOW}⚠ .env.render.production not found${NC}"
    echo "  A template is available at: .env.render.production"
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found (for local development)${NC}"
fi

echo ""
echo -e "${YELLOW}Step 4: Verifying backend dependencies...${NC}"

if grep -q "gunicorn" backend/requirements.txt; then
    echo -e "${GREEN}✓ gunicorn found in requirements.txt${NC}"
else
    echo -e "${YELLOW}⚠ gunicorn not in requirements.txt (needed for production)${NC}"
fi

echo ""
echo -e "${YELLOW}Step 5: Validating render.yaml...${NC}"

if grep -q "resume-verify-backend" render.yaml && \
   grep -q "resume-verify-frontend" render.yaml && \
   grep -q "resume-verify-db" render.yaml; then
    echo -e "${GREEN}✓ render.yaml has all required services${NC}"
else
    echo -e "${RED}✗ render.yaml is missing required services${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Validation Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Create a Render account: https://render.com"
echo "2. Push your code to GitHub:"
echo "   git add ."
echo "   git commit -m 'Prepare for Render deployment'"
echo "   git push origin main"
echo "3. Deploy using Blueprint:"
echo "   https://dashboard.render.com/blueprints"
echo "4. Set environment variables in Render dashboard"
echo "5. View logs and monitor at dashboard.render.com"
echo ""
echo "For detailed instructions, see: RENDER_DEPLOYMENT_GUIDE.md"
echo ""
