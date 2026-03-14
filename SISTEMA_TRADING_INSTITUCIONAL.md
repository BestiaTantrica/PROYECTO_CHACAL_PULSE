# 🏦 SISTEMA DE TRADING ALGORÍTMICO INSTITUCIONAL

## Chacal Pulse - Master Architecture Document

---

## 1. FILOSOFÍA DEL SISTEMA

### 1.1 Visión

Sistema de trading algorítmico multi-estrategia con detección automática de régimen de mercado y gestión de riesgo institucional.

### 1.2 Core Principle

**"No fighting the market - adapt to it"**

- Identificar el régimen actual (Bull/Bear/Lateral)
- Aplicar la estrategia óptima para ese régimen
- Maximizar win rate mientras minimizamos drawdown

---

## 2. ARQUITECTURA GENERAL

```
┌─────────────────────────────────────────────────────────────────┐
│                    SISTEMA DE TRADING                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   MERCADO    │───▶│  DETECCIÓN   │───▶│   GESTOR     │   │
│  │   (Data)     │    │   RÉGIMEN    │    │   ESTRATEGIA │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │              │
│         ▼                   ▼                   ▼              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              GESTOR DE RIESGO INSTITUCIONAL            │  │
│  │  • Max Drawdown 5% por estrategia                     │  │
│  │  • Max Drawdown 10% global                            │  │
│  │  • Exposición max 3 estrategias simultáneas           │  │
│  │  • Tamaño posición: Kelly o 2% fix                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    MONITOREO IA                         │  │
│  • Detección anomalías en tiempo real                     │  │
│  • Ajuste exposición según performance                    │  │
│  • Alertas de cambio régimen                              │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. DETECCIÓN DE MOMENTUM/RÉGIMEN

### 3.1 Indicadores Clave

| Indicador | Bull | Bear | Lateral |
|-----------|------|------|---------|
| ADX | > 30 | > 30 | < 25 |
| RSI | > 60 | < 40 | 40-60 |
| Trend Price | ↑ | ↓ | → |

### 3.2 Algoritmo de Clasificación

```python
def classify_market_regime(dataframe):
    adx = dataframe['adx'].iloc[-1]
    rsi = dataframe['rsi'].iloc[-1]
    price_slope = calculate_slope(dataframe['close'], 20)
    
    if adx > 30 and rsi > 55 and price_slope > 0:
        return "BULL"
    elif adx > 30 and rsi < 45 and price_slope < 0:
        return "BEAR"
    else:
        return "LATERAL"
```

### 3.3 Timing de Detección

- **Frecuencia**: Cada 15 minutos
- **Ventana**: últimos 50 candles (4h+)
- **Confirmación**: 2 lecturas consecutivas del mismo régimen

---

## 4. MAPA DE ESTRATEGIAS

### 4.1 Estrategias Disponibles

| Nombre | Régimen | Lógica | Parámetros Clave |
|--------|---------|--------|------------------|
| ChacalPulse_Bull | Bull | Momentum + Volumen | ADX>30, RSI>60 |
| ChacalPulse_Bear | Bear | Short en momentum | ADX>30, RSI<40 |
| ChacalPulse_Lateral | Lateral | Rebote RSI | RSI<30, Trailing |
| ChacalPulse_Volume | Mining | Máximo volumen | RSI 10-70, 24h |

### 4.2 Detalle ChacalPulse_Lateral (GANADORA ACTUAL)

**Backtest Results (2026-01-01 to 2026-03-11):**

- Profit: **+22.11%**
- Win Rate: **82.5%**
- Trades: 519
- Max Drawdown: **7.21%**

**Parámetros Optimizados:**

```python
rsi_oversold = 37
v_factor_mult = 1.691
pulse_change = 0.0
gate_start_h = 3
gate_end_h = 21
lateral_roi = 0.045 (4.5%)
lateral_stoploss = -0.123 (-12.3%)
rsi_overbought = 63
```

**Exit Rules:**

1. Trailing Stop (99% win rate) ✅
2. RSI Overbought Exit (protege de drawdown) ✅
3. Stop Loss (hard) ❌

### 4.3 ChacalPulse_Bull (Por optimizar)

**Lógica:**

- Entrada: ADX > 30 AND RSI < 30 AND volumen spike
- Salida: Trailing stop + RSI overbought
- Short: NO

### 4.4 ChacalPulse_Bear (Por optimizar)

**Lógica:**

- Entrada: ADX > 30 AND RSI > 70 (sobrecomprado) AND volumen spike
- Salida: Trailing stop + RSI oversold
- Short: SI

---

## 5. GESTIÓN DE RIESGO INSTITUCIONAL

### 5.1 Reglas de Riesgo

| Parámetro | Valor | Notas |
|-----------|-------|-------|
| Max Drawdown por estrategia | 5% | Pause trading si se exceede |
| Max Drawdown global | 10% | Reducir exposición 50% |
| Max estrategias activas | 3 | Una por régimen máximo |
| Tamaño posición | 2% fix | O Kelly Criterion |
| Max pérdida diaria | 3% | Auto-pause |
| Max ganancia diaria | 5% | Take profit agresivo |

### 5.2 Posicionamiento

```python
def calculate_position_size(account_balance, risk_per_trade=0.02):
    """
    Kelly Criterion o Fixed 2%
    """
    return account_balance * risk_per_trade
```

### 5.3 Escalado de Exposición

| Condición | Exposición |
|-----------|-----------|
| Drawdown 0-3% | 100% normal |
| Drawdown 3-5% | 50% reducción |
| Drawdown 5-10% | 25% solo mejores estrategias |
| Drawdown >10% | 0% - pause total |

---

## 6. MONITOREO IA

### 6.1 Métricas a Monitorear

- [ ] Win rate actual vs histórico
- [ ] Avg profit por trade
- [ ] Duración trades winners vs losers
- [ ] Consecutive losses
- [ ] Drawdown actual
- [ ] Correlation entre estrategias

### 6.2 Alertas Automáticas

| Condición | Acción |
|-----------|--------|
| 5 losses consecutive | Reducir exposición 50% |
| Drawdown > 5% | Alert + reduce exposure |
| Win rate < 60% | Review strategy |
| Regime change detected | Switch strategy |

### 6.3 Rebalanceo

- **Frecuencia**: Diario
- **Basado en**: Performance últimas 24h
- **Acción**: Ajustar weights de estrategias

---

## 7. PIPELINE OPERATIVO

### 7.1 Ciclo de Desarrollo

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   BACKTEST  │────▶│  HYPEROPT   │────▶│   PAPER     │────▶│    LIVE     │
│   (Datos)   │     │ (Optimize)  │     │  (Testing)  │     │ (Production)│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     1 mes              500 epochs         1 semana           Monitoreo
```

### 7.2 Criterios de Promoción

| Fase | Condición |
|------|-----------|
| Backtest → Hyperopt | Sharpe > 1.5, Drawdown < 15% |
| Hyperopt → Paper | Win rate > 70%, Profit > 0 |
| Paper → Live | 1 semana sin issues |

### 7.3 Fallback

Si estrategia falla en live:

1. Reducir exposición 50%
2. Revisar métricas
3. Si falla más 3 días → pause
4. Volver a backtest con nuevos datos

---

## 8. IMPLEMENTACIÓN TÉCNICA

### 8.1 Estructura de Archivos

```
user_data/
├── strategies/
│   ├── ChacalPulseV4_Lateral.py      # ✅ Ganadora
│   ├── ChacalPulseV4_Bull.py        # ⏳ Por crear
│   ├── ChacalPulseV4_Bear.py        # ⏳ Por crear
│   └── ChacalPulseV4_Hyperopt.py    # Genérica
├── hyperopts/
│   └── (configs de hyperopt)
├── config.json
└── estrategias_activas.json
```

### 8.2 Archivos de Configuración

```json
{
  "estrategias": {
    "lateral": {
      "enabled": true,
      "max_exposure": 0.33,
      "min_regime_confidence": 0.7
    },
    "bull": {
      "enabled": true,
      "max_exposure": 0.33,
      "min_regime_confidence": 0.8
    },
    "bear": {
      "enabled": false,
      "max_exposure": 0.33,
      "min_regime_confidence": 0.8
    }
  },
  "riesgo": {
    "max_drawdown_global": 0.10,
    "max_drawdown_estrategia": 0.05,
    "tamano_posicion": 0.02,
    "max_estrategias_simultaneas": 3
  }
}
```

---

## 9. ESTRATEGIA DE DEPLOY

### 9.1 Fase 1: Consolidación Lateral

- Usar ChacalPulseV4_Lateral con parámetros optimizados
- Período: Hasta confirmar tendencia clara

### 9.2 Fase 2: Expansión

- Agregar detección de régimen
- Activar Bull/Bear según momento

### 9.3 Fase 3: Optimización Continua

- Monthly hyperopt con nuevos datos
- Ajustar parámetros según seasons

---

## 10. KPIs Y MÉTRICAS

### 10.1 Métricas de Éxito

| KPI | Target | Alert |
|-----|--------|-------|
| Monthly Return | > 5% | < 2% |
| Sharpe Ratio | > 1.5 | < 1.0 |
| Max Drawdown | < 10% | > 7% |
| Win Rate | > 75% | < 65% |
| Avg Trade Duration | < 4h | > 8h |

### 10.2 Dashboard

- Profit/Day
- Win Rate
- Drawdown
- Trades Count
- Regime Distribution
- Strategy Performance

---

## 11. PROMPT PARA AGENTE IA

### "Eres un Gestor de Trading Algorítmico Institucional"

**Contexto:**
Eres un sistema de trading algorítmico avanzado llamado "Chacal Pulse Trading System". Tu función es gestionar un portfolio de estrategias de trading automatizadas.

**Conocimiento:**

- Mercado crypto (BTC, ETH, altcoins)
- Análisis técnico (RSI, ADX, Bollinger, Volume)
- Gestión de riesgo institucional
- Freqtrade ecosystem

**Tareas:**

1. **Detectar régimen de mercado**: Analiza datos y clasifica (Bull/Bear/Lateral)
2. **Seleccionar estrategia**: Elige la mejor estrategia según régimen
3. **Gestionar riesgo**: Aplica reglas de position sizing y drawdown
4. **Monitorear**: Detecta anomalías y ajusta exposición
5. **Reportar**: Genera métricas diarias

**Reglas:**

- Nunca exceder 10% drawdown global
- Max 3 estrategias simultáneas
- Si 5 losses consecutive → reducir exposición 50%
- Siempre priorizar capital preservation

**Input:** Datos de mercado, estado actual del portfolio
**Output:** Decisión de trading (entrar/salir/esperar), tamaño posición, stop loss

---

## 12. RESUMEN EJECUTIVO

### Estado Actual

- ✅ **ChacalPulse_Lateral**: Ganadora (22% profit, 82.5% win)
- ⏳ **Bull/Bear**: Por optimizar
- ⏳ **Gestor IA**: Por implementar

### Próximos Pasos

1. Activar ChacalPulse_Lateral en paper trading
2. Crear estrategia Bull/Bear con hyperopt
3. Implementar detector de régimen
4. Construir gestor de riesgo
5. Deploy multi-estrategia

---

*Documento generado: 2026-03-13*
*Versión: 1.0*
*Autor: Sistema IA - Chacal Pulse*
