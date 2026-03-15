"""
AUDITORÍA COMPLETA PEGASO 3.0
Analiza TODOS los pares, estrategias, balances y señales
"""
import requests
import json
import ccxt
import pandas as pd
from datetime import datetime

# Configuración
API_URL = "http://localhost:8080/api/v1"
AUTH = ('freqtrade', 'chacal2026')

# Lista completa de pares
PAIRS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "BNB/USDT:USDT",
    "XRP/USDT:USDT",
    "ADA/USDT:USDT",
    "DOGE/USDT:USDT",
    "AVAX/USDT:USDT",
    "LINK/USDT:USDT",
    "DOT/USDT:USDT",
    "SUI/USDT:USDT",
    "NEAR/USDT:USDT"
]

def get_api_status():
    """1. Estado de API"""
    print("\n" + "="*60)
    print("📡 1. ESTADO DE API FREQTRADE")
    print("="*60)
    try:
        r = requests.get(f"{API_URL}/ping", timeout=5)
        print(f"   ✅ API respondiendo: {r.json()}")
    except Exception as e:
        print(f"   ❌ API OFFLINE: {e}")
        return None
    
    try:
        # Get status
        r = requests.get(f"{API_URL}/status", auth=AUTH, timeout=5)
        status = r.json()
        print(f"   ✅ Bot estado: {status[0].get('state', 'N/A') if status else 'N/A'}")
        
        # Get config
        r = requests.get(f"{API_URL}/show_config", auth=AUTH, timeout=5)
        config = r.json()
        print(f"   📊 Estrategia activa: {config.get('strategy', 'N/A')}")
        print(f"   💰 Modo: {'DRY RUN' if config.get('dry_run') else 'LIVE'}")
        
        return config
    except Exception as e:
        print(f"   ❌ Error getting config: {e}")
        return None

def get_balance():
    """2. Balance y posiciones"""
    print("\n" + "="*60)
    print("💰 2. BALANCE Y POSICIONES")
    print("="*60)
    try:
        r = requests.get(f"{API_URL}/balance", auth=AUTH, timeout=5)
        balance = r.json()
        total = balance.get('total', {})
        print(f"   USDT Total: ${total.get('USDT', 0):.2f}")
        print(f"   USDT Libre: ${balance.get('free', {}).get('USDT', 0):.2f}")
        print(f"   Profit Total: ${balance.get('profit_all_percent', 0):.2f}%")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def get_open_trades():
    """3. Trades abiertos"""
    print("\n" + "="*60)
    print("📈 3. TRADES ABIERTOS")
    print("="*60)
    try:
        r = requests.get(f"{API_URL}/status", auth=AUTH, timeout=5)
        trades = r.json()
        if trades:
            print(f"   ✅ {len(trades)} trades abiertos:")
            for t in trades:
                print(f"      - {t.get('pair')} | Entry: {t.get('open_rate'):.4f} | Actual: {t.get('current_rate'):.4f} | P/L: {t.get('profit_abs', 0):.4f}")
        else:
            print("   ⚪ Sin trades abiertos")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def get_locks():
    """4. Locks/Bloqueos"""
    print("\n" + "="*60)
    print("🔒 4. LOCKS (BLOQUEOS DE PARES)")
    print("="*60)
    try:
        r = requests.get(f"{API_URL}/locks", auth=AUTH, timeout=5)
        locks = r.json().get('locks', [])
        if locks:
            print(f"   ⚠️ {len(locks)} pares bloqueados:")
            for l in locks:
                print(f"      - {l.get('pair')} | Hasta: {l.get('lock_end_time', 'N/A')}")
        else:
            print("   ✅ Sin bloqueos")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def analyze_all_pairs():
    """5. Análisis forense de TODOS los pares"""
    print("\n" + "="*60)
    print("🔍 5. ANÁLISIS FORENSE - TODOS LOS PARES")
    print("="*60)
    
    # Obtener parámetros de la estrategia
    try:
        r = requests.get(f"{API_URL}/show_config", auth=AUTH, timeout=5)
        config = r.json()
        v_factor_mult = config.get('strategy_parameters', {}).get('v_factor_mult', 1.691)
    except:
        v_factor_mult = 1.691
    
    print(f"   📊 v_factor_mult: {v_factor_mult}")
    
    exchange = ccxt.binance()
    
    oportunidades = []
    
    for pair in PAIRS:
        try:
            # Para CCXT, usar formato simple: BTC/USDT
            symbol = pair.split('/')[0] + '/' + pair.split('/')[1]
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=20)
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            # Calcular umbrales
            df['volume_mean'] = df['volume'].rolling(window=20).mean()
            df['threshold'] = df['volume_mean'] * v_factor_mult
            
            last_candle = df.iloc[-1]
            ratio = last_candle['volume'] / last_candle['threshold']
            
            # Buscar último disparo
            ultimo_disparo = None
            for i in range(-10, 0):
                c = df.iloc[i]
                r = c['volume'] / c['threshold']
                if r > 1:
                    ultimo_disparo = f"T{i} (ratio {r:.2f})"
                    break
            
            estado = "✅ DISPARO" if ratio > 1 else "⏳ WAIT"
            
            oportunidades.append({
                'pair': pair,
                'ratio': ratio,
                'estado': estado,
                'ultimo_disparo': ultimo_disparo,
                'volumen': last_candle['volume'],
                'threshold': last_candle['threshold']
            })
            
            print(f"   {pair[:12]:12} | Vol: {last_candle['volume']:>10.0f} | Req: {last_candle['threshold']:>10.0f} | Ratio: {ratio:.3f} | {estado}")
            
        except Exception as e:
            print(f"   {pair[:12]:12} | ❌ Error: {str(e)[:30]}")
    
    return oportunidades

def get_trade_history():
    """6. Historial de trades (últimos)"""
    print("\n" + "="*60)
    print("📜 6. HISTORIAL DE TRADES RECIENTES")
    print("="*60)
    try:
        r = requests.get(f"{API_URL}/trades", auth=AUTH, timeout=5)
        trades = r.json().get('trades', [])
        
        if trades:
            # Últimos 10
            ultimos = trades[-10:] if len(trades) > 10 else trades
            print(f"   📊 Total de trades: {len(trades)}")
            print(f"   Últimos {len(ultimos)} trades:")
            for t in ultimos:
                profit = t.get('profit_abs', 0)
                emoji = "🟢" if profit > 0 else "🔴"
                print(f"      {emoji} {t.get('pair')} | Entry: {t.get('open_rate'):.4f} | Exit: {t.get('close_rate'):.4f} | P/L: {profit:.4f}")
        else:
            print("   ⚪ Sin trades en historial")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    print("\n" + "🎯"*30)
    print(f"   AUDITORÍA COMPLETA PEGASO 3.0")
    print(f"   Fecha: {datetime.now()}")
    print("🎯"*30)
    
    # 1. API Status
    config = get_api_status()
    
    # 2. Balance
    get_balance()
    
    # 3. Trades abiertos
    get_open_trades()
    
    # 4. Locks
    get_locks()
    
    # 5. Análisis de todos los pares
    ops = analyze_all_pairs()
    
    # 6. Historial
    get_trade_history()
    
    # Resumen
    print("\n" + "="*60)
    print("📋 RESUMEN DE OPORTUNIDADES")
    print("="*60)
    disp_count = sum(1 for o in ops if o['ratio'] > 1)
    print(f"   Pares con DISPARO: {disp_count}/12")
    print(f"   Pares en ESPERA: {12-disp_count}/12")
    
    if disp_count > 0:
        print("\n   🎯 PARES CON SEÑAL:")
        for o in ops:
            if o['ratio'] > 1:
                print(f"      - {o['pair']} (ratio: {o['ratio']:.2f})")

if __name__ == "__main__":
    main()
