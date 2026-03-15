import pandas as pd
import numpy as np
import requests
import json
import ccxt
from datetime import datetime

# Configuración API local para parámetros
API_URL = "http://localhost:8080/api/v1"
AUTH = ('freqtrade', 'chacal2026')

def get_market_data():
    print(f"--- ANALISIS FORENSE PEGASO (CCXT DATA) - {datetime.now()} ---")
    
    # 1. Obtener parámetros de la estrategia activa vía API
    try:
        r = requests.get(f"{API_URL}/show_config", auth=AUTH, timeout=5)
        config = r.json()
        v_factor_mult = config.get('strategy_parameters', {}).get('v_factor_mult', 1.691)
        rsi_oversold = config.get('strategy_parameters', {}).get('rsi_oversold', 37)
        print(f"[PARAM] v_factor_mult: {v_factor_mult} | rsi_oversold: {rsi_oversold}")
    except Exception as e:
        print(f"[WARN] No se pudo obtener config de API: {e}. Usando defaults.")
        v_factor_mult = 1.691
        rsi_oversold = 37

    # 2. Descargar datos de Binance DIRECTO
    exchange = ccxt.binance()
    sample_pair = "DOT/USDT" 
    
    try:
        print(f"[INFO] Descargando velas de Binance para {sample_pair}...")
        ohlcv = exchange.fetch_ohlcv(sample_pair, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # Simular cálculo de la estrategia
        df['volume_mean'] = df['volume'].rolling(window=20).mean()
        df['threshold'] = df['volume_mean'] * v_factor_mult
        
        last_candle = df.iloc[-1]
        
        print(f"\n[DATA CRUDA] Analisis Forense:")
        print(f"- Ultimo Cierre: {last_candle['close']}")
        print(f"- Volumen Real: {last_candle['volume']:.2f}")
        print(f"- Umbral Gatillo (Mean20 * {v_factor_mult}): {last_candle['threshold']:.2f}")
        
        ratio = last_candle['volume'] / last_candle['threshold']
        print(f"- Ratio actual: {ratio:.4f}")
        
        if ratio < 1:
            print(f"- RESULTADO: El mercado esta operando a un {ratio:.1%} de la fuerza requerida.")
            print(f"- CONCLUSION: Se necesitan {last_candle['threshold'] - last_candle['volume']:.2f} unidades mas de volumen para disparar.")
        else:
            print("- RESULTADO: VOLUMEN ALCANZADO.")

        print(f"\n[FORENSE] Historial de Oportunidades (Ultimas 10 velas):")
        for i in range(-10, 0):
            c = df.iloc[i]
            r = c['volume'] / c['threshold']
            mark = "[!!!] DISPARO" if r > 1 else "[WAIT]"
            print(f"  T{i} | Vol: {c['volume']:.1f} | Req: {c['threshold']:.1f} | Ratio: {r:.2f} {mark}")

    except Exception as e:
        print(f"[ERROR] Fallo CCXT: {e}")

if __name__ == "__main__":
    get_market_data()
