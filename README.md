# 🦅 CHACAL PULSE TRADING SYSTEM

Sistema de trading algorítmico multi-estrategia con detección automática de régimen de mercado.

---

## 📁 ESTRUCTURA DEL PROYECTO

```
CHACAL_PULSE/
├── 📄 README.md                    # Este archivo
├── 📄 GITHUB_DEPLOY.md             # Instrucciones para Copilot/Git
├── 📄 SISTEMA_TRADING_INSTITUCIONAL.md  # Arquitectura completa
│
├── 📂 config/                      # Configuraciones
│   ├── config.json                 # Config principal Freqtrade
│   ├── docker-compose.yml          # Docker Compose
│   └── telegram.json               # Config Telegram
│
├── 📂 strategies/                   # Estrategias
│   ├── ChacalPulseV4_Hyperopt.py  # Estrategia MADRE (LIVE)
│   ├── ChacalPulseV4_Lateral.py   # Lateral optimizada
│   └── ChacalPulseV4_Lateral_BAK.py  # Backup
│
├── 📂 scripts/                     # Scripts operativos
│   ├── deploy_aws.sh               # Despliegue a AWS
│   ├── start_live.sh               # Iniciar bot live
│   ├── stop_live.sh                # Detener bot
│   ├── health_check.sh              # Health check
│   └── backup.sh                   # Backup automático
│
├── 📂 detection/                    # Detección de régimen
│   ├── regime_detector.py          # Script principal
│   └── requirements.txt             # Dependencias
│
└── 📂 docs/                       # Documentación
    ├── BIBLIOTECA_RESULTADOS.md    # Resultados hyperopt
    └── PARAMETROS_ACTIVOS.md       # Parámetros actuales
```

---

## 🚀 QUICK START

### 1. Clonar en AWS

```bash
git clone https://github.com/tu-usuario/chacal-pulse.git
cd Chacal-Pulse
```

### 2. Configurar variables

```bash
cp config/config.json.example config/config.json
# Editar API keys y configuración
```

### 3. Iniciar Docker

```bash
docker-compose up -d
```

### 4. Verificar estado

```bash
docker-compose ps
docker-compose logs -f freqtrade
```

---

## ⚙️ ESTRATEGIAS DISPONIBLES

### OPCIÓN A: Estrategia Unificada (ya corriendo)

| Estrategia | Régimen | Estado | Profit |
|-----------|---------|--------|--------|
| ChacalPulseV4_Hyperopt | ALL | LIVE DRY RUN | ~2%/semana |
| ChacalPulseV4_Lateral | Lateral | Optimizado | +22% backtest |

### OPCIÓN B: 3 Estrategias Separadas + IA Manager (en desarrollo)

| Estrategia | Régimen | Estado |
|-----------|---------|--------|
| ChacalPulseV4_Bull | Bull | Por crear |
| ChacalPulseV4_Bear | Bear | Por crear |
| ChacalPulseV4_Lateral | Lateral | Por crear |

**IA Manager**: `ia_manager/regime_manager.py` - Cambia estrategias automáticamente

---

## 📊 DETECCIÓN DE RÉGIMEN

El script `detection/regime_detector.py` analiza el mercado cada 15 minutos y determina si estamos en:

- **BULL**: Usar estrategia alcista
- **BEAR**: Usar estrategia bajista
- **LATERAL**: Usar estrategia lateral

### Configurar en AWS

```bash
# Agregar al crontab
*/15 * * * * cd /home/ec2-user/Chacal-Pulse && python detection/regime_detector.py >> /var/log/regime.log 2>&1
```

---

## 🔧 OPERACIONES COMMONES

### Reiniciar bot

```bash
./scripts/stop_live.sh
./scripts/start_live.sh
```

### Ver logs

```bash
docker-compose logs -f freqtrade
```

### Backup

```bash
./scripts/backup.sh
```

---

## 📝 NOTAS PARA COPILOT/GITHUB

1. **No subir**: Archivos grandes de hyperopt (/*.fthypt)
2. **No subir**: Keys o passwords (usar .env)
3. **Sí subir**: Estrategias, scripts, configs ejemplo

Ver `GITHUB_DEPLOY.md` para más detalles.

---

## 🎯 HORAS MÁGICAS

El sistema opera最佳的 en horario 08:00 - 18:00 UTC (ventana validada por hyperopt).

---

*Sistema creado: 2026-03-13*
*Versión: 4.1*
