from typing import Callable,Optional
from functools import wraps
import MetaTrader5 as mt5
from MetaTrader5 import AccountInfo, SymbolInfo, OrderSendResult
from pydantic import ValidationError
from datetime import datetime,timedelta
from utils.logger_config import logger
from pathlib import Path
import csv
from signals import SeasonalSignal, ShortTermSignal, BreakoutSignal, ResponseOpen
import time
from signals import OrderDirection, StoplossType, ResponseClose, Status
from utils import exceptions

import os
from dotenv import load_dotenv

# Загрузите переменные окружения из файла .env
load_dotenv(
    dotenv_path=os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'config', '.env'
    )
)


def on_timer(timer_seconds: int):
    def function(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_check_time = time.time()
            func(*args, **kwargs)
            while True:
                current_time = time.time()
                if current_time - last_check_time > timer_seconds:
                    # print("".join(["==_==" for _ in range(10)]))
                    # logger.info("Вызов функции on_timer")
                    func(*args, **kwargs)
                    # print("".join(["==_==" for _ in range(10)]))
                    last_check_time = time.time()

        return wrapper

    return function

def f(dig:str):
    return float(dig.replace(',', '.'))

def connection(func):
    def wrapper(self, *args, **kwargs):

        if self.terminal.initialize(path=self.path):
            result = func(self,*args, **kwargs)
            self.terminal.shutdown()
            return result

    return wrapper


class Expert:
    """
           Class expert represent a expert class like in mql5
           Include OnTick(), OnInit(), OnDeinit(),OnTimer() functions

    """
    terminal = mt5
    path = os.getenv("TERMINAL_PATH")
    last_error = None

    def __init__(self):
        """
        Imitate OnInit function

        Function takes
        :param con:
        """

        self.signals: list[SeasonalSignal, ShortTermSignal, BreakoutSignal] = []

        self.csv_file: Path = Path(__file__).parent.parent / "files" / f"{os.getenv("FILE_NAME")}.csv"
        self.refresh_signals()



    @connection
    def refresh_signals(self):
        try:
            with self.csv_file.open("r", newline="") as file:
                reader = csv.DictReader(file, delimiter=";")
                for data in reader:
                    try:
                        magic = int(data["Magic Number"])
                        for signal in self.signals:
                            if signal.magic == magic:
                                self.update(signal, data)
                                break
                        else:
                            signal = self.create(data)
                            signal_status = self.order_exists(data)
                            signal.status,signal.ticket = signal_status
                            self.signals.append(signal)

                    except ValidationError as e:
                        logger.critical(f"Validation error for row {data}: {e}")
        except FileNotFoundError:
            logger.critical(f"File {self.csv_file} not found.")
        except Exception as e:
            logger.critical(f"An error occurred: {e}")

    def create(self, data: dict):

        signal = self.parse_signal_type(
            data.get("Type")
        )
        symbol = data.get("Symbol")
        if self.terminal.symbol_info(symbol) is None:
            logger.critical(f"Signal {signal.__name__} was not created.")
            raise exceptions.SignalSymbolNotFoundError(symbol)

        logger.info(f"Start create new signal {signal.__name__}")
        return signal(
            magic=int(data['Magic Number']),
            month=int(data['Month']),
            symbol=data['Symbol'],
            entry=data['Entry'],
            tp=data["TP"],
            sl=f(data['SL']),
            sl_type=StoplossType.percentage if data['SL Type'] == "Percentage" else StoplossType.points,
            risk=f(data['Risk']),
            direction= OrderDirection.long if data['Direction'] == "Long" else OrderDirection.short,
            open_time=data['Open Time'] if data['Open Time'] else None,
            close_time=data['Close Time'] if data['Close Time'] else None,
        )

    def update(self,signal, data:dict):
        signal.magic = int(data['Magic Number'])
        signal.month = int(data['Month'])
        signal.symbol = data['Symbol']
        signal.entry = data['Entry']
        signal.tp = data["TP"]
        signal.sl = f(data['SL'])
        signal.sl_type = StoplossType.percentage if data['SL Type'] == "Percentage" else  StoplossType.points
        signal.risk = f(data['Risk'])
        signal.direction = OrderDirection.long if data['Direction'] == "Long" else OrderDirection.short
        signal.open_time = data['Open Time'] if data['Open Time'] else None
        signal.close_time = data['Close Time'] if data['Close Time'] else None
        signal.update()

    def order_exists(self,data:dict):
        """ Function check signal by magic and symbol in open and history orders.
        If signal wasn't founded, return True,else False"""
        symbol = data.get("Symbol")
        magic = int(data.get("Magic Number"))
        orders = tuple(filter(lambda order: order.magic == int(magic), self.terminal.positions_get(symbol=symbol)))
        if not orders:
            from_date = datetime.now() - timedelta(days=365)
            to_date = datetime.now() + timedelta(days=2)
            logger.info(f"Will check {magic} from {from_date} to {datetime.now()}")
            orders = self.terminal.history_deals_get(from_date, to_date)
            orders = tuple(filter(lambda order: order.magic == int(magic) and order.symbol == symbol,orders))
            print(f"List of open deals filter by magic={magic}:\n found {len(orders)} orders")
            if not orders:
                logger.info(f"Not found order with this magic")
                return Status.init, None
        else:
            return Status.open, orders[-1].ticket
        return Status.close,None

    @staticmethod
    def parse_signal_type(signal_type: str):
        if signal_type == "Seasonal":
            return SeasonalSignal
        elif signal_type == "Short-term":
            return ShortTermSignal
        else:
            return BreakoutSignal

    def get_filling_mode(self, symbol):
        """
        The MetaTrader5 library doesn't find the filling mode correctly for a lot of brokers
        """
        for i in range(2):
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": mt5.symbol_info(symbol).volume_min,
                "type": mt5.ORDER_TYPE_BUY,
                "price": mt5.symbol_info_tick(symbol).ask,
                "type_filling": i,
                "type_time": mt5.ORDER_TIME_GTC}

            result = mt5.order_check(request)

            if result.comment == "Done":
                break

        return i

    @on_timer(1)
    def main(self):
        """
        Calls two function
        1 - create or update information about signals
        2 - manage signal behaviour
        :return: None
        """
        self.refresh_signals()
        self.check_signals()

    def check_signals(self):
        """
        Check signals and calls manage function depends on class type
        :return: None
        """
        for signal in self.signals:
            self.manage_signal(signal)



    @connection
    def manage_signal(self, signal):
        """
        Handle signal data and send request depends on getted signal data
        :param signal:
        :return:
        """

        request: ResponseOpen | ResponseClose | None = signal.check(
            terminal=self.terminal
        )
        if request is None: return
        try:
            if isinstance(request, ResponseOpen):
                signal.ticket = self.send_request(request)
                if signal.ticket is not None:
                    signal.status = Status.open
            elif isinstance(request, ResponseClose):
                if self.terminal.Close(symbol=request.symbol, ticket=request.ticket):
                    logger.info(f"Order with ticket: {request.ticket} was successfully closed")
                    signal.status = Status.close
        except Exception as e:

            if self.last_error != e.status_code:
                logger.error(e)
                self.last_error = e.status_code

    def send_request(self, request: ResponseOpen) -> int | None:
        filling_type = self.get_filling_mode(request.symbol)
        r = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.volume,
            "type":  mt5.ORDER_TYPE_BUY if request.type == "Long" else mt5.ORDER_TYPE_SELL,
            "price": request.price,
            "deviation": request.deviation,
            "sl": request.sl,
            "magic": request.magic,
            "comment": "python script open",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }
        result: OrderSendResult = self.terminal.order_send(r)
        if result is None:
            logger.critical("Unidentified error, server result is None")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise exceptions.ServerStatusError(result.retcode)
        ticket = result.order
        logger.info(f"Order was successfully send with ticket {ticket}. Order params:\n {r}")
        return ticket



