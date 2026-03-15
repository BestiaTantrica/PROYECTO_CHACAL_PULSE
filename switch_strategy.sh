#!/bin/bash
# Script para cambiar estrategia en Freqtrade

STRATEGY=$1
API_URL="http://localhost:8080"
API_USER="freqtrade"
API_PASS="chacal2026"

if [ -z "$STRATEGY" ]; then
    echo "Uso: ./switch_strategy.sh [BULL|BEAR|LATERAL]"
    exit 1
fi

case $STRATEGY in
    BULL)
        STRAT_NAME="ChacalPulseV4_Bull"
        ;;
    BEAR)
        STRAT_NAME="ChacalPulseV4_Bear"
        ;;
    LATERAL)
        STRAT_NAME="ChacalPulseV4_Lateral"
        ;;
    *)
        echo "Estrategia desconocida: $STRATEGY"
        exit 1
        ;;
esac

echo "Cambiando a estrategia: $STRAT_NAME"

# Cambiar via API de Freqtrade
curl -s -X POST "$API_URL/api/v1/strategy" \
    -H "Content-Type: application/json" \
    -u "$API_USER:$API_PASS" \
    -d "{\"strategy\": \"$STRAT_NAME\"}"

echo "Estrategia cambiada a $STRAT_NAME"
