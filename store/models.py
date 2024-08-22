from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta

class Unit(models.Model):
    name=models.CharField(max_length=200, null=True, blank=True)
    update=models.DateField(auto_now_add=True,null=True)
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating:
            DispensaryLocker.objects.create(unit=self)
    
    def total_unit_value(self):
        store_value = sum(
            store.total_value for store in self.unit_store.all()
            if store.total_value is not None
        )
        # return total_value

    # Calculate value from dispensary locker
        locker_value = 0
        if hasattr(self, 'dispensary_locker'):
            locker_value = self.dispensary_locker.inventory.aggregate(
                total=Sum(F('drug__cost_price') * F('quantity'))
            )['total'] or 0

        return store_value + locker_value
    
    @classmethod
    def combined_unit_value(cls):
        combined_value = sum(
            unit.total_unit_value() for unit in cls.objects.all()
        )
        return combined_value

    @classmethod
    def grand_total_value(cls):
        main_store_value = Drug.total_store_value()  # Assuming Drug model handles the main store
        combined_unit_value = cls.combined_unit_value()
        grand_total = main_store_value + combined_unit_value
        return grand_total

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
    pack_size = models.CharField('PACK SIZE',max_length=100, null=True, blank=True)
    cost_price = models.DecimalField('COST PRICE',max_digits=10, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_purchased_quantity = models.PositiveIntegerField('TOTAL QTY PURCHASED',default=0)
    expiration_date = models.DateField(null=True, blank=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='added_drugs')
    entered_expiry_period = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateField('DATE UPDATED',auto_now=True)

    def save(self, *args, **kwargs):
        if self.expiration_date:
            six_months_before = self.expiration_date - timedelta(days=180)
            if timezone.now().date() >= six_months_before and not self.entered_expiry_period:
                self.entered_expiry_period = timezone.now()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.generic_name

    @property
    def total_value(self):
        return self.current_balance * self.cost_price if self.current_balance is not None and self.cost_price is not None else 0

    @classmethod
    def total_store_value(cls):
        total_store_value = sum(drug.total_value for drug in cls.objects.all() if drug.total_value is not None)
        return total_store_value

    @property
    def total_issued(self):
        return self.drug_records.aggregate(models.Sum('quantity'))['quantity__sum'] or 0

    @property
    def current_balance(self):
        return self.total_purchased_quantity - self.total_issued

    class Meta:
        verbose_name_plural = 'drugs'

class Record(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name="drug_records")
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, null=True, blank=True, related_name="drug_records")
    unit_issued_to = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    siv = models.CharField('SIV', max_length=100, null=True, blank=True)
    srv = models.CharField('SRV', max_length=100, null=True, blank=True)
    invoice_no = models.PositiveIntegerField('INVOICE NUMBER', null=True, blank=True)
    quantity = models.PositiveIntegerField('QTY ISSUED', null=True, blank=True)
    date_issued = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='drug_records')
    remark = models.CharField('REMARKS', max_length=200, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.drug:
            raise ValidationError(_("A drug must be specified."), code='invalid_drug')

        if self.pk:  # This is an update
            original_record = Record.objects.get(pk=self.pk)
            original_quantity = original_record.quantity
            quantity_difference = self.quantity - original_quantity
            available_quantity = self.drug.current_balance + original_quantity
        else:  # This is a new record
            quantity_difference = self.quantity
            available_quantity = self.drug.current_balance

        if quantity_difference > available_quantity:
            if available_quantity > 0:
                self.quantity = original_quantity + available_quantity
            else:
                raise ValidationError(_("No drugs available in the store."), code='invalid_quantity')

        # Deduct from the main store
        self.drug.total_purchased_quantity -= quantity_difference
        self.drug.save()

        # Update the unit's store
        unit_store, created = UnitStore.objects.get_or_create(unit=self.unit_issued_to, drug=self.drug)
        unit_store.quantity += quantity_difference
        unit_store.save()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'drugs issued record'

class Restock(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='restock_category')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, null=True,)
    quantity = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)
    restocked_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='drug_restocking')
    updated = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.drug.total_purchased_quantity += self.quantity
        self.drug.save()

    def __str__(self):
        return f"{self.quantity} of {self.drug.name} restockd on {self.date}"

    class Meta:
        verbose_name_plural = 'restocking record'

class UnitStore(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='unit_store')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='unit_store_drugs')
    quantity = models.PositiveIntegerField('Quantity Available', default=0)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_value(self):
        return self.quantity * self.drug.cost_price

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
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='issuing_unit')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='unitissue_category')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='issued_drugs')
    quantity = models.PositiveIntegerField('QTY ISSUED', null=True, blank=True)
    date_issued = models.DateField(auto_now_add=True,null=True)
    issued_to = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='receiving_unit', null=True, blank=True)
    issued_to_locker = models.ForeignKey(DispensaryLocker, on_delete=models.CASCADE, null=True, blank=True)
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        if self.issued_to and self.issued_to_locker:
            raise ValidationError("Cannot issue to both a unit and a locker at the same time.")
        if not self.issued_to and not self.issued_to_locker:
            raise ValidationError("Must issue to either a unit or a locker.")
    
    def save(self, *args, **kwargs):
        unit_store = UnitStore.objects.get(unit=self.unit, drug=self.drug)
        
        if self.quantity > unit_store.quantity:
            raise ValidationError(_("Not enough drugs in the unit store."), code='invalid_quantity')
        
        # Deduct from the issuing unit's store
        unit_store.quantity -= self.quantity
        unit_store.save()

        # Add to the receiving unit's store if applicable
        if self.issued_to:
            receiving_store, created = UnitStore.objects.get_or_create(unit=self.issued_to, drug=self.drug)
            receiving_store.quantity += self.quantity
            receiving_store.save()
        super().save(*args, **kwargs)


class DispenseRecord(models.Model):
    dispensary = models.ForeignKey(DispensaryLocker, on_delete=models.CASCADE, related_name='issuing_dispensary')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='dispensary_category')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='dispense_drugs')
    quantity = models.PositiveIntegerField('QTY ISSUED', null=True, blank=True)
    patient_info = models.CharField(max_length=100,null=True)
    dispensed_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)
    
    def clean(self):
        pass    
    
    def save(self, *args, **kwargs):
        dispense_locker = LockerInventory.objects.get(locker=self.dispensary, drug=self.drug)
        if self.quantity > dispense_locker.quantity:
            raise ValidationError(_("Not enough drugs in the unit store."), code='invalid_quantity')
        # Deduct from the dispensary locker
        dispense_locker.quantity -= self.quantity
        dispense_locker.save()
        super().save(*args, **kwargs)