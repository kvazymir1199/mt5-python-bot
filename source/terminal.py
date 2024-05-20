import MetaTrader5 as mt5
from MetaTrader5 import SymbolInfo
from signals import SeasonalSignal,ShortTermSignal,BreakoutSignal


class Terminal:
    path = 'C:\\Program Files\\Admiral Markets MT5\\terminal64.exe'
    def __init__(self):
        self.terminal = mt5


    def __enter__(self):
        if not self.terminal.initialize(path=self.path):
            print("initialize() failed, error code =", mt5.last_error())
            quit()
        return self

    def on_tick(self):
        ...

    def account(self):
        return self.terminal.account_info()

    def find_filling_mode(self,symbol):
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


    def buy(self,signal:SeasonalSignal):
        print(signal.symbol)
        symbol = signal.symbol
        filling_type = self.find_filling_mode(symbol)
        symbol_info: SymbolInfo = self.terminal.symbol_info(symbol).ask
        lot = 0.1
        point = mt5.symbol_info(symbol).point
        price = mt5.symbol_info_tick(symbol).ask
        deviation = 20
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": price - 100 * point,
            "tp": price + 100 * point,
            "deviation": deviation,
            "magic": 234000,
            "comment": "python script open",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }
        result = self.terminal.order_send(request)
        print("1. order_send(): by {} {} lots at {} with deviation={} points".format("EURUSD", lot, price, deviation));
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print("2. order_send failed, retcode={}".format(result.retcode))
            # запросим результат в виде словаря и выведем поэлементно
            result_dict = result._asdict()
            for field in result_dict.keys():
                print("   {}={}".format(field, result_dict[field]))
                # если это структура торгового запроса, то выведем её тоже поэлементно
                if field == "request":
                    traderequest_dict = result_dict[field]._asdict()
                    for tradereq_filed in traderequest_dict:
                        print("       traderequest: {}={}".format(tradereq_filed, traderequest_dict[tradereq_filed]))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminal.shutdown()
