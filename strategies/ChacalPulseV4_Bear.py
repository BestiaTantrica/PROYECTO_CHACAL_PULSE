# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)
from freqtrade.persistence import Trade

class ChacalPulseV4_Bear(IStrategy):
    """
    CHACAL PULSE V4.1 — BEAR GANADORA (+44.65%)
    ==========================================
    Estrategia optimizada para mercados bajistas.
    Profit: +44.65% | Win Rate: 67.7% | High Defense
    """

    INTERFACE_VERSION = 3
    can_short: bool = True # Bear se enfoca en Short

    # Parámetros optimizados (+44.65%)
    v_factor = DecimalParameter(5.0, 10.0, default=7.838, space="buy", optimize=False)
    v_factor_mult_sideways = DecimalParameter(0.1, 0.8, default=0.385, space="buy", optimize=False)
    use_boll_filter_short = BooleanParameter(default=False, space="buy", optimize=False)
    stoploss = -0.057
    
    bear_roi = DecimalParameter(0.005, 0.05, default=0.014, space="sell", optimize=False)

    gate_start_h = IntParameter(7, 12, default=8, space="buy", optimize=False)
    gate_end_h   = IntParameter(13, 23, default=18, space="buy", optimize=False)

    timeframe = '5m'
    trailing_stop = True
    trailing_stop_positive = 0.005
    trailing_stop_positive_offset = 0.01

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
        dataframe['is_weekend'] = (dataframe['day_of_week'] >= 5).astype(int)

        dataframe['gate_open'] = (
            (dataframe['hour'] >= self.gate_start_h.value) &
            (dataframe['hour'] < self.gate_end_h.value) &
            (dataframe['is_weekend'] == 0)
        ).astype(int)

        dataframe['price_change'] = (dataframe['close'] - dataframe['open']) / dataframe['open']
        
        volume_1h = dataframe['volume'].rolling(12).mean().replace(0, np.nan)
        dataframe['volume_regime_scaler'] = (
            dataframe['volume_mean'] / volume_1h
        ).clip(0.5, 2.0).fillna(1.0)

        return dataframe

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        # ROI agresivo de Bear Market: "toma un 1% y corre"
        if current_profit >= self.bear_roi.value:
            return "bear_roi_winner"
        return None

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0

        # Bear Short: Volumen de caída + Precio bajando + RSI bajo
        # v_factor efectivo usa mult_sideways por defecto para atrapar rebotes
        v_eff = self.v_factor.value * self.v_factor_mult_sideways.value * dataframe['volume_regime_scaler']

        pulse_short = (
            (dataframe['gate_open'] == 1) &
            (dataframe['volume'] > (dataframe['volume_mean'] * v_eff)) &
            (dataframe['price_change'] < 0) &
            (dataframe['rsi'] < 48)
        )

        dataframe.loc[pulse_short, 'enter_short'] = 1
        dataframe.loc[pulse_short, 'enter_tag']  = 'BEAR_SHORT_WINNER'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
