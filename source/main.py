import MetaTrader5 as mt5
from MetaTrader5 import AccountInfo
from terminal import Terminal
from expert import Expert
with Terminal() as terminal:
    account_info: AccountInfo = terminal.account()
    expert = Expert(con=terminal)
    expert.main()


