from django import forms
from django.contrib import admin
from .models import *
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from import_export.admin import ImportMixin
from import_export import resources
from import_export.fields import Field
from datetime import datetime
from django.utils.dateparse import parse_date
from datetime import datetime
from django.utils.dateparse import parse_date
from import_export import fields, resources


admin.site.site_header="ADMIN PANEL"
admin.site.index_title="PHARMACY INVENTORY MANAGEMENT SYSTEM"
admin.site.site_title="NOHD PHARMACY INVENTORY"

    
class DrugAdminForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = ['generic_name','trade_name','strength','category','supplier','dosage_form','pack_size','cost_price','total_purchased_quantity','expiration_date']  


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id','name']
    list_filter = ['name']
    search_fields = ['name']


from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.utils.dateparse import parse_date
from import_export import fields, resources

class DrugResource(resources.ModelResource):
    date_added = fields.Field(attribute='date_added', column_name='date_added')
    supply_date = fields.Field(attribute='supply_date', column_name='supply_date')
    expiration_date = fields.Field(attribute='expiration_date', column_name='expiration_date')
    cost_price = fields.Field(attribute='cost_price', column_name='cost_price')
    selling_price = fields.Field(attribute='selling_price', column_name='selling_price')
    entered_expiry_period = fields.Field(attribute='entered_expiry_period', column_name='entered_expiry_period')
    updated_at = fields.Field(attribute='updated_at', column_name='updated_at')

    class Meta:
        model = Drug
        import_id_fields = ('id',)
        fields = ('id', 'date_added', 'supply_date', 'strength', 'generic_name', 'trade_name', 'category', 'supplier', 'dosage_form', 'pack_size', 'cost_price', 'selling_price', 'total_purchased_quantity', 'expiration_date', 'added_by', 'entered_expiry_period', 'updated_at')

    def before_import_row(self, row, **kwargs):
        date_fields = ['date_added', 'supply_date', 'expiration_date', 'entered_expiry_period', 'updated_at']
        decimal_fields = ['cost_price', 'selling_price']

        for field in date_fields:
            if field in row and row[field]:
                row[field] = self.parse_date(row[field])

        for field in decimal_fields:
            if field in row and row[field]:
                row[field] = self.parse_decimal(row[field])

    def parse_date(self, value):
        if isinstance(value, datetime):
            return value
        elif isinstance(value, str):
            # Try parsing as date first
            parsed_date = parse_date(value)
            if parsed_date:
                return parsed_date
            # If that fails, try common datetime formats
            for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y'):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None

    def parse_decimal(self, value):
        if isinstance(value, (int, float, Decimal)):
            return Decimal(value)
        elif isinstance(value, str):
            # Remove any non-numeric characters except for the decimal point
            cleaned_value = ''.join(char for char in value if char.isdigit() or char == '.')
            try:
                return Decimal(cleaned_value)
            except InvalidOperation:
                return None
        return None

# class DrugResource(resources.ModelResource):
#     expiration_date = fields.Field(attribute='expiration_date', column_name='expiration_date')

#     class Meta:
#         model = Drug
#         import_id_fields = ('id',)
#         fields = ('id', 'date_added', 'supply_date', 'strength', 'generic_name', 'trade_name', 'category', 'supplier', 'dosage_form', 'pack_size', 'cost_price', 'selling_price', 'total_purchased_quantity', 'expiration_date', 'added_by', 'entered_expiry_period', 'updated_at')

#     def before_import_row(self, row, **kwargs):
#         if 'expiration_date' in row and row['expiration_date']:
#             if isinstance(row['expiration_date'], datetime):
#                 # If it's already a datetime object, just get the date
#                 row['expiration_date'] = row['expiration_date'].date()
#             elif isinstance(row['expiration_date'], str):
#                 # Try parsing as date first
#                 parsed_date = parse_date(row['expiration_date'])
#                 if parsed_date:
#                     row['expiration_date'] = parsed_date
#                 else:
#                     # If parsing as date fails, try parsing as datetime
#                     try:
#                         expiration_datetime = datetime.strptime(row['expiration_date'], '%Y-%m-%d %H:%M:%S')
#                         row['expiration_date'] = expiration_datetime.date()
#                     except ValueError:
#                         # If all parsing attempts fail, set to None or handle as needed
#                         row['expiration_date'] = None
                        
@admin.register(Drug)
class DrugAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = DrugResource
    form = DrugAdminForm
    exclude = ('added_by', 'balance', 'total_value')
    list_display = ['generic_name','trade_name','strength','category','supplier','dosage_form','pack_size','cost_price','total_purchased_quantity','current_balance','total_value','expiration_date','added_by', 'supply_date','updated_at']
    list_filter = ['supply_date','category','supplier','added_by']
    search_fields = ['generic_name']
    list_per_page=10

    def total_value(self, obj):
        return obj.total_value

    total_value.short_description = 'Total Value'

    def save_model(self, request, obj, form, change):
        if not obj.added_by:
            obj.added_by=request.user
        obj.save()


# @admin.register(Record)
# class RecordAdmin(admin.ModelAdmin):
#     exclude = ('issued_by', 'balance')
#     list_display = ['drug', 'unit_issued_to', 'issued_by_username', 'quantity', 'date_issued','updated_at']
#     search_fields = ['drug', 'issued_to','drug__supplier','drug__supply_date']
#     list_filter = ['unit_issued_to', 'drug','drug__supplier','drug__supply_date']
#     list_per_page = 10

#     def save_model(self, request, obj, form, change):
#         try:
#             obj.issued_by = request.user
#             super().save_model(request, obj, form, change)
#         except ValidationError as e:
#             messages.error(request, f"Error: {e.message}")

#     def drug_date(self, obj):
#         return obj.drug.supply_date

#     def issued_by_username(self, obj):
#         return obj.issued_by.username if obj.issued_by else None

#     issued_by_username.short_description = "Issued By"

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'update', 'total_unit_value')
    search_fields = ('name',)
    list_filter = ('update',)

# @admin.register(DispensaryLocker)
# class DispensaryLockerAdmin(admin.ModelAdmin):
#     list_display = ('name', 'unit')
#     search_fields = ('name','unit')
#     list_filter = ('name','unit')

# @admin.register(UnitStore)
# class UnitStoreAdmin(admin.ModelAdmin):
#     list_display = ('unit', 'drug', 'quantity', 'total_value', 'updated_at')
#     search_fields = ('unit__name', 'drug__generic_name')
#     list_filter = ('unit', 'drug', 'updated_at')


# @admin.register(UnitIssueRecord)
# class UnitIssueRecordAdmin(admin.ModelAdmin):
#     list_display = ('unit', 'drug', 'quantity', 'date_issued', 'issued_to', 'issued_by', 'updated_at')
#     search_fields = ('unit__name', 'drug__generic_name', 'issued_to__name', 'issued_by__username')
#     list_filter = ('date_issued', 'issued_to', 'issued_by', 'unit')


# @admin.register(DispensaryLocker)
# class LockerAdmin(admin.ModelAdmin):
#     list_display = ('unit', 'name')
#     list_filter = ('unit', 'name')
#     search_fields = ('name',)


# @admin.register(LockerInventory)
# class LockerInventoryAdmin(admin.ModelAdmin):
#     list_display = ('locker', 'drug','quantity')
#     list_filter = ('locker', 'drug')
#     search_fields = ('locker',)


# @admin.register(DispenseRecord)
# class DispenseRecordAdmin(admin.ModelAdmin):
#     list_display = ('dispensary', 'patient_info','drug', 'quantity', 'dispensed_by', 'updated')
#     search_fields = ('dispense__name', 'drug__generic_name', 'patient_info', 'issued_by__username')
#     list_filter = ('updated','dispensed_by', 'dispensary')
