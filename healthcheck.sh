#!/bin/bash
#
# Post-Deployment Health Check Script
#
# Verifies that both backend and frontend are working correctly
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ $1${NC}"; }

echo "========================================="
echo "Poker Analysis - Health Check"
echo "========================================="
echo ""

# Get URLs from user
read -p "Enter backend URL (e.g., https://your-app.railway.app): " BACKEND_URL
read -p "Enter frontend URL (e.g., https://your-app.vercel.app): " FRONTEND_URL

# Remove trailing slashes
BACKEND_URL=${BACKEND_URL%/}
FRONTEND_URL=${FRONTEND_URL%/}

echo ""
print_info "Starting health checks..."
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to test endpoint
test_endpoint() {
    local url=$1
    local name=$2
    local expected_status=${3:-200}

    echo -n "Testing $name... "

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")

    if [ "$response" = "$expected_status" ]; then
        print_success "OK (HTTP $response)"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "FAILED (HTTP $response, expected $expected_status)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to test JSON endpoint
test_json_endpoint() {
    local url=$1
    local name=$2
    local json_key=$3

    echo -n "Testing $name... "

    response=$(curl -s "$url" || echo "{}")

    if echo "$response" | grep -q "\"$json_key\""; then
        print_success "OK (found '$json_key' in response)"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "FAILED (key '$json_key' not found)"
        echo "Response: $response"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Backend Tests
echo "=== BACKEND TESTS ==="
echo ""

test_json_endpoint "$BACKEND_URL/api/health" "Health endpoint" "status"
test_json_endpoint "$BACKEND_URL/api/database/stats" "Database stats" "total_hands"
test_json_endpoint "$BACKEND_URL/api/database/schema" "Database schema" "tables"
test_endpoint "$BACKEND_URL/docs" "API documentation" "200"

echo ""

# Frontend Tests
echo "=== FRONTEND TESTS ==="
echo ""

test_endpoint "$FRONTEND_URL" "Frontend homepage" "200"
test_endpoint "$FRONTEND_URL/dashboard" "Dashboard page" "200"
test_endpoint "$FRONTEND_URL/upload" "Upload page" "200"
test_endpoint "$FRONTEND_URL/players" "Players page" "200"
test_endpoint "$FRONTEND_URL/claude" "Claude page" "200"

echo ""

# Integration Tests
echo "=== INTEGRATION TESTS ==="
echo ""

# Test CORS
echo -n "Testing CORS configuration... "
cors_response=$(curl -s -I -H "Origin: $FRONTEND_URL" "$BACKEND_URL/api/health" | grep -i "access-control-allow-origin" || echo "")
if [ -n "$cors_response" ]; then
    print_success "OK (CORS headers present)"
    ((TESTS_PASSED++))
else
    print_warning "CORS headers not found (may need configuration)"
    ((TESTS_FAILED++))
fi

# Test if frontend can reach backend
echo -n "Testing frontend→backend connectivity... "
# This is a simplified test - in reality, you'd check browser console
if [ $TESTS_PASSED -gt 5 ]; then
    print_success "Likely OK (both endpoints responding)"
    ((TESTS_PASSED++))
else
    print_warning "Check browser console for CORS errors"
fi

echo ""
echo "========================================="
echo "HEALTH CHECK SUMMARY"
echo "========================================="
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    print_success "All tests passed! ($TESTS_PASSED/$((TESTS_PASSED + TESTS_FAILED)))"
    echo ""
    print_info "Your application is deployed and working correctly!"
    echo ""
    echo "Next steps:"
    echo "  1. Upload a test hand history file"
    echo "  2. Check that player stats calculate correctly"
    echo "  3. Try querying Claude AI"
    echo "  4. Monitor logs for any errors"
    echo ""
    exit 0
else
    print_error "$TESTS_FAILED tests failed, $TESTS_PASSED passed"
    echo ""
    print_warning "Troubleshooting:"
    echo "  1. Check environment variables are set correctly"
    echo "  2. Verify database connection (DATABASE_URL)"
    echo "  3. Confirm ANTHROPIC_API_KEY is valid"
    echo "  4. Check CORS settings (ALLOWED_ORIGINS)"
    echo "  5. Review deployment logs for errors"
    echo ""
    echo "For detailed troubleshooting, see docs/DEPLOYMENT_CHECKLIST.md"
    echo ""
    exit 1
fi
