import time

import MetaTrader5 as mt5
from datetime import datetime, timedelta
from pydantic import BaseModel, field_validator
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


class BaseSignal(BaseModel):
    magic: int
    month: int
    symbol: str
    entry: str
    tp: str
    sl: float
    sl_type: StoplossType
    risk: float
    direction: OrderDirection
    open_time: str | None
    close_time: str | None
    status: Status = Status.init
    ticket: int = None

    # allowed_symbols: tuple = ()

    # @field_validator("symbol")
    # def validate_symbol(cls,v):
    #     if v not in cls.allowed_symbols:
    #         logger.critical(f"{v} not in {cls.allowed_symbols}")
    #         raise exceptions.SignalSymbolNotFoundError(v)
    #     return v
    #



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





def parse_datetime(month_day, hour_min) -> datetime:
    return datetime(
        year=datetime.now().year,
        month=int(month_day.split(".")[1]),
        day=int(month_day.split(".")[0]),
        hour=int(hour_min.split(":")[0]),
        minute=int(hour_min.split(":")[1])
    )


class SeasonalSignal(BaseSignal):
    open_time_d: datetime | None = None
    close_time_d: datetime | None = None

    # @field_validator("open_time")
    # def validate_entry(cls, v: str):
    #     result = v.split(":")
    #
    #     if len(result) != 2:
    #         raise exceptions.SignalTimeStartFormatError(v)
    def __init__(self, **data):
        super().__init__(**data)
        self.info()

    def info(self):
        self.open_time_d = self.get_start_time()
        self.close_time_d = self.get_close_time()
        logger.info(f"Signal {self.__class__.__name__} was sucsessfuly created")
        logger.info(f"{self.__class__.__name__} time: {self.open_time_d}")
        logger.info(f"{self.__class__.__name__} end time: {self.close_time_d}")
        return self

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
        start_time_with_delta = start_time + timedelta(days=5)
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

    def get_request(self,terminal) -> ResponseOpen | ResponseClose | None:
        current_time = datetime.now()

        if self.status is Status.init:
            if current_time > self.open_time_d:
                return self.get_response_open(terminal)

        elif self.status is Status.open:
            if current_time > self.close_time_d:
                return self.get_response_close()

    def get_response_open(self,terminal):
        if not terminal.initialize():
            logger.critical("No terminal connection")
        point: mt5.SymbolInfo = terminal.symbol_info(self.symbol).point
        digits = terminal.symbol_info(self.symbol).digits

        price = (
            terminal.symbol_info(self.symbol).ask,
            terminal.symbol_info(self.symbol).bid
        )[self.direction == OrderDirection.long]


        sl = self.get_stoploss(
                price,point,
                self.direction,
                self.sl_type
            )
        distance = abs(price - sl) / point
        account_info:mt5.AccountInfo = terminal.account_info()
        if terminal.symbol_select(self.symbol,True):
            time.sleep(2)
        volume = self.get_lot_size(account_info,terminal.symbol_info(self.symbol),distance=distance)

        order_type = ("Long", "Short")[self.direction == OrderDirection.long]
        return ResponseOpen(
            type=order_type,
            symbol=self.symbol,
            price=price,
            sl=sl,
            volume=volume,
            magic=self.magic,
            comment="test"
        )

    def get_response_close(self):
        return ResponseClose(
            ticket=self.ticket,
            symbol=self.symbol
        )
    def get_stoploss(self, price, points, direction, type):
        print("DIRECTION: ",direction, "TYPE: ",type)
        if type == StoplossType.percentage:
            logger.debug("Stoploss type selecet Percentages")
            if direction == OrderDirection.long:
                logger.debug("Direction trade long")
                sl = price - (price * 0.01 * self.sl)
                logger.debug(f"Stoploss {sl}")
                return sl
            else:
                logger.debug("Direction trade short")
                sl = price + (price * 0.01 * self.sl)
                logger.debug(f"Stoploss {sl}")
                return sl
        else:
            logger.debug("Stoploss type selecet Points")
            if type == OrderDirection.long:
                logger.debug("Direction trade long")
                sl = price - self.sl * points
                logger.debug(f"Stoploss {sl}")
                return sl
            else:
                logger.debug("Direction trade short")
                sl = price + self.sl * points
                logger.debug(f"Stoploss {sl}")
                return sl

    def get_lot_size(self,account_info,symbol_info,distance):
        """
        double CSignal::GetPositionLots(double distanceOpenPriceStoploss)
          {
        // Calculate risk
           double lotSize = riskAmount / distanceOpenPriceStoploss / pointValue; // Размер лота
           Print("Лоты до преобразования:  ",lotSize);

           return RoundDown(lotSize);
          }
        :return:
        """
        logger.debug(f"Call method {self.__class__.__name__} - get_lot_size()")

        account_balance = account_info.balance
        account_equity = account_info.equity

        risk_amount = account_equity * self.risk / 100
        logger.debug(f"risk amount for current signal is {risk_amount}")

        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size
        point_value = tick_value / (tick_size / symbol_info.point)
        logger.info(f"{risk_amount=} | {distance=} | {point_value=}")
        try:
            lot_size = risk_amount / distance / point_value
        except ZeroDivisionError:
            time.sleep(30)
            return -1
        print(f"{symbol_info.volume_min=} | {symbol_info.volume_max=}")
        lot_size_round = count_decimal_places(lot_size,symbol_info.volume_min)
        print(f"INFO: {lot_size_round}")
        return lot_size_round



def count_decimal_places(number,min_lot):
    print(min_lot)
    precision = len(str(int(min_lot * 100)))
    print(precision)
    if precision == 1:
        return float(f"{number:.2f}")
    elif precision == 2:
        return float(f"{number:.1f}")
    elif precision == 3:
        return float(int(number))
    else:
        raise ValueError("Precision must be 1, 2, or 3")


class ShortTermSignal(BaseSignal):

    def info(self):
        ...


class BreakoutSignal(BaseSignal):

    def info(self):
        ...
