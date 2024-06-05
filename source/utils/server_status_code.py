errors = """
10004 TRADE_RETCODE_REQUOTE Реквота
10006 TRADE_RETCODE_REJECT Запрос отклонен
10007 TRADE_RETCODE_CANCEL Запрос отменен трейдером
10008 TRADE_RETCODE_PLACED Ордер размещен
10009 TRADE_RETCODE_DONE Заявка выполнена
10010 TRADE_RETCODE_DONE_PARTIAL Заявка выполнена частично
10011 TRADE_RETCODE_ERROR Ошибка обработки запроса
10012 TRADE_RETCODE_TIMEOUT Запрос отменен по истечению времени
10013 TRADE_RETCODE_INVALID Неправильный запрос
10014 TRADE_RETCODE_INVALID_VOLUME Неправильный объем в запросе
10015 TRADE_RETCODE_INVALID_PRICE Неправильная цена в запросе
10016 TRADE_RETCODE_INVALID_STOPS Неправильные стопы в запросе
10017 TRADE_RETCODE_TRADE_DISABLED Торговля запрещена
10018 TRADE_RETCODE_MARKET_CLOSED Рынок закрыт
10019 TRADE_RETCODE_NO_MONEY Нет достаточных денежных средств для выполнения запроса
10020 TRADE_RETCODE_PRICE_CHANGED Цены изменились
10021 TRADE_RETCODE_PRICE_OFF Отсутствуют котировки для обработки запроса
10022 TRADE_RETCODE_INVALID_EXPIRATION Неверная дата истечения ордера в запросе
10023 TRADE_RETCODE_ORDER_CHANGED Состояние ордера изменилось
10024 TRADE_RETCODE_TOO_MANY_REQUESTS Слишком частые запросы
10025 TRADE_RETCODE_NO_CHANGES В запросе нет изменений
10026 TRADE_RETCODE_SERVER_DISABLES_AT Автотрейдинг запрещен сервером
10027 TRADE_RETCODE_CLIENT_DISABLES_AT Автотрейдинг запрещен клиентским терминалом
10028 TRADE_RETCODE_LOCKED Запрос заблокирован для обработки
10029 TRADE_RETCODE_FROZEN Ордер или позиция заморожены
10030 TRADE_RETCODE_INVALID_FILL Указан неподдерживаемый тип исполнения ордера по остатку
10031 TRADE_RETCODE_CONNECTION Нет соединения с торговым сервером
10032 TRADE_RETCODE_ONLY_REAL Операция разрешена только для реальных счетов
10033 TRADE_RETCODE_LIMIT_ORDERS Достигнут лимит на количество отложенных ордеров
10034 TRADE_RETCODE_LIMIT_VOLUME Достигнут лимит на объем ордеров и позиций для данного символа
10035 TRADE_RETCODE_INVALID_ORDER Неверный или запрещённый тип ордера
10036 TRADE_RETCODE_POSITION_CLOSED Позиция с указанным POSITION_IDENTIFIER уже закрыта
10038 TRADE_RETCODE_INVALID_CLOSE_VOLUME Закрываемый объем превышает текущий объем позиции
10039 TRADE_RETCODE_CLOSE_ORDER_EXIST Для указанной позиции уже есть ордер на закрытие. Может возникнуть при работе в системе хеджинга:при попытке закрытия позиции встречной, если уже есть ордера на закрытие этой позициипри попытке полного или частичного закрытия, если суммарный объем уже имеющихся ордеров на закрытие и вновь выставляемого ордера превышает текущий объем позиции
10040 TRADE_RETCODE_LIMIT_POSITIONS Количество открытых позиций, которое можно одновременно иметь на счете, может быть ограничено настройками сервера. При достижении лимита в ответ на выставление ордера сервер вернет ошибку TRADE_RETCODE_LIMIT_POSITIONS. Ограничение работает по-разному в зависимости от типа учета позиций на счете:Неттинговая система — учитывается количество открытых позиции. При достижении лимита платформа не позволит выставлять новые ордера, в результате исполнения которых может увеличиться количество открытых позиций. Фактически, платформа позволит выставлять ордера только по тем символам, по которым уже есть открытые позиции. В неттинговой системе при проверке лимита не учитываются текущие отложенные ордера, поскольку их исполнение может привести к изменению текущих позиций, а не увеличению их количества.Хеджинговая система — помимо открытых позиций, учитываются выставленные отложенные ордера, поскольку их срабатывание всегда приводит к открытию новой позиции. При достижении лимита платформа не позволит выставлять рыночные ордера на открытие позиций, а также отложенные ордера.
10041 TRADE_RETCODE_REJECT_CANCEL Запрос на активацию отложенного ордера отклонен, а сам ордер отменен
10042 TRADE_RETCODE_LONG_ONLY Запрос отклонен, так как на символе установлено правило "Разрешены только длинные позиции" (POSITION_TYPE_BUY)
10043 TRADE_RETCODE_SHORT_ONLY Запрос отклонен, так как на символе установлено правило "Разрешены только короткие позиции" (POSITION_TYPE_SELL)
10044 TRADE_RETCODE_CLOSE_ONLY Запрос отклонен, так как на символе установлено правило "Разрешено только закрывать существующие позиции"
10045 TRADE_RETCODE_FIFO_CLOSE Запрос отклонен, так как для торгового счета установлено правило "Разрешено закрывать существующие позиции только по правилу FIFO" (ACCOUNT_FIFO_CLOSE=true)
10046 TRADE_RETCODE_HEDGE_PROHIBITED Запрос отклонен, так как для торгового счета установлено правило "Запрещено открывать встречные позиции по одному символу". Например, если на счете имеется позиция Buy, то пользователь не может открыть позицию Sell или выставить отложенный ордер на продажу. Правило может применяться только на счетах с хеджинговой системой учета (ACCOUNT_MARGIN_MODE=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING).
"""


def parse_errors():
    error_dict = {}
    lines = errors.strip().split("\n")
    for line in lines:
        parts = line.split(" ", maxsplit=2)
        error_code = int(parts[0])
        error_description = parts[2]
        error_dict[error_code] = error_description
    return error_dict


# Вывод словаря
SERVER_STATUS_CODE = parse_errors()