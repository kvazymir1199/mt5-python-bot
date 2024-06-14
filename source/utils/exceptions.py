from . import server_status_code

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



class ServerStatusError(Exception):
    def __init__(self,status_code):
        super().__init__(f"An error has occurred when expert was trying open a position: \n"
                         f"Error number: {status_code}\n"
                         f"Error description: {server_status_code.SERVER_STATUS_CODE.get(status_code)}\n")
        self.status_code = status_code