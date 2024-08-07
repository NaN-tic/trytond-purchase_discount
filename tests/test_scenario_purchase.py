import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install purchase_discount Module
        config = activate_modules('purchase_discount')

        # Create company
        _ = create_company()
        company = get_company()

        # Reload the context
        User = Model.get('res.user')
        Group = Model.get('res.group')

        # Create purchase user
        purchase_user = User()
        purchase_user.name = 'purchase'
        purchase_user.login = 'purchase'
        purchase_group, = Group.find([('name', '=', 'Purchase')])
        purchase_user.groups.append(purchase_group)
        purchase_user.save()

        # Create stock user
        stock_user = User()
        stock_user.name = 'Stock'
        stock_user.login = 'stock'
        stock_group, = Group.find([('name', '=', 'Stock')])
        stock_user.groups.append(stock_group)
        stock_user.save()

        # Create account user
        account_user = User()
        account_user.name = 'Account'
        account_user.login = 'account'
        account_group, = Group.find([('name', '=', 'Account')])
        account_user.groups.append(account_group)
        account_user.save()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.save()
        customer = Party(name='Customer')
        customer.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        product = Product()
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.purchasable = True
        template.list_price = Decimal('10')
        template.cost_price_method = 'fixed'
        template.account_category = account_category
        product, = template.products
        product.cost_price = Decimal('5')
        template.save()
        product, = template.products

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create an Inventory
        config.user = stock_user.id
        Inventory = Model.get('stock.inventory')
        InventoryLine = Model.get('stock.inventory.line')
        Location = Model.get('stock.location')
        storage, = Location.find([
            ('code', '=', 'STO'),
        ])
        inventory = Inventory()
        inventory.location = storage
        inventory.save()
        inventory_line = InventoryLine(product=product, inventory=inventory)
        inventory_line.quantity = 100.0
        inventory_line.expected_quantity = 0.0
        inventory.save()
        inventory_line.save()
        Inventory.confirm([inventory.id], config.context)
        self.assertEqual(inventory.state, 'done')

        # Purchase 5 products testing several on_change calls and avoiding division by zero
        config.user = purchase_user.id
        Purchase = Model.get('purchase.purchase')
        purchase = Purchase()
        purchase.party = customer
        purchase.payment_term = payment_term
        purchase.invoice_method = 'order'
        purchase_line = purchase.lines.new()
        purchase_line.product = product
        self.assertEqual(purchase_line.gross_unit_price, Decimal('5.0000'))
        self.assertEqual(purchase_line.unit_price, Decimal('5.00000000'))
        purchase_line.quantity = 1.0
        purchase_line.discount = Decimal('1')
        self.assertEqual(purchase_line.unit_price, Decimal('0.00'))
        purchase_line.discount = Decimal('0.12')
        self.assertEqual(purchase_line.unit_price, Decimal('4.40'))
        purchase_line.unit = product.purchase_uom
        purchase_line.quantity = 2.0
        self.assertEqual(purchase_line.unit_price, Decimal('4.40'))
        purchase_line = purchase.lines.new()
        purchase_line.type = 'comment'
        purchase_line.description = 'Comment'
        purchase_line = purchase.lines.new()
        purchase_line.product = product
        purchase_line.quantity = 3.0
        self.assertEqual(purchase_line.unit_price, Decimal('5.00000000'))
        purchase.save()
        line1, line2, line3 = purchase.lines
        self.assertEqual(line1.amount, Decimal('8.80'))
        self.assertEqual(line1.discount, Decimal('0.12'))
        self.assertEqual(line2.amount, Decimal('0.00'))
        self.assertEqual(line3.amount, Decimal('15.00'))
        self.assertEqual(line3.discount, Decimal('0.00'))

        # Process purchase
        purchase.click('quote')
        purchase.click('confirm')
        self.assertEqual(purchase.state, 'processing')
        purchase.reload()
        invoice, = purchase.invoices
        self.assertEqual(invoice.origins, purchase.rec_name)
        self.assertEqual(invoice.untaxed_amount, Decimal('23.80'))

        # Check invoice discounts
        line1, line2, line3 = invoice.lines
        self.assertEqual(line1.gross_unit_price, Decimal('5.0000'))
        self.assertEqual(line1.discount, Decimal('0.12'))
        self.assertEqual(line1.amount, Decimal('8.80'))
        self.assertEqual(line2.gross_unit_price, None)
        self.assertEqual(line2.discount, Decimal('0.00'))
        self.assertEqual(line3.gross_unit_price, Decimal('5.0000'))
        self.assertEqual(line3.discount, Decimal('0.00'))
        self.assertEqual(line3.amount, Decimal('15.00'))
