# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union, Any, cast
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)
from freqtrade.persistence import Trade

class ChacalPulseV4_Lateral(IStrategy):
    """
    CHACAL PULSE V4.1 — LATERAL GANADORA (+22.11%)
    ==============================================
    Estrategia optimizada para mercados laterales.
    Profit: +22.11% | Win Rate: 82.5% | Max DD: 7.21%
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    # Parámetros optimizados (+22.11%)
    v_factor_mult = DecimalParameter(0.5, 2.0, default=1.691, space="buy", optimize=True)
    rsi_oversold = IntParameter(20, 50, default=37, space="buy", optimize=True)
    rsi_overbought = IntParameter(50, 80, default=63, space="sell", optimize=True)
    lateral_roi = DecimalParameter(0.01, 0.10, default=0.045, space="sell", optimize=True)
    lateral_stoploss = DecimalParameter(-0.20, -0.05, default=-0.123, space="sell", optimize=True)

    gate_start_h = IntParameter(0, 12, default=3, space="buy", optimize=False)
    gate_end_h   = IntParameter(13, 23, default=21, space="buy", optimize=False)

    trailing_stop = True
    trailing_stop_positive = 0.008
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True
    stoploss = -0.20
    timeframe = '5m'

    v_factor = DecimalParameter(1.5, 8.0, default=4.597, space="buy", load=True, optimize=False)
    pulse_change = DecimalParameter(0.0, 0.01, default=0.0, space="buy", load=True, optimize=False)

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], side: str,
                 **kwargs) -> float:
        return 3.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['volume_mean'] = dataframe['volume'].rolling(20).mean()

        dataframe['date_utc'] = pd.to_datetime(dataframe['date'], utc=True)
        dataframe['hour']     = dataframe['date_utc'].dt.hour
        dataframe['day_of_week'] = dataframe['date_utc'].dt.dayofweek
        dataframe['is_weekend'] = 0 # Liberado para Dry Run
        dataframe['gate_open'] = 1 # Liberado para Dry Run

        dataframe['price_change'] = (dataframe['close'] - dataframe['open']) / dataframe['open']

        # Gestión Horaria - Salida Programada Hoy (15 de Marzo)
        # 12:30 Art = 15:30 UTC | 13:00 Art = 16:00 UTC
        dataframe['exit_scheduled'] = 0
        dataframe.loc[dataframe['hour'] >= 16, 'exit_scheduled'] = 1

        # Restricción de entrada: No entrar después de las 15:30 UTC (12:30 Art)
        dataframe['entry_allowed'] = 1
        # Simplificación: si es >= 16h cerramos todo, si es >= 15h y min >= 30 bloqueamos entrada
        # Pero freqtrade maneja horas UTC. 
        # Para ser precisos, usamos una marca temporal de la vela
        dataframe['is_after_1530_utc'] = (dataframe['hour'] > 15) | ((dataframe['hour'] == 15) & (dataframe['date_utc'].dt.minute >= 30))
        dataframe.loc[dataframe['is_after_1530_utc'], 'entry_allowed'] = 0

        volume_1h = dataframe['volume'].rolling(12).mean().replace(0, np.nan)
        dataframe['volume_regime_scaler'] = (
            dataframe['volume_mean'] / volume_1h
        ).clip(0.5, 2.0).fillna(1.0)

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        return self.lateral_stoploss.value

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        if current_profit >= self.lateral_roi.value:
            return "lateral_roi_winner"
        
        # Cierre forzoso programado (Hoy 13:00 Art / 16:00 UTC)
        if current_time.hour >= 16:
            return "scheduled_exit_13h_art"
        
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is not None and len(cast(Any, dataframe)) > 0:
                last_candle = dataframe.iloc[-1]
                rsi = float(last_candle.get('rsi', 50.0))
                if rsi > self.rsi_overbought.value:
                    return "rsi_overbought_exit"
        except:
            pass
        
        return None

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        # v_factor efectivo: base × mult_lateral × scaler_volumen
        dataframe['v_factor_eff'] = (
            self.v_factor.value *
            self.v_factor_mult.value *
            dataframe['volume_regime_scaler']
        )

        pulse_long = (
            (dataframe['gate_open'] == 1) &
            (dataframe['entry_allowed'] == 1) &
            (dataframe['rsi'] < self.rsi_oversold.value) &
            (dataframe['rsi'] > 15) &
            (
                (dataframe['volume'] > (dataframe['volume_mean'] * dataframe['v_factor_eff'])) |
                (dataframe['price_change'] > self.pulse_change.value)
            )
        )

        dataframe.loc[pulse_long, 'enter_long'] = 1
        dataframe.loc[pulse_long, 'enter_tag']  = 'LATERAL_LONG_WINNER'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
