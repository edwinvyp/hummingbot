from decimal import Decimal, InvalidOperation
from typing import Optional

from hummingbot.core.event.events import OrderFilledEvent, TradeType
from hummingbot.model.inventory_cost import InventoryCost
from hummingbot.model.sql_connection_manager import SQLConnectionManager

s_decimal_0 = Decimal("0")


class InventoryCostPriceDelegate:
    def __init__(self, sql: SQLConnectionManager, trading_pair: str) -> None:
        self.base_asset, self.quote_asset = trading_pair.split("-")
        self._session = sql.get_shared_session()

    @property
    def ready(self) -> bool:
        return True

    def get_price(self) -> Optional[Decimal]:
        record = InventoryCost.get_record(
            self._session, self.base_asset, self.quote_asset
        )

        if record is None or record.base_volume is None or record.base_volume is None:
            return None

        try:
            price = record.quote_volume / record.base_volume
        except InvalidOperation:
            # use both volume = 0
            return None
        return Decimal(price)

    def process_order_fill_event(self, fill_event: OrderFilledEvent) -> None:
        base_asset, quote_asset = fill_event.trading_pair.split("-")
        quote_volume = fill_event.amount * fill_event.price
        base_volume = fill_event.amount

        for fee_asset, fee_amount in fill_event.trade_fee.flat_fees:
            if fill_event.trade_type == TradeType.BUY:
                if fee_asset == base_asset:
                    base_volume -= fee_amount
                elif fee_asset == quote_asset:
                    quote_volume += fee_amount
                else:
                    # used for exchange native token used as base fee .
                    base_volume /= 1 + fill_event.trade_fee.percent
            else:
                if fee_asset == base_asset:
                    base_volume += fee_amount
                elif fee_asset == quote_asset:
                    # volume adjustment with new logic.
                    quote_volume -= fee_amount
                else:
                    base_volume /= 1 + fill_event.trade_fee.percent

        if fill_event.trade_type == TradeType.SELL:
            record = InventoryCost.get_record(self._session, base_asset, quote_asset)
            if not record:
                raise RuntimeError("Sold asset without having inventory price set. This should not happen.")

            #  keeping initial buy price intact. Profits are not changing inventory price intentionally.
            quote_volume = -(Decimal(record.quote_volume / record.base_volume) * base_volume)
            base_volume = -base_volume

        InventoryCost.add_volume(
            self._session, base_asset, quote_asset, base_volume, quote_volume
        )

