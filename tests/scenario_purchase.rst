=================
Purchase Scenario
=================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()

Install purchase_discount Module::

    >>> config = activate_modules('purchase_discount')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')

Create purchase user::

    >>> purchase_user = User()
    >>> purchase_user.name = 'purchase'
    >>> purchase_user.login = 'purchase'
    >>> purchase_user.main_company = company
    >>> purchase_group, = Group.find([('name', '=', 'Purchase')])
    >>> purchase_user.groups.append(purchase_group)
    >>> purchase_user.save()

Create stock user::

    >>> stock_user = User()
    >>> stock_user.name = 'Stock'
    >>> stock_user.login = 'stock'
    >>> stock_user.main_company = company
    >>> stock_group, = Group.find([('name', '=', 'Stock')])
    >>> stock_user.groups.append(stock_group)
    >>> stock_user.save()

Create account user::

    >>> account_user = User()
    >>> account_user.name = 'Account'
    >>> account_user.login = 'account'
    >>> account_user.main_company = company
    >>> account_group, = Group.find([('name', '=', 'Account')])
    >>> account_user.groups.append(account_group)
    >>> account_user.save()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create account category::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.list_price = Decimal('10')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_category = account_category
    >>> product, = template.products
    >>> product.cost_price = Decimal('5')
    >>> template.save()
    >>> product, = template.products

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create an Inventory::

    >>> config.user = stock_user.id
    >>> Inventory = Model.get('stock.inventory')
    >>> InventoryLine = Model.get('stock.inventory.line')
    >>> Location = Model.get('stock.location')
    >>> storage, = Location.find([
    ...         ('code', '=', 'STO'),
    ...         ])
    >>> inventory = Inventory()
    >>> inventory.location = storage
    >>> inventory.save()
    >>> inventory_line = InventoryLine(product=product, inventory=inventory)
    >>> inventory_line.quantity = 100.0
    >>> inventory_line.expected_quantity = 0.0
    >>> inventory.save()
    >>> inventory_line.save()
    >>> Inventory.confirm([inventory.id], config.context)
    >>> inventory.state
    'done'

Purchase 5 products testing several on_change calls and avoiding division by zero::

    >>> config.user = purchase_user.id
    >>> Purchase = Model.get('purchase.purchase')
    >>> purchase = Purchase()
    >>> purchase.party = customer
    >>> purchase.payment_term = payment_term
    >>> purchase.invoice_method = 'order'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 1.0
    >>> purchase_line.discount = Decimal('1')
    >>> purchase_line.amount
    Decimal('0.00')
    >>> purchase_line.discount = Decimal('0.12')
    >>> purchase_line.amount
    Decimal('4.40')
    >>> purchase_line.quantity = 2.0
    >>> purchase_line.amount
    Decimal('10.00')
    >>> purchase_line.discount = Decimal('0.12')
    >>> purchase_line.amount
    Decimal('8.80')
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.type = 'comment'
    >>> purchase_line.description = 'Comment'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 3.0
    >>> purchase_line.amount
    Decimal('15.00')
    >>> purchase.untaxed_amount
    Decimal('23.80')
    >>> purchase.save()
    >>> purchase_line_w_discount = purchase.lines[0]
    >>> purchase_line_w_discount.amount
    Decimal('8.80')
    >>> purchase_line_wo_discount = purchase.lines[2]
    >>> purchase_line_wo_discount.amount
    Decimal('15.00')

Process purchase::

    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'
    >>> purchase.reload()
    >>> invoice, = purchase.invoices
    >>> invoice.origins == purchase.rec_name
    True
    >>> invoice.untaxed_amount
    Decimal('23.80')

Check invoice discounts::

    >>> purchase_line_w_discount.reload()
    >>> invoice_line_w_discount, = purchase_line_w_discount.invoice_lines
    >>> invoice_line_w_discount.gross_unit_price
    Decimal('5.0000')
    >>> invoice_line_w_discount.discount
    Decimal('0.12')
    >>> invoice_line_w_discount.amount
    Decimal('8.80')
    >>> purchase_line_wo_discount.reload()
    >>> invoice_line_wo_discount, = purchase_line_wo_discount.invoice_lines
    >>> invoice_line_wo_discount.gross_unit_price
    Decimal('5.0000')
    >>> invoice_line_wo_discount.discount
    Decimal('0')
    >>> invoice_line_wo_discount.amount
    Decimal('15.00')
