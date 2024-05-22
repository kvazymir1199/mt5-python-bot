import MetaTrader5 as mt5
from datetime import datetime, timedelta
from pydantic import BaseModel
from enum import Enum

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


class ResponseOpen(BaseModel):
    symbol: str
    volume: float
    price: float
    sl: float
    tp: float = 0
    deviation: int = 20
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

    def __init__(self, **data):
        super().__init__(**data)
        self.open_time_d = self.get_start_time()
        self.close_time_d = self.get_close_time()


    def info(self):
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
        start_time_with_delta = start_time + timedelta(minutes=5)
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

    def get_request(self, terminal) -> ResponseOpen | ResponseClose | None:
        current_time = datetime.now()

        if self.status is Status.init:
            if current_time > self.open_time_d:
                return self.get_response_open(terminal)

        elif self.status is Status.open:
            if current_time > self.close_time_d:
                return self.get_response_close()

    def get_response_open(self,terminal):
        point: mt5.SymbolInfo = terminal.symbol_info(self.symbol).point
        digits = terminal.symbol_info(self.symbol).digits

        price = (
            terminal.symbol_info(self.symbol).ask,
            terminal.symbol_info(self.symbol).bid
        )[self.direction == OrderDirection.long]


        sl = round(
            self.get_stoploss(
                price,point,
                self.direction,
                self.sl_type
            ),
            digits
        )
        distance = abs(price - sl) / point
        account_info:mt5.AccountInfo = terminal.account_info()
        volume = self.get_lot_size(account_info,terminal.symbol_info(self.symbol),distance=distance)

        return ResponseOpen(
            symbol=self.symbol,
            price=price,
            sl=sl,
            volume=volume,
            magic=12345,
            comment="test"
        )

    def get_response_close(self):
        return ResponseClose(
            ticket=self.ticket,
            symbol=self.symbol
        )
    def get_stoploss(self, price, points, direction, type):
        logger.debug("Call function get.stoploss ")
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
        lot_size = risk_amount / distance / point_value
        return round(lot_size,2)
        """
        double multiplier = MathPow(
        10, CountDigitsBeforeDecimal(SymbolInfoDouble(NULL,SYMBOL_VOLUME_MIN)));
   return MathFloor(value * multiplier) / multiplier;
   """




class ShortTermSignal(BaseSignal):

    def info(self):
        ...


class BreakoutSignal(BaseSignal):

    def info(self):
        ...
