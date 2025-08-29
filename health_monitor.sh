#!/bin/bash
# Health Check Monitor Script
# Usage: ./health_monitor.sh [endpoint] [interval_seconds]

ENDPOINT=${1:-"http://localhost:8094/api/health"}
INTERVAL=${2:-30}

echo "🔍 Health Check Monitor"
echo "📍 Endpoint: $ENDPOINT"
echo "⏱️  Interval: $INTERVAL seconds"
echo "Press Ctrl+C to stop"
echo "----------------------------------------"

while true; do
    RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "$ENDPOINT")
    HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
    JSON_RESPONSE=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    if [ "$HTTP_STATUS" = "200" ]; then
        read STATUS RESPONSE_TIME < <(echo "$JSON_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('status', 'unknown'), d.get('response_time_ms', 'N/A'))" 2>/dev/null || echo "unknown N/A")
        STATUS=${STATUS:-unknown}
        RESPONSE_TIME=${RESPONSE_TIME:-N/A}

        case $STATUS in
            "healthy")
                echo "✅ $TIMESTAMP - Status: $STATUS (Response: ${RESPONSE_TIME}ms)"
                ;;
            "degraded")
                echo "⚠️  $TIMESTAMP - Status: $STATUS (Response: ${RESPONSE_TIME}ms)"
                ;;
            "critical")
                echo "❌ $TIMESTAMP - Status: $STATUS (Response: ${RESPONSE_TIME}ms)"
                ;;
            *)
                echo "❓ $TIMESTAMP - Status: $STATUS (Response: ${RESPONSE_TIME}ms)"
                ;;
        esac
    else
        echo "❌ $TIMESTAMP - HTTP Error: $HTTP_STATUS"
    fi

    sleep "$INTERVAL"
done
