from django.test import TestCase
from django.core.exceptions import ValidationError
from store.models import DispensaryLocker, LockerInventory, DispenseRecord, Unit, Drug, Category, User

class DispensaryLockerTestCase(TestCase):

    def setUp(self):
        self.unit = Unit.objects.create(name="Test Unit")
        self.dispensary_locker = DispensaryLocker.objects.create(unit=self.unit, name="Test Dispensary Locker")

    def test_str(self):
        self.assertEqual(str(self.dispensary_locker), f"{self.unit.name} {self.dispensary_locker.name}")

    def test_one_to_one_relation(self):
        self.assertEqual(self.dispensary_locker.unit, self.unit)
        self.assertEqual(self.unit.dispensary_locker, self.dispensary_locker)

class LockerInventoryTestCase(TestCase):

    def setUp(self):
        self.unit = Unit.objects.create(name="Test Unit")
        self.dispensary_locker = DispensaryLocker.objects.create(unit=self.unit, name="Test Dispensary Locker")
        self.drug = Drug.objects.create(name="Test Drug")
        self.locker_inventory = LockerInventory.objects.create(locker=self.dispensary_locker, drug=self.drug, quantity=100)

    def test_str(self):
        self.assertEqual(str(self.locker_inventory), f"{self.drug} in {self.dispensary_locker}")

    def test_unique_together(self):
        with self.assertRaises(IntegrityError):
            LockerInventory.objects.create(locker=self.dispensary_locker, drug=self.drug, quantity=50)

class DispenseRecordTestCase(TestCase):

    def setUp(self):
        self.unit = Unit.objects.create(name="Test Unit")
        self.dispensary_locker = DispensaryLocker.objects.create(unit=self.unit, name="Test Dispensary Locker")
        self.drug = Drug.objects.create(name="Test Drug")
        self.locker_inventory = LockerInventory.objects.create(locker=self.dispensary_locker, drug=self.drug, quantity=100)
        self.category = Category.objects.create(name="Test Category")
        self.user = User.objects.create_user(username="testuser", password="testpassword")

    def test_save(self):
        dispense_record = DispenseRecord(
            dispensary=self.dispensary_locker,
            category=self.category,
            drug=self.drug,
            quantity=10,
            patient_info="Test Patient",
            dispensed_by=self.user
        )
        dispense_record.save()
        self.assertEqual(self.locker_inventory.quantity, 90)
        self.assertEqual(dispense_record.balance_quantity, 90)

    def test_clean(self):
        dispense_record = DispenseRecord(
            dispensary=self.dispensary_locker,
            category=self.category,
            drug=self.drug,
            quantity=110,  # More than available
            patient_info="Test Patient",
            dispensed_by=self.user
        )
        with self.assertRaises(ValidationError):
            dispense_record.save()

    def test_invalid_quantity(self):
        dispense_record = DispenseRecord(
            dispensary=self.dispensary_locker,
            category=self.category,
            drug=self.drug,
            quantity=-10,  # Negative quantity
            patient_info="Test Patient",
            dispensed_by=self.user
        )
        with self.assertRaises(ValidationError):
            dispense_record.save()

    def test_null_quantity(self):
        dispense_record = DispenseRecord(
            dispensary=self.dispensary_locker,
            category=self.category,
            drug=self.drug,
            quantity=None,  # Null quantity
            patient_info="Test Patient",
            dispensed_by=self.user
        )
        with self.assertRaises(ValidationError):
            dispense_record.save()
