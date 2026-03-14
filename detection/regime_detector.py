#!/usr/bin/env python3
"""
CHACAL PULSE - Regime Detector
================================
Detecta el régimen de mercado (Bull/Bear/Lateral) y envía alertas Telegram.

Ejecución: cada 15 minutos via crontab
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import requests

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =======================
# CONFIGURACIÓN
# =======================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Pares a analizar
PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 
         'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT',
         'SUI/USDT', 'NEAR/USDT']

# =======================
# PARÁMETROS DE RÉGIMEN
# =======================
REGIME_PARAMS = {
    'BULL': {
        'adx_min': 30,
        'rsi_min': 55,
        'price_slope_positive': True,
    },
    'BEAR': {
        'adx_min': 30,
        'rsi_max': 45,
        'price_slope_positive': False,
    },
    'LATERAL': {
        'adx_max': 25,
        'rsi_range': (35, 65),
    }
}

# =======================
# FUNCIONES
# =======================
def send_telegram_message(message: str) -> bool:
    """Envía mensaje a Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured, skipping alert")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False


def classify_regime(adx: float, rsi: float, price_change_1h: float) -> str:
    """
    Clasifica el régimen de mercado basado en indicadores.
    
    Returns: 'BULL', 'BEAR', o 'LATERAL'
    """
    # Bull: ADX > 30 Y RSI > 55 Y precio subiendo
    if adx > 30 and rsi > 55 and price_change_1h > 0:
        return 'BULL'
    
    # Bear: ADX > 30 Y RSI < 45 Y precio bajando
    if adx > 30 and rsi < 45 and price_change_1h < 0:
        return 'BEAR'
    
    # Lateral: cualquier otro caso
    return 'LATERAL'


def calculate_market_sentiment(regimes: list) -> Dict[str, int]:
    """Cuenta regímenes detectados"""
    sentiment = {'BULL': 0, 'BEAR': 0, 'LATERAL': 0}
    for r in regimes:
        if r in sentiment:
            sentiment[r] += 1
    return sentiment


def determine_dominant_regime(sentiment: Dict[str, int]) -> str:
    """Determina el régimen dominante"""
    # Si más del 60% coinciden, usar ese
    total = sum(sentiment.values())
    for regime, count in sentiment.items():
        if count / total >= 0.6:
            return regime
    # Si no hay consenso claro, default a LATERAL (más seguro)
    return 'LATERAL'


def get_recommended_strategy(regime: str) -> str:
    """Recomienda estrategia según régimen"""
    strategies = {
        'BULL': 'ChacalPulse_Bull (Long only)',
        'BEAR': 'ChacalPulse_Bear (Long + Short)',
        'LATERAL': 'ChacalPulse_Lateral (Rebote RSI)'
    }
    return strategies.get(regime, 'ChacalPulseV4_Hyperopt')


def analyze_market() -> Dict:
    """
    Analiza el mercado y retorna el régimen actual.
    En un caso real, estofetchearía datos de Binance.
    """
    # Simulación - en producción, usar CCXT para obtener datos reales
    # import ccxt
    # exchange = ccxt.binance()
    # for pair in PAIRS:
    #     ohlcv = exchange.fetch_ohlcv(pair, '1h', limit=50)
    
    # Por ahora, retornamos un análisis simulado
    # Esto debe ser reemplazado con datos reales
    
    logger.info("Análisis de mercado completado (simulado)")
    return {
        'timestamp': datetime.now().isoformat(),
        'regime': 'LATERAL',  # Default
        'confidence': 0.7,
        'sentiment': {'BULL': 4, 'BEAR': 2, 'LATERAL': 6},
        'pairs_analyzed': len(PAIRS)
    }


def main():
    """Main execution"""
    logger.info("🚀 Iniciando detector de régimen...")
    
    # Analizar mercado
    analysis = analyze_market()
    
    regime = analysis['regime']
    confidence = analysis['confidence']
    sentiment = analysis['sentiment']
    
    # Determinar estrategia recomendada
    strategy = get_recommended_strategy(regime)
    
    # Construir mensaje
    message = f"""
🦅 <b>CHACAL PULSE - ANÁLISIS DE MERCADO</b>

⏰ {analysis['timestamp']}

📊 <b>RÉGIMEN DETECTADO:</b> {regime}
🎯 <b>CONFIANZA:</b> {confidence*100:.0f}%

📈 <b>SENTIMIENTO MERCADO:</b>
   🟢 BULL: {sentiment['BULL']}
   🔴 BEAR: {sentiment['BEAR']}
   🟡 LATERAL: {sentiment['LATERAL']}

💡 <b>ESTRATEGIA RECOMENDADA:</b>
   {strategy}

---
<i>Chacal Pulse Trading System</i>
"""
    
    # Enviar a Telegram
    send_telegram_message(message)
    
    logger.info(f"✅ Análisis completado: {regime}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
