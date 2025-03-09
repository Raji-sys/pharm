from django import forms
from django.contrib import admin
from .models import *
from import_export.admin import ImportExportModelAdmin 
from import_export import resources
from datetime import datetime
from django.utils.dateparse import parse_date
from datetime import datetime
from django.utils.dateparse import parse_date
from import_export import fields, resources
from django.contrib import messages
from import_export.fields import Field
from import_export.widgets import Widget
from import_export.widgets import ForeignKeyWidget
from django.db.models import Q

admin.site.site_header="ADMIN PANEL"
admin.site.index_title="PHARMACY INVENTORY MANAGEMENT SYSTEM"
admin.site.site_title="NOHD PHARMACY INVENTORY"

    
class DrugAdminForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = ['total_purchased_quantity','pack_size','cost_price','selling_price','expiration_date',]  
        # readonly_fields = ['total_purchased_quantity']


class CaseInsensitiveForeignKeyWidget(ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.filter(
            Q(name__iexact=value)
        )

class DrugResource(resources.ModelResource):
    category = fields.Field(
        attribute='category',
        column_name='category',
        widget=CaseInsensitiveForeignKeyWidget(Category, 'name')
    )
    current_balance = fields.Field(column_name='current_balance')

    class Meta:
        model = Drug
        import_id_fields = ('id',)
        fields = ('id', 'strength', 'generic_name', 'trade_name', 'category', 'supplier', 'dosage_form', 'pack_size', 'cost_price', 'selling_price', 'current_balance', )

    def dehydrate_current_balance(self, drug):
        # Ensure the computed property is included in the export
        return drug.current_balance

    def before_import_row(self, row, **kwargs):
        if 'expiration_date' in row and row['expiration_date']:
            if isinstance(row['expiration_date'], datetime):
                row['expiration_date'] = row['expiration_date'].date()
            elif isinstance(row['expiration_date'], str):
                parsed_date = parse_date(row['expiration_date'])
                if parsed_date:
                    row['expiration_date'] = parsed_date
                else:
                    try:
                        expiration_datetime = datetime.strptime(row['expiration_date'], '%Y-%m-%d %H:%M:%S')
                        row['expiration_date'] = expiration_datetime.date()
                    except ValueError:
                        row['expiration_date'] = None
                        
@admin.register(Drug)
class DrugAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = DrugResource
    form = DrugAdminForm
    exclude = ('added_by', 'balance', 'total_value')
    list_display = ['generic_name', 'trade_name', 'strength', 'category', 'supplier', 'dosage_form', 'pack_size', 'cost_price', 'selling_price', 'total_purchased_quantity', 'current_balance', 'total_value', 'expiration_date', 'added_by', 'supply_date', 'updated_at']
    list_filter = ['supply_date', 'category', 'supplier', 'added_by']
    search_fields = ['generic_name','trade_name','category__name']
    list_per_page = 10
    change_list_template = 'admin/change_list.html' 
    # autocomplete_fields = ['trade_name','generic_name','category','supplier']
    
    def total_value(self, obj):
        return obj.total_value

    total_value.short_description = 'Total Value'

    def save_model(self, request, obj, form, change):
        if not obj.added_by:
            obj.added_by = request.user
        obj.save()

class DrugForeignKeyWidget(Widget):
    def __init__(self, model, field):
        self.model = model
        self.field = field

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return None
        value = value
        try:
            if self.field == 'code':
                return self.model.objects.get(code=value)
            else:
                return self.model.objects.get(trade_name__iexact=value)
        except self.model.DoesNotExist:
            raise IndexError(f"{value} does not exist in the database")

    def render(self, value, obj=None):
        if isinstance(value, self.model):
            if self.field == 'code':
                return getattr(value, self.field)
            else:
                return getattr(value, 'trade_name')
        return value


class RecordResource(resources.ModelResource):
    id = Field(
        column_name='id',
        attribute='id',
        default=None
    )
    category = Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'name')
    )
    code = Field(
        column_name='code',
        attribute='drug',
        widget=DrugForeignKeyWidget(Drug, 'code')
    )
    unit_issued_to = Field(
        column_name='unit_issued_to',
        attribute='unit_issued_to',
        widget=ForeignKeyWidget(Unit, 'name')
    )
    issued_by = Field(
        column_name='issued_by',
        attribute='issued_by',
        widget=ForeignKeyWidget(User, 'username')
    )
    quantity = Field(
        column_name='quantity',
        attribute='quantity'
    )
    date_issued = Field(
        column_name='date_issued',
        attribute='date_issued'
    )
    remark = Field(
        column_name='remark',
        attribute='remark'
    )

    class Meta:
        model = Record
        fields = ('id', 'category', 'code', 'unit_issued_to', 'quantity', 'date_issued', 'remark', 'issued_by')
        import_id_fields = []
        skip_unchanged = True
        report_skipped = False

    def before_import_row(self, row, row_number=None, **kwargs):
        # Remove empty ID field if present
        if 'id' in row and not row['id']:
            del row['id']

        # Validate the `code` field before import
        code = row.get('code')
        if not code:
            raise ValueError("The 'code' field cannot be empty.")

        # First, check if a drug with this code exists in the database
        drug_queryset = Drug.objects.filter(code=code)

        if not drug_queryset.exists():
            raise ValueError(f"Drug with code '{code}' does not exist in the database.")

        if drug_queryset.count() > 1:
            raise ValueError(f"Multiple drugs found with code '{code}'. Please specify a unique code.")

        # Set the drug ID in the row
        drug = drug_queryset.first()  # Get the first matching drug
        row['code'] = drug.id  # Update the row with the correct drug ID


            
@admin.register(Record)
class RecordAdmin(ImportExportModelAdmin,  admin.ModelAdmin):
    exclude = ('issued_by', 'balance')
    list_display = ['drug', 'unit_issued_to', 'issued_by_username', 'quantity', 'date_issued','updated_at']
    search_fields = ['drug', 'issued_to','drug__supplier','drug__supply_date']
    list_filter = ['unit_issued_to','drug__supplier','updated_at']
    list_per_page = 10
    resource_class = RecordResource

    def save_model(self, request, obj, form, change):
        try:
            obj.issued_by = request.user
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            messages.error(request, f"Error: {e.message}")

    def drug_date(self, obj):
        return obj.drug.supply_date

    def issued_by_username(self, obj):
        return obj.issued_by.username if obj.issued_by else None

    issued_by_username.short_description = "Issued By"


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'file_no', 'age','phone')
    search_fields = ('name','file_no')
    # autocomplete_fields = ['name',]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'update', 'total_unit_value')
    search_fields = ('name',)
    list_filter = ('update',)


@admin.register(DispenseRecord)
class DispenseRecordAdmin(admin.ModelAdmin):
    list_display=('patient_info','date_issued','dispensary','drug','quantity','balance_quantity','dispensed_by','dispense_date',)
    search_fields=('patient_info__file_no','dispensary__name','drug__trade_name','drug__generic_name','dispensed_by__username','dispense_date',)
    list_filter=('dispensary','dispensed_by','dispense_date',)


class UnitStoreResource(resources.ModelResource):
    unit_name = Field(attribute='unit__name', column_name='Unit')
    drug_generic_name = Field(attribute='drug__generic_name', column_name='Generic Name')
    drug_trade_name = Field(attribute='drug__trade_name', column_name='Trade Name')
    dosage_form = Field(attribute='drug__dosage_form', column_name='Dosage Form')
    strength = Field(attribute='drug__strength', column_name='Strength')
    category = Field(attribute='drug__category__name', column_name='Category')
    total_value = Field(column_name='Total Value')
    
    def dehydrate_total_value(self, obj):
        return obj.total_value
    
    class Meta:
        model = UnitStore
        fields = ('unit_name', 'drug_generic_name', 'drug_trade_name', 'dosage_form', 
                  'strength', 'category', 'quantity', 'total_value')
        export_order = fields

@admin.register(UnitStore)
class UnitStoreAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = UnitStoreResource
    
    def get_dosage_form(self, obj):
        return obj.drug.dosage_form if obj.drug else '-'
    get_dosage_form.short_description = 'Dosage Form'

    def get_trade_name(self, obj):
        return obj.drug.trade_name if obj.drug else '-'
    get_trade_name.short_description = 'Trade Name'

    def get_generic_name(self, obj):
        return obj.drug.generic_name if obj.drug else '-'
    get_generic_name.short_description = 'Generic Name'
 
    def get_strength(self, obj):
        return obj.drug.strength if obj.drug else '-'
    get_strength.short_description = 'Strength'

    def get_category(self, obj):
        return obj.drug.category.name if obj.drug and obj.drug.category else '-'
    get_category.short_description = 'Category'

    list_display = (
        'unit', 
        'drug', 
        'get_generic_name', 
        'get_trade_name', 
        'get_dosage_form', 
        'get_strength',
        'get_category', 
        'quantity', 
        'updated_at'
    )
    
    search_fields = (
        'unit__name', 
        'drug__trade_name', 
        'drug__generic_name', 
        'drug__dosage_form'
    )
    
    list_filter = (
        'unit', 
        'drug__dosage_form', 
        'drug__category', 
        'updated_at'
    )

class LockerInventoryResource(resources.ModelResource):
    locker_name = Field(attribute='locker__unit', column_name='Unit')
    drug_generic_name = Field(attribute='drug__generic_name', column_name='Generic Name')
    drug_trade_name = Field(attribute='drug__trade_name', column_name='Trade Name')
    dosage_form = Field(attribute='drug__dosage_form', column_name='Dosage Form')
    strength = Field(attribute='drug__strength', column_name='Strength')
    category = Field(attribute='drug__category__name', column_name='Category')
    
    class Meta:
        model = LockerInventory
        fields = ('locker_name', 'drug_generic_name', 'drug_trade_name', 'dosage_form', 'strength', 'category', 'quantity')
        export_order = fields

@admin.register(LockerInventory)
class LockerAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = LockerInventoryResource
    
    def get_dosage_form(self, obj):
        return obj.drug.dosage_form if obj.drug else '-'
    get_dosage_form.short_description = 'Dosage Form'


    def get_trade_name(self, obj):
        return obj.drug.trade_name if obj.drug else '-'
    get_trade_name.short_description = 'Trade Name'

    def get_generic_name(self, obj):
        return obj.drug.generic_name if obj.drug else '-'
    get_generic_name.short_description = 'Generic Name'

    def get_strength(self, obj):
        return obj.drug.strength if obj.drug else '-'
    get_strength.short_description = 'Strength'

    def get_category(self, obj):
        return obj.drug.category.name if obj.drug and obj.drug.category else '-'
    get_category.short_description = 'Category'

    list_display = (
        'locker', 
        'drug', 
        'get_generic_name', 
        'get_trade_name', 
        'get_dosage_form', 
        'get_strength',
        'get_category', 
        'quantity', 
        'updated'
    )
    
    search_fields = (
        'locker__name', 
        'drug__trade_name', 
        'drug__generic_name', 
        'drug__dosage_form'
    )
    
    list_filter = (
        'locker', 
        'drug__dosage_form', 
        'drug__category', 
        'updated'
    )


class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        fields = ('id', 'name')
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = False


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ['id', 'name']
    list_filter = ['name']
    search_fields = ['name']
    resource_class = CategoryResource


@admin.register(DrugRequest)
class DrugRequestAdmin(admin.ModelAdmin):
    list_display = ['unit','drugs', 'updated', 'requested_by']
    list_filter = ['requested_by','unit', 'updated']
    search_fields = ['drugs', 'requested_by__username']
    list_per_page = 10

    def save_model(self, request, obj, form, change):
        if not obj.requested_by:
            obj.requested_by = request.user
        obj.save()