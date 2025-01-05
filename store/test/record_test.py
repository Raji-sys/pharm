from django.test import TestCase
from django.contrib.auth.models import User
from store.models import Unit, Category, Drug, Record, UnitStore

class RecordModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.unit = Unit.objects.create(name='Test Unit')
        self.category = Category.objects.create(name='ANTIBIOTIC')
        self.drug = Drug.objects.create(
            generic_name='Test Drug',
            category=self.category,
            pack_size=10,
            cost_price=100.00,
            total_purchased_quantity=100
        )
        self.unit_store = UnitStore.objects.create(unit=self.unit, drug=self.drug, quantity=50)

    def test_create_record(self):
        record = Record.objects.create(
            category=self.category,
            drug=self.drug,
            unit_issued_to=self.unit,
            quantity=10,
            issued_by=self.user
        )
        self.assertEqual(record.quantity, 10)
        self.assertEqual(record.unit_issued_to, self.unit)
        self.assertEqual(record.drug, self.drug)
        self.assertEqual(record.category, self.category)
        self.assertEqual(record.issued_by, self.user)

    def test_update_record(self):
        record = Record.objects.create(
            category=self.category,
            drug=self.drug,
            unit_issued_to=self.unit,
            quantity=10,
            issued_by=self.user
        )
        record.quantity = 20
        record.save()
        self.assertEqual(record.quantity, 20)

    def test_unit_store_quantity_update_on_record_creation(self):
        initial_quantity = self.unit_store.quantity
        record = Record.objects.create(
            category=self.category,
            drug=self.drug,
            unit_issued_to=self.unit,
            quantity=10,
            issued_by=self.user
        )
        self.unit_store.quantity += record.quantity
        self.unit_store.save()
        self.unit_store.refresh_from_db()
        self.assertEqual(self.unit_store.quantity, initial_quantity + 10)

    def test_unit_store_quantity_update_on_record_update(self):
        record = Record.objects.create(
            category=self.category,
            drug=self.drug,
            unit_issued_to=self.unit,
            quantity=10,
            issued_by=self.user
        )
        initial_quantity = self.unit_store.quantity
        record.quantity = 20
        record.save()
        self.unit_store.quantity += 10
        self.unit_store.save()
        self.unit_store.refresh_from_db()
        self.assertEqual(self.unit_store.quantity, initial_quantity + 10)

    def test_unit_store_quantity_update_on_record_delete(self):
        record = Record.objects.create(
            category=self.category,
            drug=self.drug,
            unit_issued_to=self.unit,
            quantity=10,
            issued_by=self.user
        )
        initial_quantity = self.unit_store.quantity
        record.delete()
        self.unit_store.quantity -= 10
        self.unit_store.save()
        self.unit_store.refresh_from_db()
        self.assertEqual(self.unit_store.quantity, initial_quantity - 10)