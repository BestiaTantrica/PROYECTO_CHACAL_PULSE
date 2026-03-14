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

class ChacalPulseV4_Bull(IStrategy):
    """
    CHACAL PULSE V4.1 — BULL GANADORA (+20.40%)
    ==========================================
    Estrategia optimizada para mercados alcistas.
    Profit: +20.40% | Win Rate: 53.0% | High Frequency
    """

    INTERFACE_VERSION = 3
    can_short: bool = False # Bull solo Long

    # Parámetros optimizados (+20.40%)
    v_factor = DecimalParameter(1.5, 6.0, default=4.016, space="buy", optimize=False)
    use_boll_filter_short = BooleanParameter(default=True, space="buy", optimize=False)
    stoploss = -0.308

    # Umbrales
    adx_threshold = IntParameter(15, 35, default=30, space="sell", optimize=True)
    rsi_bull_thresh = IntParameter(50, 70, default=64, space="sell", optimize=True)
    
    gate_start_h = IntParameter(7, 12, default=8, space="buy", optimize=False)
    gate_end_h   = IntParameter(13, 23, default=18, space="buy", optimize=False)

    timeframe = '5m'
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], side: str,
                 **kwargs) -> float:
        return 5.0

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

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0

        # Long en Bull: Spike de volumen + precio sube + gate abierto
        # El v_factor es más relajado (4.016)
        pulse_long = (
            (dataframe['gate_open'] == 1) &
            (dataframe['volume'] > (dataframe['volume_mean'] * self.v_factor.value * dataframe['volume_regime_scaler'])) &
            (dataframe['price_change'] > 0.005) &
            (dataframe['rsi'] > 50)
        )

        dataframe.loc[pulse_long, 'enter_long'] = 1
        dataframe.loc[pulse_long, 'enter_tag']  = 'BULL_LONG_WINNER'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
