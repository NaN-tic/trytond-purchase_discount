from decimal import Decimal
import unittest
from proteus import Model
from trytond.modules.company.tests.tools import create_company
from trytond.tests.tools import activate_modules
from trytond.tests.test_tryton import drop_db


class Test(unittest.TestCase):
    def setUp(self):
        drop_db()
        super().setUp()
        
    def tearDown(self):
        drop_db()
        super().tearDown()

    def test_purchase_discount(self):
        activate_modules('purchase_discount')
        
        create_company()
        
        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name="Supplier")
        supplier.save()
        
        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.purchasable = True
        product_supplier = template.product_suppliers.new(party=supplier)
        product_supplier.prices.new(quantity=1, unit_price=Decimal('10'))
        template.save()
        product, = template.products
        
        # Create a purchase
        Purchase = Model.get('purchase.purchase')
        purchase = Purchase()
        purchase.party = supplier
        line = purchase.lines.new()
        line.product = product
        line.quantity = 1
        self.assertEqual(line.base_price, Decimal('10.0000'))
        self.assertEqual(line.unit_price, Decimal('10.0000'))
        
        # Set a discount of 10%
        line.discount_rate = Decimal('0.1')
        self.assertEqual(line.unit_price, Decimal('9.0000'))
        self.assertEqual(line.discount_amount, Decimal('1.0000'))
        self.assertEqual(line.discount, '10%')
    
        purchase.save()
        line, = purchase.lines
        self.assertEqual(line.unit_price, Decimal('9.0000'))
        self.assertEqual(line.discount_amount, Decimal('1.0000'))
        self.assertEqual(line.discount, '10%')
        
        # Set a discount amount
        line.discount_amount = Decimal('3.3333')
        self.assertEqual(line.unit_price, Decimal('6.6667'))
        self.assertEqual(line.discount_rate, Decimal('0.3333'))
        self.assertEqual(line.discount, '$3.3333')

