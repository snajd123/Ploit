#!/bin/bash
#
# Poker Analysis Platform - Deployment Helper Script
#
# This script helps deploy the application to production.
# Choose your deployment platform and follow the prompts.
#

set -e

echo "========================================="
echo "Poker Analysis Platform - Deployment"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
echo "Checking prerequisites..."

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed. Please install git first."
    exit 1
fi
print_success "Git is installed"

# Check if we're in a git repository
if [ ! -d .git ]; then
    print_error "Not in a git repository. Please run this script from the project root."
    exit 1
fi
print_success "Git repository detected"

# Check if there are uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    print_warning "You have uncommitted changes. It's recommended to commit them first."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Choose your deployment platform:"
echo "1) Railway (Recommended for backend)"
echo "2) Render"
echo "3) Docker (Self-hosted)"
echo "4) Vercel (Frontend only)"
echo "5) Full stack (Backend + Frontend)"
echo ""
read -p "Enter choice [1-5]: " deployment_choice

case $deployment_choice in
    1)
        print_info "Deploying backend to Railway..."
        echo ""
        echo "Steps to deploy to Railway:"
        echo "1. Visit https://railway.app and sign in with GitHub"
        echo "2. Click 'New Project' → 'Deploy from GitHub repo'"
        echo "3. Select the 'Ploit' repository"
        echo "4. Railway will auto-detect the Dockerfile"
        echo "5. Add environment variables:"
        echo "   - DATABASE_URL (from Supabase)"
        echo "   - ANTHROPIC_API_KEY"
        echo "   - ALLOWED_ORIGINS (your frontend URL)"
        echo "   - ENVIRONMENT=production"
        echo "6. Click 'Deploy'"
        echo ""
        print_success "Configuration files ready: railway.json, backend/Dockerfile"
        ;;

    2)
        print_info "Deploying backend to Render..."
        echo ""
        echo "Steps to deploy to Render:"
        echo "1. Visit https://render.com and sign in with GitHub"
        echo "2. Click 'New +' → 'Web Service'"
        echo "3. Connect your Ploit repository"
        echo "4. Render will auto-detect render.yaml"
        echo "5. Add environment variables in dashboard:"
        echo "   - DATABASE_URL (from Supabase)"
        echo "   - ANTHROPIC_API_KEY"
        echo "6. Click 'Create Web Service'"
        echo ""
        print_success "Configuration files ready: render.yaml"
        ;;

    3)
        print_info "Building Docker image..."
        echo ""

        # Check if Docker is installed
        if ! command -v docker &> /dev/null; then
            print_error "Docker is not installed. Please install Docker first."
            exit 1
        fi

        print_info "Building backend Docker image..."
        docker build -t poker-analysis-backend -f backend/Dockerfile .
        print_success "Docker image built successfully"

        echo ""
        echo "To run the container:"
        echo "docker run -p 8000:8000 --env-file backend/.env poker-analysis-backend"
        echo ""
        print_warning "Don't forget to set up your .env file with production values!"
        ;;

    4)
        print_info "Deploying frontend to Vercel..."
        echo ""
        echo "Steps to deploy to Vercel:"
        echo "1. Visit https://vercel.com and sign in with GitHub"
        echo "2. Click 'Add New' → 'Project'"
        echo "3. Import your Ploit repository"
        echo "4. Set root directory to 'frontend'"
        echo "5. Framework Preset: Vite"
        echo "6. Add environment variable:"
        echo "   - VITE_API_URL (your backend URL)"
        echo "7. Click 'Deploy'"
        echo ""
        print_success "Configuration files ready: frontend/vercel.json"
        ;;

    5)
        print_info "Full stack deployment guide..."
        echo ""
        echo "=== STEP 1: Deploy Database (Supabase) ==="
        echo "1. Visit https://supabase.com/dashboard"
        echo "2. Create new project"
        echo "3. Go to SQL Editor"
        echo "4. Run backend/database_schema.sql"
        echo "5. Copy connection string from Settings → Database"
        echo ""

        echo "=== STEP 2: Deploy Backend (Railway) ==="
        echo "1. Visit https://railway.app"
        echo "2. New Project → Deploy from GitHub → Select Ploit"
        echo "3. Add environment variables:"
        echo "   - DATABASE_URL (from Supabase)"
        echo "   - ANTHROPIC_API_KEY"
        echo "   - ALLOWED_ORIGINS=https://your-frontend.vercel.app"
        echo "   - ENVIRONMENT=production"
        echo "4. Wait for deployment"
        echo "5. Copy the backend URL (e.g., https://xxx.railway.app)"
        echo ""

        echo "=== STEP 3: Deploy Frontend (Vercel) ==="
        echo "1. Visit https://vercel.com"
        echo "2. New Project → Import Ploit repository"
        echo "3. Root Directory: frontend"
        echo "4. Framework: Vite"
        echo "5. Add environment variable:"
        echo "   - VITE_API_URL=https://your-backend.railway.app"
        echo "6. Deploy"
        echo ""

        echo "=== STEP 4: Update CORS ==="
        echo "1. Go back to Railway"
        echo "2. Update ALLOWED_ORIGINS with your Vercel URL"
        echo "3. Redeploy if needed"
        echo ""

        echo "=== STEP 5: Test ==="
        echo "1. Visit your Vercel URL"
        echo "2. Check dashboard loads"
        echo "3. Upload a test hand history"
        echo "4. Query Claude AI"
        echo ""

        print_success "You're all set! Follow the steps above."
        ;;

    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo ""
print_info "For detailed deployment instructions, see docs/DEPLOYMENT_CHECKLIST.md"
print_success "Deployment configuration complete!"
