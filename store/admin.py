from django import forms
from django.contrib import admin
from .models import *
from import_export.admin import ImportMixin
from import_export import resources
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


class DrugResource(resources.ModelResource):
    expiration_date = fields.Field(attribute='expiration_date', column_name='expiration_date')

    class Meta:
        model = Drug
        import_id_fields = ('id',)
        fields = ('id', 'date_added', 'supply_date', 'strength', 'generic_name', 'trade_name', 'category', 'supplier', 'dosage_form', 'pack_size', 'cost_price', 'selling_price', 'total_purchased_quantity', 'expiration_date', 'added_by', 'entered_expiry_period', 'updated_at')

    def before_import_row(self, row, **kwargs):
        if 'expiration_date' in row and row['expiration_date']:
            if isinstance(row['expiration_date'], datetime):
                # If it's already a datetime object, just get the date
                row['expiration_date'] = row['expiration_date'].date()
            elif isinstance(row['expiration_date'], str):
                # Try parsing as date first
                parsed_date = parse_date(row['expiration_date'])
                if parsed_date:
                    row['expiration_date'] = parsed_date
                else:
                    # If parsing as date fails, try parsing as datetime
                    try:
                        expiration_datetime = datetime.strptime(row['expiration_date'], '%Y-%m-%d %H:%M:%S')
                        row['expiration_date'] = expiration_datetime.date()
                    except ValueError:
                        # If all parsing attempts fail, set to None or handle as needed
                        row['expiration_date'] = None
                        
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