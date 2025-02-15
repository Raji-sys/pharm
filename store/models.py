from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta
import logging
logger = logging.getLogger(__name__)
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils.timezone import now
from user_agents import parse
from django.db.models import F, ExpressionWrapper, DecimalField
from django.core.validators import MinValueValidator


class Unit(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    update = models.DateField(auto_now_add=True, null=True)

    @transaction.atomic
    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating:
            DispensaryLocker.objects.create(unit=self)

    def total_unit_value(self):
        store_value = sum(
            store.quantity * (store.drug.piece_unit_cost_price or 0) for store in self.unit_store.all()
        )

        locker_value = 0
        if hasattr(self, 'dispensary_locker'):
            locker_value = sum(
                item.quantity * (item.drug.piece_unit_cost_price or 0) for item in self.dispensary_locker.inventory.all()
            )

        return store_value + locker_value


    def total_unit_quantity(self):
        store_quantity = sum(
            store.quantity for store in self.unit_store.all()
        )
        locker_quantity = 0
        if hasattr(self, 'dispensary_locker'):
            locker_quantity = self.dispensary_locker.inventory.aggregate(
                total=Sum('quantity')
            )['total'] or 0
        return store_quantity + locker_quantity

    @classmethod
    def combined_unit_value(cls):
        return sum(unit.total_unit_value() for unit in cls.objects.all())

    @classmethod
    def combined_unit_quantity(cls):
        return sum(unit.total_unit_quantity() for unit in cls.objects.all())

    @classmethod
    def grand_total_value(cls):
        main_store_value = Drug.total_store_value()
        combined_unit_value = cls.combined_unit_value()
        return main_store_value + combined_unit_value

    @classmethod
    def grand_total_quantity(cls):
        main_store_quantity = Drug.total_store_quantity()  # Assuming you've added this method to the Drug model
        combined_unit_quantity = cls.combined_unit_quantity()
        return main_store_quantity + combined_unit_quantity

    def __str__(self):
        return self.name

class Category(models.Model):
    DRUG_CLASSES = [
        ('ANALGESIC', 'Analgesic'),
        ('ANAESTHETIC', 'Anaesthetic'),
        ('ANTIBIOTIC', 'Antibiotic'),
        ('ANTICOAGULANT', 'Anticoagulant'),
        ('ANTICONVULSANT', 'Anticonvulsant'),
        ('ANTIDEPRESSANT', 'Antidepressant'),
        ('ANTIDIABETIC', 'Antidiabetic'),
        ('ANTIDIARHEAL', 'Antidiarheal'),
        ('ANTIEMETIC', 'Antiemetic'),
        ('ANTIFUNGAL', 'Antifungal'),
        ('ANTIFIBRINOLYTICS', 'Antifibrinolytics'),
        ('ANTI_ACNE', 'Anti-Acne'),
        ('ANTIHISTAMINE', 'Antihistamine'),
        ('ANTIHYPERTENSIVE', 'Antihypertensive'),
        ('ANTI-INFLAMMATORY', 'Anti-inflammatory'),
        ('ANTINEOPLASTIC', 'Antineoplastic'),
        ('ANTIPARASITIC', 'Antiparasitic'),
        ('ANTIPSYCHOTIC', 'Antipsychotic'),
        ('ANTI-TUBERCULOSIS', 'Anti-Tuberculosis'),
        ('ANTI-UCLER', 'Anti-ulcer'),
        ('ANTIVIRAL', 'Antiviral'),
        ('BRONCHODILATOR', 'Bronchodilator'),
        ('CARDIOVASCULAR', 'Cardiovascular'),
        ('CNS_STIMULANT', 'CNS Stimulant'),
        ('CORTICOSTEROID', 'Corticosteroid'),
        ('CONSUMABLES', 'Consumables'),
        ('DERMATOLOGICAL', 'Dermatological'),
        ('DIURETIC', 'Diuretic'),
        ('GASTROINTESTINAL', 'Gastrointestinal'),
        ('HORMONE', 'Hormone'),
        ('IMMUNOSUPPRESSANT', 'Immunosuppressant'),
        ('LIPID_LOWERING', 'Lipid-lowering'),
        ('MUSCLE_RELAXANT', 'Muscle Relaxant'),
        ('NSAID', 'NSAID'),
        ('OPIOID', 'Opioid'),
        ('OPHTHALMIC', 'Ophthalmic'),
        ('PSYCHOTROPIC', 'Psychotropic'),
        ('SEDATIVES_HYPNOTIC', 'Sedatives/Hypnotic'),
        ('THYROID_PREPARATION', 'Thyroid Preparation'),
        ('VACCINE', 'Vaccine'),
        ('VITAMINS_MINERAL', 'Vitamins and Mineral'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField('CLASS OF DRUG', max_length=200, choices=DRUG_CLASSES)
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'categories'


class Drug(models.Model):
    date_added = models.DateField(auto_now_add=True,null=True)
    supply_date = models.DateField(null=True)
    strength = models.CharField('STRENGTH',max_length=100, null=True, blank=True)
    generic_name = models.CharField('GENERIC NAME',max_length=100, null=True, blank=True)
    trade_name = models.CharField('TRADE NAME',max_length=100, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='drug_category')
    supplier = models.CharField('SUPPLIER',max_length=100, null=True, blank=True)
    dosage=(('TABLET','TABLET'),('CAPSULE','CAPSULE'),('SYRUP','SYRUP'),('INJECTION','INJECTION'),('INFUSION','INFUSION'),('SUSPENSION','SUSPENSION'),('SOLUTION','SOLUTION'),('CONSUMABLE','CONSUMABLE'),('POWDER','POWDER'),('GRANULE','GRANULE'),('PELLET','PELLET'),
            ('EMULSION','EMULSION'),('TINCTURE','TINCTURE'),('OINTMENT','OINMENT'),('CREAM','CREAM'),('GEL','GEL'),('SUPPOSITORY','SUPPOSITORY'),('INHALER','INHALER'),('IMPLANT','IMPLANT'),('LOZENGE','LOZENGEN'),('SPRAY','SPRAY'),('TRANSDERMAL PATCH','TRANSDERMAL PATCH'))
    dosage_form = models.CharField(choices=dosage,max_length=100, null=True, blank=True)
    pack_size = models.PositiveIntegerField('PACK SIZE', validators=[MinValueValidator(1)], default=1)

    cost_price = models.DecimalField('COST PRICE',max_digits=10, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_purchased_quantity = models.PositiveIntegerField('TOTAL QTY PURCHASED',default=0)
    expiration_date = models.DateField(null=True, blank=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='added_drugs')
    entered_expiry_period = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField('DATE UPDATED',auto_now=True)

    def save(self, *args, **kwargs):
       if self.expiration_date:
           six_months_before = self.expiration_date - timedelta(days=180)
           if timezone.now().date() >= six_months_before and not self.entered_expiry_period:
               self.entered_expiry_period = timezone.now()
       super().save(*args, **kwargs)

    @property
    def piece_unit_cost_price(self):
        if self.pack_size and self.cost_price:
            return round(self.cost_price / self.pack_size, 2)
        return self.cost_price

    @property
    def piece_unit_selling_price(self):
        if self.pack_size and self.selling_price:
            return round(self.selling_price / self.pack_size, 2)
        return self.selling_price

    def __str__(self):
        return self.trade_name

    @classmethod
    def total_store_quantity(cls):
        return sum(drug.total_purchased_quantity - drug.total_issued for drug in cls.objects.all())    
    
    @property
    def total_value(self):
        return self.current_balance * self.cost_price if self.current_balance is not None and self.cost_price is not None else 0

    @classmethod
    def total_store_value(cls):
        return sum(drug.total_value for drug in cls.objects.all() if drug.total_value is not None)

    @property
    def total_issued(self):
        return self.drug_records.aggregate(models.Sum('quantity'))['quantity__sum'] or 0

    @property
    def current_balance(self):
        return self.total_purchased_quantity - self.total_issued
    
    @property
    def total_items_purchased(self):
        return self.total_purchased_quantity * (self.pack_size or 1) if self.total_purchased_quantity > 0 else 0

    @property
    def total_items_issued(self):
        return self.total_issued * (self.pack_size or 1)

    @property
    def items_in_stock(self):
        return self.current_balance * (self.pack_size or 1)
    

class Record(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name="drug_records")
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, null=True, blank=True, related_name="drug_records")
    unit_issued_to = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField('QTY ISSUED', null=True, blank=True)
    date_issued = models.DateField(null=True)
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='drug_records')
    remark = models.CharField('REMARKS', max_length=200, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated = models.DateField(auto_now=True)

    def save(self, *args, **kwargs):
        try:
            with transaction.atomic():
                if self.pk:
                    # Update logic for an existing record
                    original_record = Record.objects.select_for_update().get(pk=self.pk)
                    if original_record.unit_issued_to != self.unit_issued_to:
                        # Revert the quantity (in pieces if valid pack_size) in the original unit
                        UnitStore.objects.filter(
                            unit=original_record.unit_issued_to,
                            drug=original_record.drug
                        ).update(quantity=F('quantity') - (
                            original_record.quantity if not original_record.drug.pack_size or original_record.drug.pack_size <= 0 
                            else original_record.quantity * original_record.drug.pack_size
                        ))

                    # Adjust the quantity for the new unit
                    unit_store, created = UnitStore.objects.get_or_create(
                        unit=self.unit_issued_to,
                        drug=self.drug,
                        defaults={'quantity': 0}
                    )
                    items_change = self.quantity if not self.drug.pack_size or self.drug.pack_size <= 0 else self.quantity * self.drug.pack_size
                    if created:
                        unit_store.quantity = items_change
                    else:
                        unit_store.quantity = F('quantity') + items_change
                    unit_store.save()
                else:
                    # Logic for new record
                    unit_store, created = UnitStore.objects.get_or_create(
                        unit=self.unit_issued_to,
                        drug=self.drug,
                        defaults={'quantity': 0}
                    )
                    items_to_add = self.quantity if not self.drug.pack_size or self.drug.pack_size <= 0 else self.quantity * self.drug.pack_size
                    unit_store.quantity = F('quantity') + items_to_add
                    unit_store.save()

                # Save the record
                super().save(*args, **kwargs)
        except Exception as e:
            raise ValidationError(f"Error updating unit store: {str(e)}")

    class Meta:
        verbose_name_plural = 'drugs issued record'


class Restock(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='restock_category')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, null=True,)
    quantity = models.IntegerField()
    date = models.DateField(null=True)
    expiration_date = models.DateField(null=True, blank=True)
    restocked_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='drug_restocking')
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.drug.total_purchased_quantity += self.quantity
        self.drug.save()

    def __str__(self):
        return f"{self.quantity} of {self.drug} restocked on {self.date}"

    class Meta:
        verbose_name_plural = 'restocking record'


class UnitStore(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='unit_store')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='unit_store_drugs')
    quantity = models.PositiveIntegerField('Quantity Available', default=0)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def total_value(self):
        if self.quantity is not None and self.drug.piece_unit_cost_price is not None:
            return self.quantity * self.drug.piece_unit_cost_price
        return 0

    def __str__(self):
        return f"{self.quantity} of {self.drug.generic_name} in {self.unit.name}"

class DispensaryLocker(models.Model):
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='dispensary_locker')
    name = models.CharField(max_length=100, default="Dispensary Locker")
    
    def __str__(self):
        return f"{self.unit.name} {self.name}"

class LockerInventory(models.Model):
    locker = models.ForeignKey(DispensaryLocker, on_delete=models.CASCADE, related_name='inventory')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['locker', 'drug']

    def __str__(self):
        return f"{self.drug} in {self.locker}"


class UnitIssueRecord(models.Model):
    BOX_CHOICES = [
        ('expiry', 'Expiry'),
        ('damage', 'Damage'),
        ('other', 'Other'),
    ]
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='issuing_unit')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='unitissue_category')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='issued_drugs')
    quantity = models.PositiveIntegerField(null=True, blank=True)
    date_issued = models.DateTimeField(auto_now_add=True,null=True)
    moved_to = models.CharField (null=True, blank=True, choices=BOX_CHOICES, max_length=100)
    issued_to_locker = models.ForeignKey(DispensaryLocker, on_delete=models.CASCADE, null=True, blank=True)
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    updated_at = models.DateField(auto_now=True)
    
    
    def save(self, *args, **kwargs):
        unit_store = UnitStore.objects.get(unit=self.unit, drug=self.drug)
        
        if self.quantity > unit_store.quantity:
            raise ValidationError(_("Not enough drugs in the unit store."), code='invalid_quantity')
        
        # Deduct from the issuing unit's store
        unit_store.quantity -= self.quantity
        unit_store.save()
        super().save(*args, **kwargs)


# class TransferRecord(models.Model):
#     unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='transfer_unit')
#     category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='transfer_category')
#     drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='transfer_drugs')
#     quantity = models.PositiveIntegerField(null=True, blank=True)
#     date_issued = models.DateTimeField(auto_now_add=True,null=True)
#     issued_to = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='receiving_unit', null=True, blank=True)
#     issued_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
#     updated_at = models.DateField(auto_now=True)
    
    
#     def save(self, *args, **kwargs):
#         unit_store = UnitStore.objects.get(unit=self.unit, drug=self.drug)
        
#         if self.quantity > unit_store.quantity:
#             raise ValidationError(_("Not enough drugs in the unit store."), code='invalid_quantity')
        
#         # Deduct from the issuing unit's store
#         unit_store.quantity -= self.quantity
#         unit_store.save()

#         # Add to the receiving unit's store if applicable
#         if self.issued_to:
#             receiving_store, created = UnitStore.objects.get_or_create(unit=self.issued_to, drug=self.drug)
#             receiving_store.quantity += self.quantity
#             receiving_store.save()
#         super().save(*args, **kwargs)

class TransferRecord(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='transfer_unit')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='transfer_category')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='transfer_drugs')
    quantity = models.PositiveIntegerField(null=True, blank=True)
    date_issued = models.DateTimeField(auto_now_add=True, null=True)
    issued_to = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='receiving_unit', null=True, blank=True)
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    updated_at = models.DateField(auto_now=True)
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        # Get the dispensary locker for the issuing unit
        issuing_locker = self.unit.dispensary_locker
        issuing_inventory = LockerInventory.objects.filter(
            locker=issuing_locker,
            drug=self.drug
        ).first()
        
        if not issuing_inventory:
            raise ValidationError(_("Drug not found in the dispensary locker."))
            
        if self.quantity > issuing_inventory.quantity:
            raise ValidationError(_("Not enough drugs in the dispensary locker."))
        
        # Deduct from the issuing unit's dispensary locker
        issuing_inventory.quantity -= self.quantity
        issuing_inventory.save()

        # Add to the receiving unit's dispensary locker if applicable
        if self.issued_to:
            receiving_locker = self.issued_to.dispensary_locker
            receiving_inventory, created = LockerInventory.objects.get_or_create(
                locker=receiving_locker,
                drug=self.drug,
                defaults={'quantity': 0}
            )
            receiving_inventory.quantity += self.quantity
            receiving_inventory.save()
            
        super().save(*args, **kwargs)


class Patient(models.Model):
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField(null=True, blank=True)
    file_no = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.name} No: {self.file_no}"
    

class DispenseRecord(models.Model):
    dispensary = models.ForeignKey(DispensaryLocker, on_delete=models.CASCADE, related_name='issuing_dispensary')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='dispensary_category')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='dispense_drugs')
    quantity = models.PositiveIntegerField(null=True, blank=True)
    patient_info = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='dispense_records',null=True, blank=True)
    # patient_info = models.CharField(max_length=100,null=True)
    dispensed_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    dispense_date = models.DateTimeField(auto_now=True)
    updated = models.DateField(auto_now=True)
    balance_quantity = models.PositiveIntegerField(default=0)  # New field to store balance quantity
    date_issued = models.DateField(auto_now=True, null=True)
    
    def clean(self):
        pass    
    
    def save(self, *args, **kwargs):
        dispense_locker = LockerInventory.objects.get(locker=self.dispensary, drug=self.drug)
        if self.quantity > dispense_locker.quantity:
            raise ValidationError(_("Not enough drugs in the unit store."), code='invalid_quantity')
        # Deduct from the dispensary locker
        dispense_locker.quantity -= self.quantity
        dispense_locker.save()
        # Store current balance quantity
        self.balance_quantity = dispense_locker.quantity
        super().save(*args, **kwargs)


class ReturnedDrugs(models.Model):
    unit = models.ForeignKey('Unit', on_delete=models.CASCADE, related_name='returned_drugs',null=True)  # New field
    patient_info = models.CharField(max_length=100,null=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True, related_name='returned_category')
    drug = models.ForeignKey('Drug', on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField(null=True)
    date = models.DateField(auto_now=True,null=True)
    received_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='drug_returning')
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.drug.total_purchased_quantity += self.quantity
        self.drug.save()

    def __str__(self):
        return f"{self.quantity} of {self.drug} returned to {self.unit} on {self.date}"

    class Meta:
        verbose_name_plural = 'returned drugs record'


class LoginActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    browser = models.CharField(max_length=255, null=True, blank=True)
    os = models.CharField(max_length=255, null=True, blank=True)
    device_type = models.CharField(max_length=50, default='Unknown')
    updated = models.DateTimeField(auto_now=True)

    def get_browser_name(self):
        if not self.user_agent:
            return 'Unknown'
        user_agent = parse(self.user_agent)
        return user_agent.browser.family

    def get_os_name(self):
        if not self.user_agent:
            return 'Unknown'
        user_agent = parse(self.user_agent)
        return user_agent.os.family

    def get_device_type(self):
        if not self.user_agent:
            return 'Unknown'
        user_agent = parse(self.user_agent)
        if user_agent.is_mobile:
            return 'mobile'
        elif user_agent.is_tablet:
            return 'tablet'
        return 'pc'
    
    def get_device_icon(self):
        device_type = self.get_device_type()
        if device_type == 'mobile':
            return 'fas fa-mobile-alt'
        elif device_type == 'tablet':
            return 'fas fa-tablet-alt'
        return 'fas fa-desktop'

    def get_os_icon(self):
        os_name = self.get_os_name()
        if os_name == 'Windows':
            return 'fab fa-windows'
        elif os_name == 'MacOS':
            return 'fab fa-apple'
        elif os_name == 'Linux':
            return 'fab fa-linux'
        elif os_name == 'Android':
            return 'fab fa-android'
        elif os_name == 'iOS':
            return 'fab fa-apple'
        return 'fas fa-desktop'

    def get_browser_icon(self):
        browser_name = self.get_browser_name()
        if browser_name == 'Chrome':
            return 'fab fa-chrome'
        elif browser_name == 'Firefox':
            return 'fab fa-firefox'
        elif browser_name == 'Safari':
            return 'fab fa-safari'
        elif browser_name == 'Edge':
            return 'fab fa-edge'
        elif browser_name == 'Opera':
            return 'fab fa-opera'
        return 'fas fa-globe'
    
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    
    activity = LoginActivity(
        user=user,
        session_key=request.session.session_key,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    activity.browser = activity.get_browser_name()
    activity.os = activity.get_os_name()
    activity.device_type = activity.get_device_type()
    
    activity.save()

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    LoginActivity.objects.filter(
        user=user,
        logout_time__isnull=True,
        session_key=request.session.session_key
    ).update(logout_time=timezone.now())


class DrugRequest(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='request_drug',null=True)
    drugs = models.TextField(null=True, blank=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    request_date = models.DateField(auto_now=True,null=True)