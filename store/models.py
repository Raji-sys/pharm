from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class Unit(models.Model):
    name=models.CharField(max_length=200, null=True, blank=True)
    update=models.DateField(auto_now_add=True)
    def __str__(self):
        return self.name

class Category(models.Model):
    DRUG_CLASSES = [
        ('ANALGESICS', 'Analgesics'),
        ('ANESTHETICS', 'Anesthetics'),
        ('ANTIBIOTICS', 'Antibiotics'),
        ('ANTICOAGULANTS', 'Anticoagulants'),
        ('ANTICONVULSANTS', 'Anticonvulsants'),
        ('ANTIDEPRESSANTS', 'Antidepressants'),
        ('ANTIDIABETICS', 'Antidiabetics'),
        ('ANTIEMETICS', 'Antiemetics'),
        ('ANTIFUNGALS', 'Antifungals'),
        ('ANTIHISTAMINES', 'Antihistamines'),
        ('ANTIHYPERTENSIVES', 'Antihypertensives'),
        ('ANTI_INFLAMMATORIES', 'Anti-inflammatories'),
        ('ANTINEOPLASTICS', 'Antineoplastics'),
        ('ANTIPARASITICS', 'Antiparasitics'),
        ('ANTIPSYCHOTICS', 'Antipsychotics'),
        ('ANTIVIRALS', 'Antivirals'),
        ('BRONCHODILATORS', 'Bronchodilators'),
        ('CARDIOVASCULAR', 'Cardiovascular'),
        ('CNS_STIMULANTS', 'CNS Stimulants'),
        ('CORTICOSTEROIDS', 'Corticosteroids'),
        ('DERMATOLOGICALS', 'Dermatologicals'),
        ('DIURETICS', 'Diuretics'),
        ('GASTROINTESTINAL', 'Gastrointestinal'),
        ('HORMONES', 'Hormones'),
        ('IMMUNOSUPPRESSANTS', 'Immunosuppressants'),
        ('LIPID_LOWERING', 'Lipid-lowering'),
        ('MUSCLE_RELAXANTS', 'Muscle Relaxants'),
        ('NSAIDS', 'NSAIDs'),
        ('OPIOIDS', 'Opioids'),
        ('OPHTHALMICS', 'Ophthalmics'),
        ('PSYCHOTROPICS', 'Psychotropics'),
        ('SEDATIVES_HYPNOTICS', 'Sedatives/Hypnotics'),
        ('THYROID_PREPARATIONS', 'Thyroid Preparations'),
        ('VACCINES', 'Vaccines'),
        ('VITAMINS_MINERALS', 'Vitamins and Minerals'),
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
    name = models.CharField('DRUG NAME',max_length=100, unique=True)
    generic_name = models.CharField('GENERIC NAME',max_length=100, null=True, blank=True)
    brand_name = models.CharField('BRAND NAME',max_length=100, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='drug_category')
    supplier = models.CharField('SUPPLIER',max_length=100, null=True, blank=True)
    dosage=(('TABLET','TABLET'),('CAPSULE','CAPSULE'),('SYRUP','SYRUP'),('POWDER','POWDER'),('GRANULE','GRANULE'),('PELLET','PELLET'),('SOLUTION','SOLUTION'),('INFUSION','INFUSION'),('SUSPENSIONS','SUSPENSION'),
            ('EMULSION','EMULSION'),('TINCTURE','TINCTURE'),('OINTMENT','OINMENT'),('CREAM','CREAM'),('GEL','GEL'),('SUPPOSITORY','SUPPOSITORY'),('INHALER','INHALER'),('IMPLANT','IMPLANT'),('LOZENGE','LOZENGEN'),('SPRAY','SPRAY'),('TRANSDERMAL PATCH','TRANSDERMAL PATCH'))
    dosage_form = models.CharField(choices=dosage,max_length=100, null=True, blank=True)
    pack_size = models.CharField('PACK SIZE',max_length=100, null=True, blank=True)
    cost_price = models.DecimalField('COST PRICE',max_digits=10, decimal_places=2, null=True, blank=True)
    total_purchased_quantity = models.PositiveIntegerField('TOTAL QTY PURCHASED',default=0)
    expiration_date = models.DateField(null=True, blank=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='added_drugs')
    updated_at = models.DateField('DATE UPDATED',auto_now=True)

    def __str__(self):
        return self.name

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
    siv = models.CharField('SIV',max_length=100, null=True, blank=True)
    srv = models.CharField('SRV',max_length=100, null=True, blank=True)
    invoice_no = models.PositiveIntegerField('INVOICE NUMBER',null=True, blank=True)
    quantity = models.PositiveIntegerField('QTY ISSUED',null=True, blank=True)
    date_issued = models.DateField()
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='drug_records')
    remark = models.CharField('REMARKS',max_length=200, null=True, blank=True)
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

        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'drugs issued record'


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