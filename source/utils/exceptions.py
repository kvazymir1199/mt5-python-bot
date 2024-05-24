class SignalSymbolNotFoundError(Exception):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(f"Symbol: {self.symbol} not found in Broker symbols. Check symbol field in csv file")


class SignalTimeStartFormatError(Exception):

    def __init__(self, time):
        self.time = time
        super().__init__(f"Signal start time {self.time} have wrong format it must be xx:xx.Check entry field in csv file")


class SignalTimeEndFormatError(Exception):
    def __init__(self, time):
        super().__init__(f"Signal end time {time} have wrong format it must be xx:xx.Check entry field in csv file")



