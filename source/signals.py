from datetime import datetime
from pydantic import BaseModel
from typing import Literal, Any
from enum import Enum
import MetaTrader5 as mt5
from MetaTrader5 import AccountInfo

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
    ...

class ResponseClose(BaseModel):
    ...

def parse_datetime(month_day, hour_min) -> datetime:
    return datetime(
        year=datetime.now().year,
        month=int(month_day.split(".")[1]),
        day=int(month_day.split(".")[0]),
        hour=int(hour_min.split(":")[0]),
        minute=int(hour_min.split(":")[1])
    )


class SeasonalSignal(BaseSignal):

    def info(self):
        return self

    def get_start_time(self) -> datetime:
        """
        Return signal time for open trade
        :return: datetime:

        """
        return parse_datetime(
            self.entry,
            self.open_time
        )

    def get_close_time(self) -> datetime:
        start_data: datetime = self.get_start_time()
        end_time: datetime = parse_datetime(
            self.tp,
            self.close_time
        )
        if start_data > end_time:
            print("Signal in new year")
            end_time = end_time.replace(year=end_time.year + 1)

        return end_time




    def main(self) -> ResponseOpen | ResponseClose | None:
        current_time = datetime.now()
        if self.status is Status.init:
            if current_time > self.get_start_time():
                """Return data to open order"""
                return ResponseOpen()

        elif self.status is Status.open:
            if current_time > self.get_close_time():
                """Return data to close order"""
                return ResponseClose()


class ShortTermSignal(BaseSignal):

    def info(self):
        ...


class BreakoutSignal(BaseSignal):

    def info(self):
        ...
