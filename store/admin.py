from django import forms
from django.contrib import admin
from .models import *
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from import_export.admin import ImportMixin


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


@admin.register(Restock)
class RestockAdmin(admin.ModelAdmin):
    list_display = ('category','drug', 'quantity', 'date')

    def drug_name(self, obj):
        return obj.drug.name
    
    drug_name.short_description = 'drug Name'


@admin.register(Drug)
class DrugAdmin(ImportMixin,admin.ModelAdmin):
    form=DrugAdminForm
    # readonly_fields=('total_purchased_quantity',)
    exclude=('added_by','balance','total_value')
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


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    exclude = ('issued_by', 'balance')
    list_display = ['drug', 'unit_issued_to', 'issued_by_username', 'quantity', 'date_issued','updated_at']
    search_fields = ['drug', 'issued_to','drug__supplier','drug__supply_date']
    list_filter = ['unit_issued_to', 'drug','drug__supplier','drug__supply_date']
    list_per_page = 10

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

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'update', 'total_unit_value')
    search_fields = ('name',)
    list_filter = ('update',)

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


@admin.register(DispenseRecord)
class DispenseRecordAdmin(admin.ModelAdmin):
    list_display = ('dispensary', 'patient_info','drug', 'quantity', 'dispensed_by', 'updated')
    search_fields = ('dispense__name', 'drug__generic_name', 'patient_info', 'issued_by__username')
    list_filter = ('updated','dispensed_by', 'dispensary')
