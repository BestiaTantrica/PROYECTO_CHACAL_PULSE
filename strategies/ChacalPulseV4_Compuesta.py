# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union, Dict, Any, cast
import talib.abstract as ta
import math

import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)
from freqtrade.persistence import Trade

class ChacalPulseV4_Compuesta(IStrategy):
    """
    CHACAL PULSE V4.5 — ESTRATEGIA COMPUESTA (CON MOTOR PROPORCIONAL)
    ================================================================
    V4.5.1 - Corregido par informativo y flexibilizado para primer test.
    """

    INTERFACE_VERSION = 3
    can_short: bool = True 

    # --- Hyperopt Parameters (Matemática Sigmoide - OPTIMIZADOS EPOCH 69) ---
    vol_target = DecimalParameter(1.2, 3.0, default=2.255, space="buy", optimize=True)
    mom_multiplier = DecimalParameter(1.0, 5.0, default=3.057, space="buy", optimize=True)
    rsi_center = IntParameter(40, 60, default=55, space="buy", optimize=True)
    score_threshold = DecimalParameter(0.65, 0.9, default=0.868, space="buy", optimize=True)
    override_threshold = DecimalParameter(0.80, 0.98, default=0.859, space="buy", optimize=True)
    
    # --- Parámetros Originales Lateral (+22.11%) ---
    v_factor_mult = DecimalParameter(0.8, 2.5, default=1.476, space="buy", optimize=True)
    rsi_oversold = IntParameter(20, 50, default=32, space="buy", optimize=True)
    rsi_overbought = IntParameter(50, 80, default=63, space="sell", optimize=True)
    lateral_roi = DecimalParameter(0.02, 0.12, default=0.045, space="sell", optimize=True)
    lateral_stoploss = DecimalParameter(-0.08, -0.04, default=-0.05, space="sell", optimize=True)

    gate_start_h = IntParameter(0, 12, default=3, space="buy", optimize=False)
    gate_end_h   = IntParameter(13, 23, default=21, space="buy", optimize=False)
    
    v_factor = DecimalParameter(2.5, 8.0, default=4.0, space="buy", load=True, optimize=False)
    pulse_change = DecimalParameter(0.0, 0.01, default=0.0, space="buy", load=True, optimize=False)

    # Risk Management
    trailing_stop = True
    trailing_stop_positive = 0.008
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True
    stoploss = -0.05
    timeframe = '5m'
    max_open_trades = 12

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], side: str,
                 **kwargs) -> float:
        return 3.0

    def informative_pairs(self):
        # IMPORTANTE: En Futures Binance, los pares se descargan con :USDT al final
        return [("BTC/USDT:USDT", "5m")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Indicadores Base
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['volume_mean'] = dataframe['volume'].rolling(30).mean()
        
        # Horarios
        dataframe['date_utc'] = pd.to_datetime(dataframe['date'], utc=True)
        dataframe['hour']     = dataframe['date_utc'].dt.hour
        dataframe['gate_open'] = (
            (dataframe['hour'] >= self.gate_start_h.value) &
            (dataframe['hour'] < self.gate_end_h.value)
        ).astype(int)
        
        dataframe['price_change'] = (dataframe['close'] - dataframe['open']) / dataframe['open']
        
        # Volumen Scaling
        volume_1h = dataframe['volume'].rolling(12).mean().replace(0, np.nan)
        dataframe['volume_regime_scaler'] = (
            dataframe['volume_mean'] / volume_1h
        ).clip(0.5, 2.0).fillna(1.0)
        
        dataframe['vol_ratio'] = np.where(dataframe['volume_mean'] > 0, 
                                          dataframe['volume'] / dataframe['volume_mean'], 1.0)
        
        # Informativa BTC - Ajuste de nombre de par para Backtest
        inf_pair = "BTC/USDT:USDT"
        informative = self.dp.get_pair_dataframe(pair=inf_pair, timeframe='5m')
        
        if informative is not None and not informative.empty:
            informative = informative.copy()
            informative['btc_rsi'] = ta.RSI(informative, timeperiod=14)
            informative['btc_change_15m'] = informative['close'].pct_change(periods=3)
            informative['btc_change_1h'] = informative['close'].pct_change(periods=12)
            
            dataframe = pd.merge(dataframe, informative[['date', 'btc_rsi', 'btc_change_15m', 'btc_change_1h']], 
                                 on='date', how='left').fillna(method='ffill')
        else:
            # Fallback si falla la informativa en local
            dataframe['btc_rsi'] = 50.0
            dataframe['btc_change_15m'] = 0.0
            dataframe['btc_change_1h'] = 0.0

        # --- Motor de Probabilidad (Matemática Sigmoide) ---
        # Scoring Volumen
        dataframe['score_vol'] = 1.0 / (1.0 + np.exp(-3.0 * (dataframe['vol_ratio'] - self.vol_target.value)))
        
        # Scoring Momentum BTC
        chg = dataframe['btc_change_15m'] * 100
        dataframe['score_mom'] = np.where(chg > 0, 
                                          1.0 / (1.0 + np.exp(-self.mom_multiplier.value * (chg + 0.5))),
                                          1.0 - (1.0 / (1.0 + np.exp(-self.mom_multiplier.value * (np.abs(chg) + 0.5)))))
        
        # Scoring RSI BTC (Gaussiana centrada)
        dataframe['score_rsi'] = np.exp(-((dataframe['btc_rsi'] - self.rsi_center.value)**2) / 450.0)
        
        # Score Consolidado
        dataframe['total_score'] = (dataframe['score_vol'] * 0.4) + (dataframe['score_mom'] * 0.4) + (dataframe['score_rsi'] * 0.2)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        
        # V Factor dinámico
        dataframe['v_factor_eff'] = (
            self.v_factor.value *
            self.v_factor_mult.value *
            dataframe['volume_regime_scaler']
        )
        
        # Override de Gate si hay Vol institucional REAL
        dataframe['gate_eff'] = np.where(dataframe['total_score'] >= self.override_threshold.value, 1, dataframe['gate_open'])

        # Entrada Long (Endurecida para evitar ruido de mercado)
        long_cond = (
            (dataframe['gate_eff'] == 1) &
            (dataframe['rsi'] < self.rsi_oversold.value) &
            (
                (dataframe['volume'] > (dataframe['volume_mean'] * dataframe['v_factor_eff'])) |
                (dataframe['total_score'] >= self.score_threshold.value)
            ) &
            (dataframe['btc_change_1h'] > -0.01) # Filtro más estricto contra caídas BTC
        )
        dataframe.loc[long_cond, 'enter_long'] = 1
        dataframe.loc[long_cond, 'enter_tag'] = 'COMPOUND_LONG'

        # Entrada Short / Pivote Bear (SOLO EN CAÍDAS VIOLENTAS)
        short_cond = (
            (dataframe['total_score'] < 0.25) & # Señal de debilidad extrema
            (dataframe['btc_change_1h'] < -0.025) & # Solo si BTC ya cayó un 2.5%
            (dataframe['rsi'] > 30) # No entrar si ya está muy sobrevendido
        )
        dataframe.loc[short_cond, 'enter_short'] = 1
        dataframe.loc[short_cond, 'enter_tag'] = 'PIVOT_BEAR_SHORT'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0
        return dataframe
        
    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        return self.lateral_stoploss.value

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        if current_profit >= self.lateral_roi.value:
            return "lateral_roi_winner"
        
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is not None and len(cast(Any, dataframe)) > 0:
                last_candle = dataframe.iloc[-1]
                rsi = float(last_candle.get('rsi', 50.0))
                if trade.is_short:
                    if rsi < 35: return "short_rsi_exit"
                else:
                    if rsi > self.rsi_overbought.value: return "long_rsi_exit"
        except:
            pass
        
        return None
