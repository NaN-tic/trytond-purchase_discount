# This file is part purchase_discount module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.modules.company.tests import CompanyTestMixin
from trytond.tests.test_tryton import ModuleTestCase


class PurchaseDiscountTestCase(CompanyTestMixin, ModuleTestCase):
    'Test Purchase Discount module'
    module = 'purchase_discount'


del ModuleTestCase
