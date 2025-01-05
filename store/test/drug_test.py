from django.test import TestCase
from django.contrib.auth.models import User
from datetime import date, timedelta
from store.models import Drug, Category

class DrugModelTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name="Antibiotics")
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.drug = Drug.objects.create(
            generic_name="Amoxicillin",
            trade_name="Amoxil",
            category=self.category,
            supplier="Supplier A",
            dosage_form="TABLET",
            pack_size=10,
            cost_price=100.00,
            selling_price=150.00,
            total_purchased_quantity=100,
            expiration_date=date.today() + timedelta(days=365),
            added_by=self.user
        )

    def test_piece_unit_cost_price(self):
        self.assertEqual(self.drug.piece_unit_cost_price, 10.00)

    def test_piece_unit_selling_price(self):
        self.assertEqual(self.drug.piece_unit_selling_price, 15.00)

    def test_total_store_quantity(self):
        self.assertEqual(Drug.total_store_quantity(), 100)

    def test_total_value(self):
        self.assertEqual(self.drug.total_value, 10000.00)

    def test_total_store_value(self):
        self.assertEqual(Drug.total_store_value(), 10000.00)

    def test_total_issued(self):
        self.assertEqual(self.drug.total_issued, 0)

    def test_current_balance(self):
        self.assertEqual(self.drug.current_balance, 100)

    def test_total_items_purchased(self):
        self.assertEqual(self.drug.total_items_purchased, 1000)

    def test_total_items_issued(self):
        self.assertEqual(self.drug.total_items_issued, 0)

    def test_items_in_stock(self):
        self.assertEqual(self.drug.items_in_stock, 0)

    def test_entered_expiry_period(self):
        self.drug.expiration_date = date.today() + timedelta(days=179)
        self.drug.save()
        self.assertIsNotNone(self.drug.entered_expiry_period)