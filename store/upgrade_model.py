from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
from django.db.models import Sum


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

class Unit(models.Model):
    UNIT_TYPES = (
        ('MAIN', 'Main Store'),
        ('LOCAL', 'Local Store'),
        ('DISPENSARY', 'Dispensary Locker'),
    )
    name = models.CharField(max_length=100,null=True)
    unit_type = models.CharField(max_length=10, choices=UNIT_TYPES,null=True)
    parent_unit = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_units')
    group = models.OneToOneField(Group, on_delete=models.PROTECT, related_name='unit', null=True,blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and not self.group:
            self.group = Group.objects.create(name=f"{self.name} Group")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_unit_type_display()})"

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
    total_purchased_quantity = models.PositiveIntegerField('TOTAL QTY PURCHASED',default=0)
    expiration_date = models.DateField(null=True, blank=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='added_drugs')
    updated_at = models.DateField('DATE UPDATED',auto_now=True)

    def __str__(self):
        return self.generic_name

    @property
    def total_value(self):
        return self.current_balance * self.cost_price if self.current_balance is not None and self.cost_price is not None else 0

    @classmethod
    def total_store_value(cls):
        return sum(drug.total_value for drug in cls.objects.all())

    @property
    def total_issued(self):
        return self.distributions.filter(from_unit__unit_type='MAIN').aggregate(Sum('quantity'))['quantity__sum'] or 0

    @property
    def current_balance(self):
        main_store = Unit.objects.get(unit_type='MAIN')
        main_store_quantity = UnitStore.objects.filter(unit=main_store, drug=self).aggregate(Sum('quantity'))['quantity__sum'] or 0
        return main_store_quantity

    @property
    def total_quantity_in_system(self):
        return UnitStore.objects.filter(drug=self).aggregate(Sum('quantity'))['quantity__sum'] or 0

    class Meta:
        verbose_name_plural = 'drugs'

    def quantity_in_unit(self, unit):
        unit_store = UnitStore.objects.filter(unit=unit, drug=self).first()
        return unit_store.quantity if unit_store else 0

    def quantity_in_local_stores(self):
        return UnitStore.objects.filter(unit__unit_type='LOCAL', drug=self).aggregate(Sum('quantity'))['quantity__sum'] or 0

    def quantity_in_dispensaries(self):
        return UnitStore.objects.filter(unit__unit_type='DISPENSARY', drug=self).aggregate(Sum('quantity'))['quantity__sum'] or 0


class Distribution(models.Model):
    DISTRIBUTION_TYPES = (
        ('MAIN_TO_LOCAL', 'Main Store to Local Store'),
        ('LOCAL_TO_LOCAL', 'Local Store to Local Store'),
        ('LOCAL_TO_DISPENSARY', 'Local Store to Dispensary Locker'),
    )

    category = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True, related_name="distributions")
    drug = models.ForeignKey('Drug', on_delete=models.CASCADE, related_name="distributions")
    from_unit = models.ForeignKey('Unit', on_delete=models.CASCADE, related_name='distributions_from')
    to_unit = models.ForeignKey('Unit', on_delete=models.CASCADE, related_name='distributions_to')
    distribution_type = models.CharField(max_length=20, choices=DISTRIBUTION_TYPES)
    siv = models.CharField('SIV', max_length=100, null=True, blank=True)
    srv = models.CharField('SRV', max_length=100, null=True, blank=True)
    invoice_no = models.PositiveIntegerField('INVOICE NUMBER', null=True, blank=True)
    quantity = models.PositiveIntegerField('QTY ISSUED')
    date_issued = models.DateField()
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='distributions')
    remark = models.CharField('REMARKS', max_length=200, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.from_unit.unit_type == 'MAIN' and self.distribution_type != 'MAIN_TO_LOCAL':
            raise ValidationError("Main store can only distribute to local stores.")
        if self.from_unit.unit_type == 'LOCAL' and self.to_unit.unit_type == 'MAIN':
            raise ValidationError("Local stores cannot distribute to the main store.")
        if self.from_unit.unit_type == 'DISPENSARY':
            raise ValidationError("Dispensary lockers cannot distribute drugs.")
        if self.distribution_type == 'LOCAL_TO_DISPENSARY' and self.to_unit.unit_type != 'DISPENSARY':
            raise ValidationError("This distribution type must be to a dispensary locker.")
        if self.distribution_type == 'LOCAL_TO_DISPENSARY' and self.to_unit.parent_unit != self.from_unit:
            raise ValidationError("Can only distribute to dispensary lockers within the same local store.")

    def save(self, *args, **kwargs):
        self.clean()
        
        from_store, _ = UnitStore.objects.get_or_create(unit=self.from_unit, drug=self.drug)
        
        if self.pk:  # This is an update
            original_distribution = Distribution.objects.get(pk=self.pk)
            original_quantity = original_distribution.quantity
            quantity_difference = self.quantity - original_quantity
        else:  # This is a new distribution
            quantity_difference = self.quantity

        if quantity_difference > from_store.quantity:
            if from_store.quantity > 0:
                self.quantity = original_quantity + from_store.quantity
            else:
                raise ValidationError(_("Not enough drugs available in the source unit."), code='invalid_quantity')

        from_store.quantity -= quantity_difference
        from_store.save()

        to_store, _ = UnitStore.objects.get_or_create(unit=self.to_unit, drug=self.drug)
        to_store.quantity += quantity_difference
        to_store.save()

        if self.from_unit.unit_type == 'MAIN':
            self.drug.total_purchased_quantity -= quantity_difference
            self.drug.save()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'drug distributions'

    def __str__(self):
        return f"{self.distribution_type}: {self.quantity} of {self.drug.name} from {self.from_unit.name} to {self.to_unit.name}"

class Restock(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='restock_category')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, null=True,)
    quantity = models.IntegerField()
    date = models.DateField()
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
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='unit_store',null=True)
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='unit_store_drugs',null=True)
    quantity = models.PositiveIntegerField('Quantity Available', default=0,null=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_value(self):
        return self.quantity * self.drug.cost_price

    def __str__(self):
        return f"{self.quantity} of {self.drug.generic_name} in {self.unit.name}"