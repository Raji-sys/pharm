from tabnanny import verbose
import django_filters
from .models import Drug, Category, Record, Restock, Unit
from django import forms


class DrugSearchFilter(django_filters.FilterSet):
    generic_name = django_filters.CharFilter(label="GENERIC NAME",field_name='generic_name', lookup_expr='icontains')
    trade_name = django_filters.CharFilter(label="TRADE NAME",field_name='trade_name', lookup_expr='icontains')
   
    class Meta:
        model = Drug
        fields = ['generic_name','trade_name',]


from django_filters import rest_framework as filters
from django.forms.widgets import SelectDateWidget
import datetime

class DrugFilter(filters.FilterSet):
    category = filters.ChoiceFilter(label="CLASS", field_name='category__name', lookup_expr='iexact', choices=Category.DRUG_CLASSES,
                                    widget=forms.Select(attrs={'class': 'text-center text-xs focus:outline-none w-1/3 sm:w-fit text-indigo-800 rounded shadow-sm shadow-indigo-600 border-indigo-600 border'}))
    name = filters.CharFilter(label="DRUG", field_name='generic_name', lookup_expr='icontains')
    dosage_form = filters.ChoiceFilter(label="DOSAGE FORM", field_name='dosage_form', choices=Drug.dosage, lookup_expr='iexact',
                                       widget=forms.Select(attrs={'class': 'text-center text-xs focus:outline-none w-1/3 sm:w-fit text-indigo-800 rounded shadow-sm shadow-indigo-600 border-indigo-600 border'}))
    generic_name = filters.CharFilter(label="GENERIC NAME", field_name='generic_name', lookup_expr='icontains')
    trade_name = filters.CharFilter(label="TRADE NAME", field_name='trade_name', lookup_expr='icontains')
    supplier = filters.CharFilter(label="SUPPLIER", field_name='supplier', lookup_expr='icontains')
    
    # Supply Date Filters
    supply_date_exact = filters.DateFilter(label="EXACT SUPPLY DATE", field_name='supply_date', lookup_expr='exact',
                                           widget=forms.DateInput(attrs={'type':'date'}))
    supply_date_start = filters.DateFilter(label="SUPPLY DATE FROM", field_name='supply_date', lookup_expr='gte',
                                           widget=forms.DateInput(attrs={'type':'date'}))
    supply_date_end = filters.DateFilter(label="SUPPLY DATE TO", field_name='supply_date', lookup_expr='lte',
                                         widget=forms.DateInput(attrs={'type':'date'}))
    
    # Expiration Date Filters
    expiration_date_exact = filters.DateFilter(label="EXACT EXPIRY DATE", field_name='expiration_date', lookup_expr='exact',
                                               widget=forms.DateInput(attrs={'type':'date'}))
    expiration_date_start = filters.DateFilter(label="EXPIRY DATE FROM", field_name='expiration_date', lookup_expr='gte',
                                               widget=forms.DateInput(attrs={'type':'date'}))
    expiration_date_end = filters.DateFilter(label="EXPIRY DATE TO", field_name='expiration_date', lookup_expr='lte',
                                             widget=forms.DateInput(attrs={'type':'date'}))
    
    pack_size = filters.CharFilter(label="PACK SIZE", field_name='pack_size', lookup_expr='icontains')
    added_by = filters.CharFilter(label="ADDED BY", field_name='added_by__username', lookup_expr='iexact')

    class Meta:
        model = Drug
        exclude = ['date_added', 'supply_date', 'total_value', 'selling_price', 'entered_expiry_period', 'cost_price', 'updated_at', 'expiration_date', 'total_purchased_quantity']



class RecordFilter(django_filters.FilterSet):
    generic_name = django_filters.CharFilter(label="GENERIC NAME", field_name='drug__generic_name', lookup_expr='icontains')
    trade_name = django_filters.CharFilter(label="TRADE NAME", field_name='drug__trade_name', lookup_expr='icontains')
    supplier = django_filters.CharFilter(label="SUPPLIER", field_name='drug__supplier', lookup_expr='icontains')
    unit_issued_to = django_filters.ModelChoiceFilter(
        label="UNIT ISSUED",
        queryset=Unit.objects.all(),
        field_name='unit_issued_to',
        to_field_name='id',
        lookup_expr='exact',
        widget=forms.Select(attrs={'class': 'text-center text-xs focus:outline-none w-1/3 sm:w-fit text-indigo-800 rounded shadow-sm shadow-indigo-600 border-indigo-600 border'})
    )

    # Date Issued Filters
    date_issued_exact = django_filters.DateFilter(
        label="EXACT DATE ISSUED",
        field_name='date_issued',
        lookup_expr='exact',
        widget=forms.DateInput(attrs={'type':'date'})
    )
    date_issued_start = django_filters.DateFilter(
        label="DATE ISSUED FROM",
        field_name='date_issued',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type':'date'})
    )
    date_issued_end = django_filters.DateFilter(
        label="DATE ISSUED TO",
        field_name='date_issued',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type':'date'})
    )


    issued_by = django_filters.CharFilter(label="ISSUED BY", field_name='issued_by__username', lookup_expr='iexact')

    class Meta:
        model = Record
        exclude = ['date_issued', 'category', 'drug', 'balance', 'siv', 'srv', 'invoice_no', 'updated_at', 'remark', 'quantity']



class RestockFilter(django_filters.FilterSet):
    # Date Filters
    date_exact = django_filters.DateFilter(
        label="EXACT DATE",
        field_name='date',
        lookup_expr='exact',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_start = django_filters.DateFilter(
        label="DATE FROM",
        field_name='date',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_end = django_filters.DateFilter(
        label="DATE TO",
        field_name='date',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    # Category Filter
    category = django_filters.ChoiceFilter(
        label="CATEGORY",
        field_name='drug__category__name',
        lookup_expr='iexact',
        choices=Category.DRUG_CLASSES,
        widget=forms.Select(attrs={'class': 'text-center text-xs focus:outline-none w-1/3 sm:w-fit text-indigo-800 rounded shadow-sm shadow-indigo-600 border-indigo-600 border'})
    )

    # Drug Filter
    drug = django_filters.CharFilter(label="DRUG", field_name='drug__name', lookup_expr='icontains')


    # Restocked By Filter (new)
    restocked_by = django_filters.CharFilter(label="RESTOCKED BY", field_name='restocked_by__username', lookup_expr='icontains')

    class Meta:
        model = Restock
        exclude = ['updated', 'date', 'quantity', 'restocked_by']