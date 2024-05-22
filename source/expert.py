from typing import Callable
from functools import wraps
import MetaTrader5 as mt5
from MetaTrader5 import AccountInfo, SymbolInfo, OrderSendResult
from pydantic import ValidationError
from utils.logger_config import logger
from pathlib import Path
import csv
from signals import SeasonalSignal, ShortTermSignal, BreakoutSignal, ResponseOpen
import time
from signals import OrderDirection, StoplossType, ResponseClose, Status


import os
from dotenv import load_dotenv



# Загрузите переменные окружения из файла .env
load_dotenv(
    dotenv_path=os.path.join(
        os.path.dirname(os.path.dirname(__file__)),'config', '.env'
                             )
)

print(os.getenv("MY_KEY"))


def on_timer(timer_seconds: int):
    def function(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_check_time = time.time()
            func(*args, **kwargs)
            while True:
                current_time = time.time()

                if current_time - last_check_time > timer_seconds:
                    print("".join(["==_==" for _ in range(10)]))
                    #print(f"{args=} | {kwargs=}")
                    logger.info("Вызов функции on_timer")
                    func(*args, **kwargs)
                    print("".join(["==_==" for _ in range(10)]))
                    last_check_time = time.time()

        return wrapper

    return function

#

class Expert:
    """
           Class expert represent a expert class like in mql5
           Include OnTick(), OnInit(), OnDeinit(),OnTimer() functions

    """


    def __init__(self):
        """
        Imitate OnInit function

        Function takes
        :param con:
        """

        self.terminal = mt5
        self.signals: list[SeasonalSignal, ShortTermSignal, BreakoutSignal] = []


    def __enter__(self):

        self.path = os.getenv("TERMINAL_PATH")
        if not self.terminal.initialize(path=self.path):
            print("initialize() failed, error code =", mt5.last_error())
            quit()
        self.csv_file: Path = Path(__file__).parent.parent / "files" / f"{os.getenv("FILE_NAME")}.csv"
        self.parse_signal_data()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminal.shutdown()

    def __del__(self):
        pass

    def parse_signal_data(self):
        """
        Parse data from csv file and convert to Signal
        :return:
        """
        header = ['Magic Number;Month;Symbol;Entry;TP;SL;SL Type;Risk;Direction;Type;Open Time;Close Time']

        print(f"CSV file path: {self.csv_file}")
        try:
            with self.csv_file.open("r", newline="") as file:
                reader = csv.DictReader(file, delimiter=";")
                for row in reader:
                    try:
                        signal = self.create_signal(row)
                        self.signals.append(signal)
                    except ValidationError as e:
                        print(f"Validation error for row {row}: {e}")
        except FileNotFoundError:
            print(f"File {self.csv_file} not found.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def create_signal(self, data: dict):
        signal_type = data.get("Type")
        if signal_type == "Seasonal":
            signal = SeasonalSignal
        elif signal_type == "Short-term":
            signal = ShortTermSignal
        else:
            signal = BreakoutSignal

        return signal(
            magic=int(data['Magic Number']),
            month=int(data['Month']),
            symbol=data['Symbol'],
            entry=data['Entry'],
            tp=data['TP'],
            sl=float(data['SL']),
            sl_type=(StoplossType.percentage, StoplossType.points)[data['SL Type'] == "Points"],
            risk=float(data['Risk']),
            direction=(OrderDirection.short, OrderDirection.long)[data['Direction'] == "Short"],
            open_time=data['Open Time'] if data['Open Time'] else None,
            close_time=data['Close Time'] if data['Close Time'] else None
        )

    def find_filling_mode(self, symbol):
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


    @on_timer(5)
    def main(self):
        for signal in self.signals:
            if isinstance(signal, SeasonalSignal):
                print(f"{signal.__class__.__name__} time: {signal.open_time_d}")
                print(f"{signal.__class__.__name__} end time: {signal.close_time_d}")
                request: ResponseClose = signal.get_request(self.terminal)
                print(f"{request= }")

                if isinstance(request, ResponseOpen):
                    signal.ticket = self.send_request(request)
                    if signal.ticket is not None:
                        signal.status = Status.open
                elif isinstance(request, ResponseClose):
                    if not self.terminal.Close(symbol=request.symbol, ticket=request.ticket):
                        signal.status = Status.close



    def send_request(self, request: ResponseOpen) -> int | None:
        filling_type = self.find_filling_mode(request.symbol)
        r = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.volume,
            "type": mt5.ORDER_TYPE_BUY,
            "price": request.price,
            "sl":request.sl,
            "deviation": request.deviation,
            "magic": 234000,
            "comment": "python script open",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }
        result: OrderSendResult = self.terminal.order_send(r)
        ticket = result.order
        #print(f"ticket open position {result= }")
        print("1. order_send(): by {} {} lots at {} with deviation={} points".format(
            request.symbol, request.volume, request.price, request.deviation))
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return None
        return ticket
