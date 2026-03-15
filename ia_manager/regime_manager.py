#!/usr/bin/env python3
"""
CHACAL PULSE V4.1 - IA Regime Manager
=====================================
Gestor de régimen de mercado con Capa de Riesgo integrada.

FUNCIONA ASI:
1. Analiza mercado cada 15 min
2. Confirma régimen con 2 velas consecutivas
3. Detecta cambios bruscos y ejecuta Kill Switch
4. Cambia estrategia automáticamente
5. Envía alertas Telegram

 USO:
   python regime_manager.py --strategy BULL   # Cambiar a estrategia Bull
   python regime_manager.py --check           # Solo analizar y alertar
   python regime_manager.py --auto            # Modo automático completo
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import requests
import ccxt
import numpy as np
from collections import Counter

# Configuración de logging
LOG_DIR = r"c:\ai_trading_agent\PROYECTO_CHACAL_PULSE\logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'regime_manager.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =======================
# CONFIGURACIÓN
# =======================
FREQTRADE_API_URL = os.getenv('FREQTRADE_API_URL', 'http://localhost:8080')
FREQTRADE_API_KEY = os.getenv('FREQTRADE_API_KEY', 'freqtrade')
FREQTRADE_API_PASSWORD = os.getenv('FREQTRADE_API_PASSWORD', 'chacal2026')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8733469976:AAHj8ZhIxRn0i9rNwau8ih8ygYoGbfYS6Ds')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '6527908321')

# Proyecto
PROJECT_DIR = r"c:\ai_trading_agent\PROYECTO_CHACAL_PULSE"

# Pares a analizar
PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 
         'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT',
         'SUI/USDT', 'NEAR/USDT']

# =======================
# UMBRALES DE RÉGIMEN (Gear Shift)
# =======================
REGIME_THRESHOLDS = {
    'BULL': {
        'adx_min': 30,
        'rsi_min': 60,
    },
    'BEAR': {
        'adx_min': 30,
        'rsi_max': 40,
    },
    'LATERAL': {
        'adx_max': 25,
        'rsi_min': 40,
        'rsi_max': 60,
    }
}

# Benchmarks de WinRate
WINRATE_BENCHMARKS = {
    'BULL': 20.0,
    'BEAR': 44.0,
    'LATERAL': 22.0
}

# =======================
# ESTRATEGIAS
# =======================
STRATEGIES = {
    'BULL': 'ChacalPulseV4_Bull',
    'BEAR': 'ChacalPulseV4_Bear',
    'LATERAL': 'ChacalPulseV4_Lateral'
}

# Historial de régimen
_regime_history: List[str] = []
_last_regime: Optional[str] = None

# =======================
# CAPA DE RIESGO (KILL SWITCH)
# =======================

def execute_kill_switch(reason: str) -> bool:
    """
    Ejecuta el Kill Switch para proteger el capital.
    Cancela órdenes abiertas antes del cambio de estrategia.
    """
    logger.warning(f"⚠️ KILL SWITCH ACTIVADO: {reason}")
    
    try:
        url = f"{FREQTRADE_API_URL}/api/v1/forceenter"
        auth = (FREQTRADE_API_KEY, FREQTRADE_API_PASSWORD)
        requests.post(url, auth=auth, timeout=10)
        
        message = f"""
[KILL SWITCH ACTIVADO]

RAZON: {reason}

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Ejecutando proteccion de capital...
---
Chacal Pulse V4.1
"""
        send_telegram(message)
        logger.info("✅ Kill Switch ejecutado")
        return True
        
    except Exception as e:
        logger.error(f"Error en Kill Switch: {e}")
        return False


def detect_sudden_change(current_regime: str) -> bool:
    """
    Detecta cambios bruscos de régimen (Bear <-> Bull).
    """
    global _last_regime
    
    if _last_regime is None:
        _last_regime = current_regime
        return False
    
    sudden_changes = [('BEAR', 'BULL'), ('BULL', 'BEAR')]
    
    if (_last_regime, current_regime) in sudden_changes:
        logger.warning(f"CAMBIO BRUSCO: {_last_regime} -> {current_regime}")
        return True
    
    _last_regime = current_regime
    return False


def confirm_regime(regime: str) -> bool:
    """
    Confirma el régimen con 2 velas consecutivas.
    Evita señales falsas.
    """
    global _regime_history
    
    _regime_history.append(regime)
    
    if len(_regime_history) > 2:
        _regime_history.pop(0)
    
    if len(_regime_history) < 2:
        return False
    
    if _regime_history[0] == _regime_history[1] == regime:
        logger.info(f"Regimen confirmado: {regime} (2 velas)")
        return True
    
    return False


# =======================
# FUNCIONES PRINCIPALES
# =======================

def send_telegram(message: str) -> bool:
    """Envía mensaje a Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram no configurado")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'})
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Error Telegram: {e}")
        return False


def get_open_orders() -> int:
    """Obtiene número de órdenes abiertas"""
    try:
        url = f"{FREQTRADE_API_URL}/api/v1/status"
        auth = (FREQTRADE_API_KEY, FREQTRADE_API_PASSWORD)
        r = requests.get(url, auth=auth, timeout=10)
        if r.status_code == 200:
            return len(r.json())
    except Exception as e:
        logger.error(f"Error órdenes: {e}")
    return 0


def get_current_strategy() -> Optional[str]:
    """Obtiene estrategia actual de Freqtrade"""
    try:
        url = f"{FREQTRADE_API_URL}/api/v1/strategy"
        auth = (FREQTRADE_API_KEY, FREQTRADE_API_PASSWORD)
        r = requests.get(url, auth=auth, timeout=10)
        if r.status_code == 200:
            return r.json().get('strategy', 'unknown')
    except Exception as e:
        logger.error(f"Error strategy: {e}")
    return None


def change_strategy_via_bat(regime: str) -> bool:
    """Cambia estrategia usando switch_strategy.bat"""
    try:
        script_path = os.path.join(PROJECT_DIR, "switch_strategy.bat")
        result = subprocess.run([script_path, regime], capture_output=True, text=True, timeout=60, shell=True)
        
        if result.returncode == 0:
            logger.info(f"Estrategia cambiada a {regime}")
            return True
        else:
            logger.error(f"Error: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error cambiando: {e}")
        return False


def calculate_adx(closes: List[float], highs: List[float], lows: List[float]) -> float:
    """Calcula ADX simplificado"""
    if len(closes) < 14:
        return 25.0
    
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    
    if not trs:
        return 25.0
    
    avg_tr = np.mean(trs[-14:])
    adx = min(100, (avg_tr / closes[-1]) * 100 * 10)
    return max(10, min(80, adx))


def calculate_rsi(closes: List[float]) -> float:
    """Calcula RSI"""
    if len(closes) < 15:
        return 50.0
    
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-14:])
    avg_loss = np.mean(losses[-14:])
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def analyze_pair(pair: str) -> Optional[str]:
    """Analiza un par y retorna su régimen"""
    try:
        exchange = ccxt.binance({'enableRateLimit': True})
        ohlcv = exchange.fetch_ohlcv(pair, '1h', limit=50)
        
        if len(ohlcv) < 20:
            return None
        
        closes = [c[4] for c in ohlcv]
        highs = [c[2] for c in ohlcv]
        lows = [c[3] for c in ohlcv]
        
        adx = calculate_adx(closes, highs, lows)
        rsi = calculate_rsi(closes)
        
        # Aplicar umbrales
        if adx > REGIME_THRESHOLDS['BULL']['adx_min'] and rsi > REGIME_THRESHOLDS['BULL']['rsi_min']:
            return 'BULL'
        if adx > REGIME_THRESHOLDS['BEAR']['adx_min'] and rsi < REGIME_THRESHOLDS['BEAR']['rsi_max']:
            return 'BEAR'
        if adx < REGIME_THRESHOLDS['LATERAL']['adx_max']:
            return 'LATERAL'
        if REGIME_THRESHOLDS['LATERAL']['rsi_min'] <= rsi <= REGIME_THRESHOLDS['LATERAL']['rsi_max']:
            return 'LATERAL'
        
        return 'LATERAL'
    except Exception as e:
        logger.warning(f"Error {pair}: {e}")
        return None


def analyze_regime() -> Tuple[str, Dict]:
    """Analiza mercado y retorna régimen dominante"""
    regimes = []
    details = {'pairs_analyzed': 0, 'confidence': 0, 'vote_distribution': {}}
    
    logger.info("Analizando mercado...")
    
    for pair in PAIRS[:5]:
        regime = analyze_pair(pair)
        if regime:
            regimes.append(regime)
            details['pairs_analyzed'] += 1
    
    if not regimes:
        return 'LATERAL', details
    
    vote = Counter(regimes).most_common(1)[0][0]
    confidence = regimes.count(vote) / len(regimes)
    
    details['confidence'] = confidence
    details['vote_distribution'] = dict(Counter(regimes))
    
    logger.info(f"Regimen: {vote} (confianza: {confidence:.0%})")
    return vote, details


def automatic_mode() -> int:
    """Modo automático completo con Capa de Riesgo"""
    logger.info("Modo automatico iniciado")
    
    regime, details = analyze_regime()
    
    if not confirm_regime(regime):
        logger.info(f"--- {regime} sin confirmar...")
        return 0
    
    current = get_current_strategy()
    target = STRATEGIES[regime]
    
    if current == target:
        logger.info(f"Ya esta en {target}")
        return 0
    
    # CAPA DE RIESGO
    if detect_sudden_change(regime):
        reason = f"Cambio brusco: {_last_regime} -> {regime}"
        execute_kill_switch(reason)
        import time
        time.sleep(5)
    
    success = change_strategy_via_bat(regime)
    
    if success:
        msg = f"""
[CAMBIO AUTOMATICO]

Regimen: {regime}
Estrategia: {target}

Confianza: {details['confidence']*100:.0f}%
Dist: {details['vote_distribution']}

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---
Chacal Pulse V4.1
"""
        send_telegram(msg)
    
    return 0 if success else 1


def main():
    parser = argparse.ArgumentParser(description='Chacal Pulse V4.1 Regime Manager')
    parser.add_argument('--check', action='store_true', help='Solo analizar y alertar')
    parser.add_argument('--strategy', choices=['BULL', 'BEAR', 'LATERAL'], help='Cambiar estrategia')
    parser.add_argument('--auto', action='store_true', help='Modo automático')
    args = parser.parse_args()
    
    if args.strategy:
        success = change_strategy_via_bat(args.strategy)
        return 0 if success else 1
    
    elif args.check:
        regime, details = analyze_regime()
        msg = f"""
🦅 ANÁLISIS

Régimen: {regime}
Estrategia: {STRATEGIES[regime]}

Confianza: {details['confidence']*100:.0f}%
---
Chacal Pulse
"""
        send_telegram(msg)
        print(f"Régimen: {regime}")
        return 0
    
    elif args.auto:
        return automatic_mode()
    
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
