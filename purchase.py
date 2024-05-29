# This file is part of purchase_discount module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.modules.currency.fields import Monetary
from trytond.modules.account_invoice_discount.invoice import (gross_unit_price_digits,
    discount_digits)
from trytond.modules.product import round_price

STATES = {
    'invisible': Eval('type') != 'line',
    'required': Eval('type') == 'line',
    'readonly': Eval('purchase_state') != 'draft',
    }


class PurchaseLine(metaclass=PoolMeta):
    __name__ = 'purchase.line'

    gross_unit_price = Monetary('Gross Price', digits=gross_unit_price_digits,
        currency='currency', states=STATES)
    discount = fields.Numeric('Discount', digits=discount_digits,
        states=STATES)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.unit_price.states['readonly'] = True

    @staticmethod
    def default_discount():
        return Decimal(0)

    @fields.depends('gross_unit_price', 'unit_price', 'discount',
        methods=['on_change_with_amount'])
    def update_prices(self):
        unit_price = None
        gross_unit_price = self.gross_unit_price
        if self.gross_unit_price is not None and self.discount is not None:
            unit_price = self.gross_unit_price * (1 - self.discount)
            unit_price = round_price(unit_price)

            if self.discount != 1:
                gross_unit_price = unit_price / (1 - self.discount)

            gup_digits = self.__class__.gross_unit_price.digits[1]
            gross_unit_price = gross_unit_price.quantize(
                Decimal(str(10.0 ** -gup_digits)))

        self.gross_unit_price = gross_unit_price
        self.unit_price = unit_price
        self.amount = self.on_change_with_amount()

    @fields.depends('discount')
    def on_change_unit(self):
        super().on_change_unit()

    @fields.depends(methods=['update_prices'])
    def on_change_gross_unit_price(self):
        return self.update_prices()

    @fields.depends('unit_price', methods=['update_prices'])
    def on_change_unit_price(self):
        # unit_price has readonly state but could set unit_price from source code
        if self.unit_price is not None:
            self.update_prices()

    @fields.depends(methods=['update_prices'])
    def on_change_discount(self):
        return self.update_prices()

    @fields.depends('unit_price', 'discount', methods=['update_prices'])
    def on_change_product(self):
        super().on_change_product()
        self.gross_unit_price = self.unit_price
        if not self.discount:
            self.discount = Decimal(0)

        if self.unit_price is not None:
            self.update_prices()

    @fields.depends('unit_price', 'discount', methods=['update_prices'])
    def on_change_quantity(self):
        super().on_change_quantity()
        self.gross_unit_price = self.unit_price
        if not self.discount:
            self.discount = Decimal(0)

        if self.unit_price is not None:
            self.update_prices()

    def get_invoice_line(self):
        lines = super().get_invoice_line()
        for line in lines:
            line.gross_unit_price = self.gross_unit_price
            line.discount = self.discount
        return lines

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for vals in vlist:
            if vals.get('type', 'line') != 'line':
                continue
            gross_unit_price = (vals.get('unit_price', Decimal(0))
                or Decimal(0))
            if 'discount' in vals and vals['discount'] != 1:
                gross_unit_price = gross_unit_price / (1 - vals['discount'])
            vals['gross_unit_price'] = round_price(gross_unit_price)
            if not vals.get('discount'):
                vals['discount'] = Decimal(0)
        return super().create(vlist)
