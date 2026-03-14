#!/usr/bin/env python3
"""
CHACAL PULSE V4.1 - Stats Monitor
==================================
Monitorea el rendimiento del bot y ajusta leverage automáticamente.

FUNCIONA ASI:
1. Consulta API de Freqtrade cada 30 min
2. Calcula WinRate actual
3. Compara contra benchmarks (Bear +44%, Bull +20%, Lateral +22%)
4. Si desviación > 10% negativa, reduce leverage
5. Envía alertas Telegram

 USO:
   python stats_monitor.py              # Monitoreo único
   python stats_monitor.py --daemon    # Modo daemon (30 min)
"""

import os
import sys
import json
import logging
import argparse
import time
from datetime import datetime
from typing import Dict, Optional, Tuple
import requests

# Configuración de logging
LOG_DIR = r"c:\ai_trading_agent\PROYECTO_CHACAL_PULSE\logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'stats_monitor.log')),
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
CONFIG_FILE = os.path.join(PROJECT_DIR, "config", "config.json")

# Benchmarks de WinRate (%)
WINRATE_BENCHMARKS = {
    'BULL': 20.0,
    'BEAR': 44.0,
    'LATERAL': 22.0
}

# Umbral de desviación negativa (%)
DEVIATION_THRESHOLD = 10.0

# Niveles de leverage
LEVERAGE_LEVELS = [5, 4, 3, 2, 1]  # De mayor a menor riesgo
DEFAULT_LEVERAGE = 5
MIN_LEVERAGE = 1

# =======================
# FUNCIONES
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


def get_current_strategy() -> str:
    """Obtiene estrategia actual"""
    try:
        url = f"{FREQTRADE_API_URL}/api/v1/strategy"
        auth = (FREQTRADE_API_KEY, FREQTRADE_API_PASSWORD)
        r = requests.get(url, auth=auth, timeout=10)
        if r.status_code == 200:
            return r.json().get('strategy', 'unknown')
    except Exception as e:
        logger.error(f"Error strategy: {e}")
    return 'unknown'


def get_profit_stats() -> Dict:
    """
    Obtiene estadísticas de profit del bot.
    """
    try:
        url = f"{FREQTRADE_API_URL}/api/v1/profit"
        auth = (FREQTRADE_API_KEY, FREQTRADE_API_PASSWORD)
        r = requests.get(url, auth=auth, timeout=10)
        
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error(f"Error profit: {e}")
    
    return {}


def get_trade_stats() -> Dict:
    """
    Obtiene estadísticas de trades.
    Calcula WinRate real.
    """
    try:
        url = f"{FREQTRADE_API_URL}/api/v1/trades"
        auth = (FREQTRADE_API_KEY, FREQTRADE_API_PASSWORD)
        params = {'limit': 100}  # Últimos 100 trades
        r = requests.get(url, auth=auth, params=params, timeout=10)
        
        if r.status_code == 200:
            trades = r.json()
            
            if not trades:
                return {'total': 0, 'wins': 0, 'losses': 0, 'winrate': 0}
            
            wins = sum(1 for t in trades if t.get('profit_abs', 0) > 0)
            total = len(trades)
            
            return {
                'total': total,
                'wins': wins,
                'losses': total - wins,
                'winrate': (wins / total * 100) if total > 0 else 0
            }
    except Exception as e:
        logger.error(f"Error trades: {e}")
    
    return {'total': 0, 'wins': 0, 'losses': 0, 'winrate': 0}


def get_current_leverage() -> int:
    """Obtiene leverage actual del config.json"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('leverage', DEFAULT_LEVERAGE)
    except Exception as e:
        logger.error(f"Error leyendo leverage: {e}")
    return DEFAULT_LEVERAGE


def calculate_benchmark(strategy: str) -> float:
    """Calcula benchmark según estrategia"""
    # Determinar régimen desde nombre de estrategia
    strategy_upper = strategy.upper()
    
    if 'BEAR' in strategy_upper:
        return WINRATE_BENCHMARKS['BEAR']
    elif 'BULL' in strategy_upper:
        return WINRATE_BENCHMARKS['BULL']
    else:
        return WINRATE_BENCHMARKS['LATERAL']


def adjust_leverage(new_leverage: int) -> bool:
    """
    Ajusta el leverage en config.json.
    """
    try:
        if not os.path.exists(CONFIG_FILE):
            logger.error("config.json no encontrado")
            return False
        
        # Leer config
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        old_leverage = config.get('leverage', DEFAULT_LEVERAGE)
        
        if new_leverage == old_leverage:
            logger.info(f"Leverage sin cambios: {old_leverage}x")
            return True
        
        # Actualizar leverage
        config['leverage'] = new_leverage
        
        # Escribir config
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"✅ Leverage cambiado: {old_leverage}x -> {new_leverage}x")
        
        # Notificación
        msg = f"""
📉 <b>LEVERAGE AJUSTADO</b>

🔧 Anterior: {old_leverage}x
🔧 Nuevo: <b>{new_leverage}x</b>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---
<i>Chacal Pulse V4.1</i>
"""
        send_telegram(msg)
        
        return True
        
    except Exception as e:
        logger.error(f"Error ajustando leverage: {e}")
        return False


def reduce_leverage_step() -> int:
    """
    Reduce el leverage un nivel.
    Retorna el nuevo nivel de leverage.
    """
    current = get_current_leverage()
    
    if current <= MIN_LEVERAGE:
        logger.info("⚠️ Leverage ya en mínimo (1x)")
        return current
    
    new_leverage = current - 1
    return new_leverage


def analyze_performance() -> Tuple[bool, str]:
    """
    Analiza el rendimiento y ajusta si es necesario.
    Retorna: (ajuste_realizado, mensaje)
    """
    logger.info("📊 Analizando rendimiento...")
    
    # 1. Obtener estrategia actual
    strategy = get_current_strategy()
    benchmark = calculate_benchmark(strategy)
    
    # 2. Obtener stats de trades
    stats = get_trade_stats()
    winrate = stats.get('winrate', 0)
    total_trades = stats.get('total', 0)
    
    if total_trades < 10:
        logger.info(f"⚠️ Solo {total_trades} trades, esperando más datos...")
        return False, f"Solo {total_trades} trades analizados"
    
    # 3. Calcular desviación
    deviation = benchmark - winrate
    deviation_pct = (deviation / benchmark) * 100
    
    logger.info(f"📈 WinRate: {winrate:.1f}% | Benchmark: {benchmark}% | Desviación: {deviation_pct:.1f}%")
    
    # 4. Verificar si necesita ajuste
    if deviation_pct > DEVIATION_THRESHOLD:
        # Desviación negativa excesiva, reducir leverage
        new_leverage = reduce_leverage_step()
        
        if adjust_leverage(new_leverage):
            msg = f"""
⚠️ <b>ALERTA RENDIMIENTO</b>

📊 WinRate: <b>{winrate:.1f}%</b>
🎯 Benchmark: {benchmark}%
📉 Desviación: {deviation_pct:.1f}% (>{DEVIATION_THRESHOLD}%)

🔧 Leverage reducido a: <b>{new_leverage}x</b>

🛡️ <i>Medida de protección activada</i>
---
<i>Chacal Pulse V4.1</i>
"""
            send_telegram(msg)
            return True, f"Leverage reducido a {new_leverage}x"
        else:
            return False, "Error ajustando leverage"
    else:
        logger.info(f"✅ Rendimiento OK (desviación: {deviation_pct:.1f}%)")
        return False, f"Rendimiento OK (WinRate: {winrate:.1f}%)"


def daemon_mode(interval_minutes: int = 30):
    """
    Modo daemon: ejecuta análisis cada X minutos.
    """
    logger.info(f"🚀 Modo daemon iniciado (cada {interval_minutes} min)")
    
    while True:
        try:
            analyze_performance()
        except Exception as e:
            logger.error(f"Error en análisis: {e}")
        
        logger.info(f"⏳ Esperando {interval_minutes} minutos...")
        time.sleep(interval_minutes * 60)


def main():
    parser = argparse.ArgumentParser(description='Chacal Pulse V4.1 Stats Monitor')
    parser.add_argument('--daemon', action='store_true', help='Modo daemon (30 min)')
    parser.add_argument('--interval', type=int, default=30, help='Intervalo en minutos (default: 30)')
    args = parser.parse_args()
    
    # Obtener profit stats inicial
    profit = get_profit_stats()
    logger.info(f"💰 Profit actual: {profit.get('profit_abs', 0):.2f} USDT")
    
    if args.daemon:
        daemon_mode(args.interval)
    else:
        # Modo único
        adjustment, message = analyze_performance()
        print(message)
        
        # Mostrar stats
        stats = get_trade_stats()
        print(f"\n📊 Estadísticas:")
        print(f"   Trades: {stats['total']}")
        print(f"   Wins: {stats['wins']}")
        print(f"   Losses: {stats['losses']}")
        print(f"   WinRate: {stats['winrate']:.1f}%")
        print(f"   Leverage actual: {get_current_leverage()}x")
        
        return 0 if not adjustment else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
