import requests
import json
import os
from datetime import datetime

def audit():
    print(f"--- AUDITORIA PEGASO - {datetime.now()} ---")
    
    # 1. API Status
    try:
        r = requests.get("http://localhost:8080/api/v1/ping", timeout=5)
        print(f"[OK] API Freqtrade respondiendo: {r.status_code}")
    except Exception as e:
        print(f"[ERROR] API Freqtrade NO RESPONDE: {e}")

    # 2. Extract active strategy from API
    try:
        r = requests.get("http://localhost:8080/api/v1/show_config", auth=('freqtrade', 'chacal2026'), timeout=5)
        config = r.json()
        active_strat = config.get('strategy', 'UNK')
        print(f"[INFO] Estrategia activa en memoria: {active_strat}")
    except:
        print("[WARN] No se pudo obtener la estrategia activa vía API.")

    # 3. Check for "locks" or "pairlist" issues
    try:
        r = requests.get("http://localhost:8080/api/v1/locks", auth=('freqtrade', 'chacal2026'), timeout=5)
        locks = r.json().get('locks', [])
        if locks:
            print(f"[WARN] Pares bloqueados temporalmente: {len(locks)}")
        else:
            print("[OK] No hay bloqueos (locks) de pares.")
    except:
        pass

    # 4. Check for whitelist vs balance
    try:
        r = requests.get("http://localhost:8080/api/v1/balance", auth=('freqtrade', 'chacal2026'), timeout=5)
        balance = r.json()
        free = balance.get('total', {}).get('USDT', 0)
        print(f"[INFO] Saldo libre (Dry Run): {free} USDT")
    except:
        pass

if __name__ == "__main__":
    audit()
