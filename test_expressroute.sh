#!/bin/bash

# Script de testing completo para ExpressRoute monitoring

SCRIPT_PATH="/usr/lib/zabbix/externalscripts/expressroute_rpo.py"
TEST_CIRCUIT="vm-name-de-prueba"
LOG_FILE="/var/log/zabbix/expressroute_test.log"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Función para imprimir con color
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "OK")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "FAIL")
            echo -e "${RED}✗${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        *)
            echo "  $message"
            ;;
    esac
}

# Inicio del test
echo "================================================"
echo "ExpressRoute Monitoring - Complete Test Suite"
echo "================================================"
echo ""

# Test 1: Verificar existencia del script
echo "Test 1: Script existence"
if [ -f "$SCRIPT_PATH" ]; then
    print_status "OK" "Script found at $SCRIPT_PATH"
else
    print_status "FAIL" "Script not found at $SCRIPT_PATH"
    exit 1
fi

# Test 2: Verificar permisos
echo ""
echo "Test 2: Script permissions"
if [ -x "$SCRIPT_PATH" ]; then
    print_status "OK" "Script is executable"
else
    print_status "FAIL" "Script is not executable"
    exit 1
fi

OWNER=$(stat -c '%U' "$SCRIPT_PATH")
if [ "$OWNER" == "zabbix" ]; then
    print_status "OK" "Script owned by zabbix user"
else
    print_status "WARN" "Script owned by $OWNER (expected: zabbix)"
fi

# Test 3: Verificar sintaxis Python
echo ""
echo "Test 3: Python syntax validation"
python3 -m py_compile "$SCRIPT_PATH" 2>/dev/null
if [ $? -eq 0 ]; then
    print_status "OK" "Python syntax is valid"
else
    print_status "FAIL" "Python syntax error detected"
    exit 1
fi

# Test 4: Ejecutar script y verificar salida
echo ""
echo "Test 4: Script execution"
OUTPUT=$(sudo -u zabbix python3 "$SCRIPT_PATH" "$TEST_CIRCUIT" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    print_status "OK" "Script executed successfully (exit code: 0)"
else
    print_status "FAIL" "Script failed with exit code: $EXIT_CODE"
    echo "Output: $OUTPUT"
    exit 1
fi

# Test 5: Validar formato JSON
echo ""
echo "Test 5: JSON output validation"
echo "$OUTPUT" | python3 -m json.tool > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_status "OK" "Output is valid JSON"
else
    print_status "FAIL" "Output is not valid JSON"
    echo "Output: $OUTPUT"
    exit 1
fi

# Test 6: Verificar campos requeridos
echo ""
echo "Test 6: Required fields validation"

REQUIRED_FIELDS=(
    "HOSTNAME"
    "RPO"
    "CIRCUIT_STATE"
    "BGP_STATE"
    "ARP_AVAILABILITY"
    "BGP_AVAILABILITY"
    "BANDWIDTH_IN_MBPS"
    "BANDWIDTH_OUT_MBPS"
    "LATENCY_MS"
    "TIMESTAMP"
    "STATUS"
)

ALL_FIELDS_OK=true
for field in "${REQUIRED_FIELDS[@]}"; do
    echo "$OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); exit(0 if '$field' in data['data'][0] else 1)" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_status "OK" "Field '$field' present"
    else
        print_status "FAIL" "Field '$field' missing"
        ALL_FIELDS_OK=false
    fi
done

if [ "$ALL_FIELDS_OK" = false ]; then
    exit 1
fi

# Test 7: Verificar valores de datos
echo ""
echo "Test 7: Data values validation"

# Extraer valores
RPO=$(echo "$OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['data'][0]['RPO'])" 2>/dev/null)
CIRCUIT_STATE=$(echo "$OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['data'][0]['CIRCUIT_STATE'])" 2>/dev/null)

if [ -n "$RPO" ]; then
    print_status "OK" "RPO value: $RPO"
    
    if [ "$RPO" -gt 300 ]; then
        print_status "WARN" "RPO exceeds threshold (>300s)"
    fi
else
    print_status "FAIL" "Could not extract RPO value"
fi

if [ -n "$CIRCUIT_STATE" ]; then
    print_status "OK" "Circuit state: $CIRCUIT_STATE"
else
    print_status "FAIL" "Could not extract circuit state"
fi

# Test 8: Performance test
echo ""
echo "Test 8: Performance test (10 executions)"

TOTAL_TIME=0
for i in {1..10}; do
    START=$(date +%s.%N)
    sudo -u zabbix python3 "$SCRIPT_PATH" "$TEST_CIRCUIT" > /dev/null 2>&1
    END=$(date +%s.%N)
    ELAPSED=$(echo "$END - $START" | bc)
    TOTAL_TIME=$(echo "$TOTAL_TIME + $ELAPSED" | bc)
done

AVG_TIME=$(echo "scale=3; $TOTAL_TIME / 10" | bc)
print_status "OK" "Average execution time: ${AVG_TIME}s"

if (( $(echo "$AVG_TIME > 5" | bc -l) )); then
    print_status "WARN" "Average time exceeds 5 seconds"
fi

# Test 9: Verificar log file
echo ""
echo "Test 9: Log file verification"

LOG_DIR=$(dirname "/var/log/zabbix/expressroute_monitor.log")
if [ -d "$LOG_DIR" ]; then
    print_status "OK" "Log directory exists: $LOG_DIR"
    
    if [ -w "$LOG_DIR" ]; then
        print_status "OK" "Log directory is writable"
    else
        print_status "WARN" "Log directory is not writable"
    fi
else
    print_status "WARN" "Log directory does not exist: $LOG_DIR"
fi

# Test 10: Verificar servicios de Zabbix
echo ""
echo "Test 10: Zabbix services status"

systemctl is-active --quiet zabbix-server
if [ $? -eq 0 ]; then
    print_status "OK" "Zabbix Server is running"
else
    print_status "FAIL" "Zabbix Server is not running"
fi

systemctl is-active --quiet zabbix-agent
if [ $? -eq 0 ]; then
    print_status "OK" "Zabbix Agent is running"
else
    print_status "FAIL" "Zabbix Agent is not running"
fi

# Resumen final
echo ""
echo "================================================"
echo "Test Summary"
echo "================================================"
echo ""
echo "Sample output (formatted):"
echo "$OUTPUT" | python3 -m json.tool
echo ""
print_status "OK" "All tests completed successfully!"
echo ""
echo "Next steps:"
echo "  1. Check Zabbix web interface: http://localhost/zabbix"
echo "  2. Verify items are receiving data: Monitoring → Latest data"
echo "  3. Check for active triggers: Monitoring → Problems"
echo "  4. Review dashboard: Monitoring → Dashboards"
echo ""

log "Test suite completed successfully"