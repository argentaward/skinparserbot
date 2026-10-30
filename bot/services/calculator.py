from dataclasses import dataclass

@dataclass
class CalculationResult:
    buy_price: float
    sell_price: float
    deposit_fee_percent: float
    sale_fee_percent: float
    withdraw_fee_percent: float
    
    real_cost: float
    balance_after_sale: float
    net_payout: float
    net_profit: float
    roi: float

def calculate_arbitrage(
    buy_price: float,
    sell_price: float,
    deposit_fee_percent: float = 0.0,
    sale_fee_percent: float = 5.0,
    withdraw_fee_percent: float = 3.0,
) -> CalculationResult:
    """
    Расчет экономики круга:
    - Реальные затраты = Цена покупки * (1 + Комиссия пополнения / 100)
    - Баланс после продажи = Цена продажи * (1 - Комиссия продажи / 100)
    - Чистый вывод = Баланс после продажи * (1 - Комиссия на вывод / 100)
    - Чистый профит = Чистый вывод - Реальные затраты
    - ROI = (Чистый профит / Реальные затраты) * 100%
    """
    dep_rate = deposit_fee_percent / 100.0
    sale_rate = sale_fee_percent / 100.0
    with_rate = withdraw_fee_percent / 100.0

    real_cost = buy_price * (1.0 + dep_rate)
    balance_after_sale = sell_price * (1.0 - sale_rate)
    net_payout = balance_after_sale * (1.0 - with_rate)
    net_profit = net_payout - real_cost
    
    roi = (net_profit / real_cost * 100.0) if real_cost > 0 else 0.0

    return CalculationResult(
        buy_price=round(buy_price, 2),
        sell_price=round(sell_price, 2),
        deposit_fee_percent=deposit_fee_percent,
        sale_fee_percent=sale_fee_percent,
        withdraw_fee_percent=withdraw_fee_percent,
        real_cost=round(real_cost, 2),
        balance_after_sale=round(balance_after_sale, 2),
        net_payout=round(net_payout, 2),
        net_profit=round(net_profit, 2),
        roi=round(roi, 2)
    )
