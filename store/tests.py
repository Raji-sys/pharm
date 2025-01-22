from django.contrib.messages import get_messages
from .models import *
from .views import *
from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User, Group
from unittest.mock import patch
from django.db import transaction

class DispenseRecordViewTests(TestCase):
    # @patch('django.contrib.auth.models.User.groups')
    # def test_normal_case(self, mock_groups):
    #     # Mock the groups.filter().exists() chain
    #     mock_groups.filter.return_value.exists.return_value = True

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Set up request factory
        self.factory = RequestFactory()
        
        # Create unit - this will automatically create a DispensaryLocker
        self.unit = Unit.objects.create(name="Test Unit")
         # Create and assign group matching unit name
        self.group = Group.objects.create(name=self.unit.name)
        self.user.groups.add(self.group)
        
        # Get the automatically created dispensary locker
        self.dispensary_locker = self.unit.dispensary_locker
        
        # Create test drugs with different pack sizes
        self.drug_normal = Drug.objects.create(
            trade_name="Normal Drug",
            pack_size=10,
            cost_price=Decimal('100.00'),
            selling_price=Decimal('150.00')
        )
        
        self.drug_zero_pack = Drug.objects.create(
            trade_name="Zero Pack Drug",
            pack_size=0,
            cost_price=Decimal('100.00'),
            selling_price=Decimal('150.00')
        )
        
        self.drug_null_pack = Drug.objects.create(
            trade_name="Null Pack Drug",
            pack_size=None,
            cost_price=Decimal('100.00'),
            selling_price=Decimal('150.00')
        )

        # Create LockerInventory entries for each drug
        LockerInventory.objects.create(
            locker=self.dispensary_locker,
            drug=self.drug_normal,
            quantity=100  # Initial quantity
        )
        LockerInventory.objects.create(
            locker=self.dispensary_locker,
            drug=self.drug_zero_pack,
            quantity=100
        )
        LockerInventory.objects.create(
            locker=self.dispensary_locker,
            drug=self.drug_null_pack,
            quantity=100
        )

    @transaction.atomic
    def test_normal_case(self):
        """Test view with normal data"""
        # Create dispense record with normal drug
        DispenseRecord.objects.create(
            drug=self.drug_normal,
            quantity=5,
            dispensary=self.dispensary_locker,
            dispensed_by=self.user
        )
        
        request = self.factory.get(reverse('dispensed_list', kwargs={'pk': self.dispensary_locker.pk}))
        request.user = self.user
        
    # Properly initialize the view
        view = DispenseRecordView.as_view()
        response = view(request, pk=self.dispensary_locker.pk)
        response.render()  # Render the response
        
        # Get the context from the response
        context = response.context_data        
        self.assertEqual(context['total_dispensed'], 1)
        self.assertEqual(context['total_quantity'], 5)
        expected_cost = Decimal('50.00')  # (5 * 100) / 10
        expected_selling = Decimal('75.00')  # (5 * 150) / 10
        self.assertEqual(context['total_cost_price'], expected_cost)
        self.assertEqual(context['total_piece_unit_selling_price'], expected_selling)
        self.assertEqual(context['total_profit'], Decimal('25.00'))
        self.assertEqual(context['percentage'], Decimal('50.00'))

    # ... rest of test methods follow the same pattern
# class DispenseRecordViewTests(TestCase):
#     def setUp(self):
#         # Create test user
#         self.user = User.objects.create_user(
#             username='testuser',
#             password='testpass123'
#         )
        
#         # Set up request factory
#         self.factory = RequestFactory()
        
#         # Create test data
#         self.dispensary_locker = DispensaryLocker.objects.create(
#             name="Test Locker",
#             unit=Unit.objects.create(name="Test Unit")
#         )
        
#         # Create test drugs with different pack sizes
#         self.drug_normal = Drug.objects.create(
#             name="Normal Drug",
#             pack_size=10,
#             cost_price=Decimal('100.00'),
#             selling_price=Decimal('150.00')
#         )
        
#         self.drug_zero_pack = Drug.objects.create(
#             name="Zero Pack Drug",
#             pack_size=0,
#             cost_price=Decimal('100.00'),
#             selling_price=Decimal('150.00')
#         )
        
#         self.drug_null_pack = Drug.objects.create(
#             name="Null Pack Drug",
#             pack_size=None,
#             cost_price=Decimal('100.00'),
#             selling_price=Decimal('150.00')
#         )

#     def test_normal_case(self):
#         """Test view with normal data"""
#         # Create dispense record with normal drug
#         DispenseRecord.objects.create(
#             drug=self.drug_normal,
#             quantity=5,
#             dispensary=self.dispensary_locker,
#             dispense_date='2024-01-23'
#         )
        
#         request = self.factory.get(reverse('dispense-record-list', kwargs={'pk': self.dispensary_locker.pk}))
#         request.user = self.user
        
#         view = DispenseRecordView()
#         view.setup(request, pk=self.dispensary_locker.pk)
#         context = view.get_context_data()
        
#         self.assertEqual(context['total_dispensed'], 1)
#         self.assertEqual(context['total_quantity'], 5)
#         # Test calculations for normal case
#         expected_cost = Decimal('50.00')  # (5 * 100) / 10
#         expected_selling = Decimal('75.00')  # (5 * 150) / 10
#         self.assertEqual(context['total_cost_price'], expected_cost)
#         self.assertEqual(context['total_piece_unit_selling_price'], expected_selling)
#         self.assertEqual(context['total_profit'], Decimal('25.00'))
#         self.assertEqual(context['percentage'], Decimal('50.00'))

#     def test_zero_pack_size(self):
#         """Test view with zero pack size drug"""
#         DispenseRecord.objects.create(
#             drug=self.drug_zero_pack,
#             quantity=5,
#             dispensary=self.dispensary_locker,
#             dispense_date='2024-01-23'
#         )
        
#         request = self.factory.get(reverse('dispense-record-list', kwargs={'pk': self.dispensary_locker.pk}))
#         request.user = self.user
        
#         view = DispenseRecordView()
#         view.setup(request, pk=self.dispensary_locker.pk)
#         context = view.get_context_data()
        
#         # Should be filtered out due to pack_size=0
#         self.assertEqual(context['total_cost_price'], Decimal('0.00'))
#         self.assertEqual(context['total_piece_unit_selling_price'], Decimal('0.00'))
#         self.assertEqual(context['total_profit'], Decimal('0.00'))
#         self.assertEqual(context['percentage'], Decimal('0.00'))

#     def test_null_pack_size(self):
#         """Test view with null pack size drug"""
#         DispenseRecord.objects.create(
#             drug=self.drug_null_pack,
#             quantity=5,
#             dispensary=self.dispensary_locker,
#             dispense_date='2024-01-23'
#         )
        
#         request = self.factory.get(reverse('dispense-record-list', kwargs={'pk': self.dispensary_locker.pk}))
#         request.user = self.user
        
#         view = DispenseRecordView()
#         view.setup(request, pk=self.dispensary_locker.pk)
#         context = view.get_context_data()
        
#         # Should use Coalesce(pack_size, 1)
#         expected_cost = Decimal('500.00')  # (5 * 100) / 1
#         expected_selling = Decimal('750.00')  # (5 * 150) / 1
#         self.assertEqual(context['total_cost_price'], expected_cost)
#         self.assertEqual(context['total_piece_unit_selling_price'], expected_selling)
#         self.assertEqual(context['total_profit'], Decimal('250.00'))
#         self.assertEqual(context['percentage'], Decimal('50.00'))

#     def test_mixed_records(self):
#         """Test view with mixture of normal and edge cases"""
#         # Create multiple records
#         DispenseRecord.objects.create(
#             drug=self.drug_normal,
#             quantity=5,
#             dispensary=self.dispensary_locker,
#             dispense_date='2024-01-23'
#         )
#         DispenseRecord.objects.create(
#             drug=self.drug_zero_pack,
#             quantity=5,
#             dispensary=self.dispensary_locker,
#             dispense_date='2024-01-23'
#         )
#         DispenseRecord.objects.create(
#             drug=self.drug_null_pack,
#             quantity=5,
#             dispensary=self.dispensary_locker,
#             dispense_date='2024-01-23'
#         )
        
#         request = self.factory.get(reverse('dispense-record-list', kwargs={'pk': self.dispensary_locker.pk}))
#         request.user = self.user
        
#         view = DispenseRecordView()
#         view.setup(request, pk=self.dispensary_locker.pk)
#         context = view.get_context_data()
        
#         # Should only include normal and null pack size records
#         # (zero pack size should be filtered out)
#         expected_cost = Decimal('550.00')  # (5 * 100 / 10) + (5 * 100 / 1)
#         expected_selling = Decimal('825.00')  # (5 * 150 / 10) + (5 * 150 / 1)
#         self.assertEqual(context['total_cost_price'], expected_cost)
#         self.assertEqual(context['total_piece_unit_selling_price'], expected_selling)
#         self.assertEqual(context['total_profit'], Decimal('275.00'))
#         self.assertEqual(context['percentage'], Decimal('50.00'))