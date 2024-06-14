import time
from typing import Any

import MetaTrader5 as mt5
from datetime import datetime, timedelta

from MetaTrader5 import Tick
from pydantic import BaseModel, field_validator, validator
from enum import Enum
from utils import exceptions
from utils.logger_config import logger


class StoplossType(Enum):
    percentage = 0
    points = 1


class OrderDirection(Enum):
    long = 0
    short = 1


class Status(Enum):
    init = 1
    open = 2
    close = 3


class ResponseOpen(BaseModel):
    type: str
    symbol: str
    volume: float
    price: float
    sl: float
    tp: float = 0
    deviation: int = 50
    magic: int
    comment: str = ""


class ResponseClose(BaseModel):
    symbol: str
    ticket: int


def parse_datetime(month_day: str | tuple, hour_min) -> datetime:
    return datetime(
        year=datetime.now().year,
        month=int(month_day.split(".")[1]) if isinstance(month_day, str) else month_day[0],
        day=int(month_day.split(".")[0]) if isinstance(month_day, str) else month_day[1],
        hour=int(hour_min.split(":")[0]),
        minute=int(hour_min.split(":")[1])
    )


class BaseSignal(BaseModel):
    magic: int
    month: int
    symbol: str
    entry: str
    tp: str
    sl: float | str
    sl_type: StoplossType
    risk: float | str
    direction: OrderDirection
    open_time: str | None
    close_time: str | None
    status: Status = Status.init
    ticket: int = None
    counter:int = 0


    def __init__(self, **data):
        super().__init__(**data)
        self.info()


    def info(self):
        self.update()
        logger.info(
            f"Signal {self.__class__.__name__} was succsessfuly created")
        logger.info(f"{self.__class__.__name__} time: {self.open_time_d}")
        logger.info(f"{self.__class__.__name__} end time: {self.close_time_d}")

    def update(self):
        ...


    def check(self, terminal) -> ResponseOpen | ResponseClose | None:
        ...

    def get_stoploss(self, price, points):
        if self.direction == OrderDirection.long:
            if self.sl_type == StoplossType.percentage:
                return price - (price * 0.01 * self.sl)
            else:
                return price - self.sl * points
        else:
            if self.sl_type == StoplossType.percentage:
                return price + (price * 0.01 * self.sl)
            else:
                return price + self.sl * points

    def get_lot_size(self, account_info, symbol_info, distance):

        account_equity = account_info.equity
        risk_amount = account_equity * self.risk / 100
        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size
        point_value = tick_value / (tick_size / symbol_info.point)
        try:
            lot_size = risk_amount / distance / point_value
        except ZeroDivisionError:
            time.sleep(30)
            return -1
        lot_size_round = count_decimal_places(lot_size, symbol_info.volume_min)
        return lot_size_round

    def response_open(self, terminal):
        point: mt5.SymbolInfo = terminal.symbol_info(self.symbol).point
        digits: mt5.SymbolInfo = terminal.symbol_info(self.symbol).digits

        price = (
            terminal.symbol_info(self.symbol).ask
            if self.direction == OrderDirection.long
            else terminal.symbol_info(self.symbol).bid
        )
        sl = self.get_stoploss(
            price, point,

        )
        sl = round(sl, digits)
        distance = abs(price - sl) / point
        account_info: mt5.AccountInfo = terminal.account_info()
        if terminal.symbol_select(self.symbol, True):
            time.sleep(2)
        volume = self.get_lot_size(account_info,
                                   terminal.symbol_info(self.symbol),
                                   distance=distance)

        order_type = "Long" if self.direction == OrderDirection.long else "Short"
        return ResponseOpen(
            type=order_type,
            symbol=self.symbol,
            price=price,
            sl=sl,
            volume=volume,
            magic=self.magic,
            comment=self.__class__.__name__
        )

    def response_close(self):
        return ResponseClose(
            ticket=self.ticket,
            symbol=self.symbol
        )


class SeasonalSignal(BaseSignal):
    open_time_d: datetime | None = None
    close_time_d: datetime | None = None

    def update(self):
        if self.open_time_d is None:
            self.open_time_d = self.get_start_time()
        self.close_time_d = self.get_close_time()

    def get_start_time(self) -> datetime:
        """
        Return signal time for open trade
        :return: datetime:

        """
        current_time = datetime.now()
        start_time = parse_datetime(
            self.entry,
            self.open_time
        )
        start_time_with_delta = start_time
        if current_time > start_time_with_delta:
            start_time = start_time.replace(year=start_time.year + 1)
        return start_time

    def get_close_time(self) -> datetime:
        start_data: datetime = self.get_start_time()
        end_time: datetime = parse_datetime(
            self.tp,
            self.close_time
        )
        if start_data > end_time:
            end_time = end_time.replace(year=end_time.year + 1)

        return end_time

    def check(self, terminal) -> ResponseOpen | ResponseClose | None:
        current_time = datetime.now()

        if self.status is Status.init:
            if current_time > self.open_time_d:
                return self.response_open(terminal)

        elif self.status is Status.open:
            if current_time > self.close_time_d:
                return self.response_close()


def count_decimal_places(number, min_lot):
    precision = len(str(int(min_lot * 100)))
    if precision == 1:
        return float(f"{number:.2f}")
    elif precision == 2:
        return float(f"{number:.1f}")
    elif precision == 3:
        return float(int(number))
    else:
        raise ValueError("Precision must be 1, 2, or 3")


class ShortTermSignal(BaseSignal):
    start_day: int = None
    end_day: int = None

    def __init__(self, **data):
        super().__init__(**data)
        self.update()

    def update(self):
        self.start_day = int(self.entry.split(" ")[0])
        self.end_day = int(self.tp.split(" ")[0])

    def get_signal_trading_days(
            self,
            terminal: mt5,
            _time: datetime
    ):
        """
        Return trading days from selected date

        :param terminal: Terminal for interaction with MT5 API and getting rates
        :param _time: datetime variable from what date start gathering
        :return: Count of working days (bars that have minimum 1 tick volume)
        """

        rates = terminal.copy_rates_range(
            self.symbol,
            terminal.TIMEFRAME_D1,
            _time,
            datetime.now()

        )
        return len(rates)

    def info(self):
        ...

    def check_signal_time(self, _time):
        signal_time = parse_datetime(
            (datetime.now().month, datetime.now().day),
            _time
        )
        if datetime.now() < signal_time:
            return
        return signal_time

    def get_parse_time(self, hour_min: str):
        _time = datetime.now()
        hour, minute = map(int, hour_min.split(":"))
        _time = _time.replace(hour=hour, minute=minute, second=0)
        return _time

    def check(self, terminal: mt5):
        signal_date = datetime(
            year=datetime.now().year,
            month=self.month,
            day=1
        )
        work_day_in_month = self.get_signal_trading_days(
            terminal,
            signal_date
        )
        #logger.info(f"Trading days in month {work_day_in_month}")
        condition = (work_day_in_month >= self.start_day
                     if self.status == Status.init
                     else work_day_in_month >= self.end_day)
        if not condition: return None

        signal_time = self.get_parse_time(
            self.open_time if self.status == Status.init else self.close_time)

        if datetime.now() > signal_time:
            if self.status == Status.init:
                logger.info(f"Return responce open")
                return self.response_open(terminal)
            elif self.status == Status.open:
                logger.info(f"Return responce close")
                return self.response_close()
            return (self.response_open(terminal)
                    if self.status == Status.init
                    else self.response_close())


class BreakoutSignal(BaseSignal):
    start_day: datetime = None
    end_day: int = None
    prev_high: float = None
    prev_low: float = None
    signal_time: datetime = None

    def __init__(self, **data):
        super().__init__(**data)
        self.update()

    def update(self):
        self.end_day = int(self.tp.split(" ")[0])
        self.start_day = datetime(
            year=datetime.now().year,
            month=self.month,
            day=1
        )

    def info(self):
        ...
    def check_counter(self,terminal):
        self.counter += 1
        if self.counter > 360:
            self.counter = 0
            work_day_in_month = self.get_signal_trading_days(
                terminal,
                self.signal_time
            )

            logger.info(
                (f"{self.__class__.__name__} trade with magic"
                 f"[{self.magic}] has been opened on {self.signal_time.strftime('%Y-%m-%d %H:%M')} with the duration of {self.end_day} TD."
                 f"Left {work_day_in_month} TD")
            )

    def check(self, terminal: mt5) -> ResponseOpen | ResponseClose | None:


        if self.prev_high is None or self.prev_low is None:
            prev_bar = terminal.copy_rates_from_pos(self.symbol,
                                                    terminal.TIMEFRAME_D1,
                                                    1, 1)[0]
            self.prev_high = prev_bar[2]
            self.prev_low = prev_bar[3]
        if self.status is Status.init:
            if datetime.now() > self.start_day:
                tick: Tick = terminal.symbol_info_tick(self.symbol)
                condition = (tick.bid > self.prev_high
                             if self.entry == "PMH"
                             else tick.ask < self.prev_low)
                if condition:
                    message = (
                        f"{self} send request bid price: {tick.bid} > {self.prev_high}"
                        if self.entry == "PMH"
                        else f"send request ask price{tick.ask} < {self.prev_low}"
                    )
                    logger.info(message)
                    self.signal_time = datetime.now()
                    return self.response_open(terminal)

        if self.status is Status.open:
            self.check_counter(terminal)
            work_day_in_month = self.get_signal_trading_days(
                terminal,
                self.signal_time
            )

            if work_day_in_month > self.end_day:
                if datetime.now() > self.signal_time:
                    return self.response_close()

    def get_signal_trading_days(
            self,
            terminal: mt5,
            _time: datetime
    ):
        """
        Return trading days from selected date

        :param terminal: Terminal for interaction with MT5 API and getting rates
        :param _time: datetime variable from what date start gathering
        :return: Count of working days (bars that have minimum 1 tick volume)
        """
        rates = terminal.copy_rates_range(
            self.symbol,
            terminal.TIMEFRAME_D1,
            _time,
            datetime.now()

        )
        return len(rates)

    def check_signal_time(self, _time):
        signal_time = parse_datetime(
            (datetime.now().month, datetime.now().day),
            _time
        )
        if datetime.now() < signal_time:
            return
        return signal_time
