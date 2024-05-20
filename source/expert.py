from pprint import pprint
from typing import Callable
from functools import wraps
import MetaTrader5 as mt5
from MetaTrader5 import AccountInfo, SymbolInfo
from pydantic import ValidationError

from terminal import Terminal
from pathlib import Path
import csv
from signals import SeasonalSignal, ShortTermSignal, BreakoutSignal
import time
from signals import OrderDirection,StoplossType

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
                    print(f"{args=} | {kwargs=}")
                    func(*args, **kwargs)
                    print("".join(["==_==" for _ in range(10)]))
                    last_check_time = time.time()

        return wrapper

    return function





class Expert:
    """
           Class expert represent a expert class like in mql5
           Include OnTick(), OnInit(), OnDeinit(),OnTimer() functions

    """

    def __init__(self, con):
        """
        Imitate OnInit function

        Function takes
        :param con:
        """

        self.terminal:Terminal = con
        self.account_info: AccountInfo = self.terminal.account()
        self.csv_file: Path = Path(__file__).parent.parent / "files" / "Admiral markets Group AS.csv"
        self.signals: list[SeasonalSignal, ShortTermSignal, BreakoutSignal] = []
        self.parse_signal_data()

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

    def create_signal(self,data: dict):
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
            sl_type=(StoplossType.percentage,StoplossType.points)[data['SL Type'] == "Percentage"],
            risk=float(data['Risk']),
            direction=(OrderDirection.short, OrderDirection.long)[data['Direction'] == "Long"],
            open_time=data['Open Time'] if data['Open Time'] else None,
            close_time=data['Close Time'] if data['Close Time'] else None
        )


    @on_timer(5)
    def main(self):

        for signal in self.signals:
            if isinstance(signal, SeasonalSignal):
                print(f"{signal.__class__.__name__} time: {signal.get_start_time()}")
                print(f"{signal.__class__.__name__} end time: {signal.get_close_time()}")
                #signal.main()

                self.terminal.buy(signal)
