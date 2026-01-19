#!/bin/bash
#
# Rate Limiting Test Script
# Tests the 60 requests/minute limit
#

set -e

BASE_URL="http://localhost:8000"
ENDPOINT="/health"
REQUESTS=65

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         Rate Limiting Test - Quiz Platform                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Base URL: $BASE_URL"
echo "  Endpoint: $ENDPOINT"
echo "  Requests: $REQUESTS"
echo "  Expected: 60 succeed, 5 rate limited"
echo ""
echo "Starting test in 3 seconds..."
sleep 3
echo ""

SUCCESS=0
RATE_LIMITED=0
ERRORS=0
START_TIME=$(date +%s)

for i in $(seq 1 $REQUESTS); do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$ENDPOINT" 2>/dev/null)
    
    if [ "$RESPONSE" = "200" ]; then
        SUCCESS=$((SUCCESS + 1))
        echo " Request $i: $RESPONSE (OK)"
    elif [ "$RESPONSE" = "429" ]; then
        RATE_LIMITED=$((RATE_LIMITED + 1))
        
        if [ $RATE_LIMITED -eq 1 ]; then
            echo ""
            echo " Request $i: $RESPONSE (RATE LIMITED - First occurrence)"
            echo ""
            echo "   Fetching detailed response..."
            DETAIL=$(curl -s "$BASE_URL$ENDPOINT" 2>/dev/null | python3 -m json.tool 2>/dev/null || echo '{"error": "Could not parse JSON"}')
            echo "$DETAIL" | sed 's/^/   /'
            echo ""
        else
            echo " Request $i: $RESPONSE (RATE LIMITED)"
        fi
    else
        ERRORS=$((ERRORS + 1))
        echo " Request $i: $RESPONSE (Unexpected)"
    fi
    
    # Small delay to avoid overwhelming
    sleep 0.05
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    Test Results                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  Total Requests:    $REQUESTS"
echo "  Successful (200):  $SUCCESS"
echo "  Rate Limited (429): $RATE_LIMITED"
echo "  Errors:            $ERRORS"
echo "  Time Elapsed:      ${ELAPSED}s"
echo "  Requests/Second:   $(echo "scale=2; $REQUESTS / $ELAPSED" | bc)"
echo ""

# Determine test result
if [ $SUCCESS -eq 60 ] && [ $RATE_LIMITED -eq 5 ]; then
    echo "  PASS: Rate limiting working correctly!"
    echo ""
    echo "  Expected: 60 successful, 5 rate limited"
    echo "  Actual:   $SUCCESS successful, $RATE_LIMITED rate limited"
elif [ $RATE_LIMITED -gt 0 ]; then
    echo "  WARNING: Rate limiting active but counts unexpected"
    echo ""
    echo "  Expected: 60 successful, 5 rate limited"
    echo "  Actual:   $SUCCESS successful, $RATE_LIMITED rate limited"
else
    echo "  FAIL: No rate limiting detected!"
    echo ""
    echo "  All $SUCCESS requests succeeded - rate limiting may be disabled"
    echo "  Check: docker-compose logs api | grep 'rate'"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  Next Steps:                               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  1. Wait 60 seconds for rate limit to reset"
echo "  2. Run this script again to verify reset"
echo "  3. Check logs: docker-compose logs -f api | grep 'Rate limit'"
echo ""

# Offer to wait and test recovery
if [ $RATE_LIMITED -gt 0 ]; then
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           Test Rate Limit Recovery?                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    read -p "Wait 60 seconds and test recovery? [y/N]: " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo " Waiting for rate limit to reset..."
        echo ""
        
        for remaining in $(seq 60 -5 0); do
            echo "   $remaining seconds remaining..."
            sleep 5
        done
        
        echo ""
        echo " Testing recovery with single request..."
        RECOVERY=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$ENDPOINT")
        
        if [ "$RECOVERY" = "200" ]; then
            echo " PASS: Rate limit reset successfully!"
            echo "   Status: $RECOVERY OK"
        else
            echo " FAIL: Still rate limited after timeout"
            echo "   Status: $RECOVERY"
        fi
        echo ""
    fi
fi

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 Test Complete                              ║"
echo "╚════════════════════════════════════════════════════════════╝"