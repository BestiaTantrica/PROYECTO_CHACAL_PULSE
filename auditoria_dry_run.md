# Auditoría Total - Dry Run (15 de Marzo de 2026)

## 📌 1. Estado General de la Estrategia (Lateral)
- **Modo:** DRY RUN
- **Estrategia Activa:** `ChacalPulseV4_Lateral`
- **Rentabilidad de trades cerrados recientementes:** Excelente.
- **Historial de 7 trades recientes:** TODOS GANADORES (🟢).
  - DOT/USDT (+1.17 USDT)
  - BNB/USDT (+0.86 USDT)
  - XRP/USDT (+1.50 USDT)
  - DOGE/USDT (+1.13 USDT)
  - SUI/USDT (+2.53 USDT)
  - DOT/USDT (+0.10 USDT)
  - SUI/USDT (+1.50 USDT)

## 📈 2. Estado de Posiciones Abiertas
Actualmente el bot tiene **8 posiciones abiertas**. El P/L flotante es estable y manejable (entre -2.9 a +0.3 USDT).
- **Lista de activos (con P/L):** 
  - BTC/USDT: +0.32
  - SOL/USDT: +0.35
  - ADA/USDT: -0.63
  - DOGE/USDT: -0.48
  - BNB/USDT: -0.65
  - NEAR/USDT: -0.13
  - LINK/USDT: -0.96
  - ETH/USDT: -2.94
- **Transición por apagado de PC:** Las posiciones abiertas han quedado resguardadas en la base de datos local SQLite de Freqtrade. Al reiniciar la PC y levantar el contenedor nuevamente, el bot retomará la gestión continua de estos trades sin romper su métrica.

## 🔍 3. Análisis Forense de Mercado (Ejemplo de métricas: DOT/USDT)
- **Parámetros detectados:** `v_factor_mult: 1.691` | `rsi_oversold: 37`
- **Estado actual del mercado:** El mercado está en una etapa transaccional lenta. Volumen actual de velas de 5m operando a un ~1.4% de la fuerza requerida para generar nuevos disparos (Wait state). 
- **Conclusión:** El filtro de volumen está detectando correctamente la falta de impulso del mercado. El bot se mantiene pacientemente inactivo protegiendo el capital.

## 🛠 4. Acciones de Apagado Seguro Realizadas
- Se ejecutó `docker compose down` para apagar de manera **_graceful_ (segura)** el stack de freqtrade.
- Esto detiene la ingesta de datos de Binance y guarda el estado actual sin corromper la DB local. Al volver se pueden retomar los trades en curso.

## 💡 5. Observaciones sobre Fin de Semana y Régimen del mercado
Actualmente, la restricción horaria (3 a 21) o restricción de Fin de Semana no está activa (o codificada directamente) limitando operaciones dentro del script, y dada su alta rentabilidad adaptativa mediante confirmadores de volúmen es factible dejar esta estrategia **24/7**, ya que ella sola filtra el letargo del mercado en fin de semana de forma dinámica con su `v_factor`. 

Para testear cambios de régimen de mercado sin romper este dry-run, podemos utilizar `freqtrade backtesting` usando rangos de días con condiciones de mercado específicas (ej. un bull run), o desplegar un segundo contenedor con un sub-balance.

## 🚀 6. Plan de Acción hacia el Server LIVE
Para la escalabilidad a Live en el Cloud:
1. **Configuración de seguridad:** Activación de Whitelists de IPs en la API KEY de Binance. Verificación estricta de variables de control de stoploss (`stoploss` predefinido como cinturón de seguridad). 
2. **Transferencia de Estado y Scripts:** Git clone del repositorio `c:\ai_trading_agent\` en el VPS o Server Destino. (Se recomienda Debian/Ubuntu Server).
3. **Puesta a punto y Configuración de capital:** Modificar una copia de `config.json` para que pase a **Live** (`dry_run: false`), con una porción fraccionada de la cartera inicial.
4. **Despliegue silencioso:** Ejecutar en el server `docker compose -f docker-compose.yml up -d` y realizar un monitoreo de API por telegram.
