from tabnanny import verbose
import django_filters
from .models import Drug, Category, Record, Restock, Unit
from django import forms


class DrugSearchFilter(django_filters.FilterSet):
    category = django_filters.ChoiceFilter(label="CLASS", field_name='category__name', lookup_expr='iexact', choices=Category.DRUG_CLASSES,widget=forms.Select(attrs={'class': 'text-center text-xs focus:outline-none w-1/3 sm:w-fit text-indigo-800 rounded shadow-sm shadow-indigo-600 border-indigo-600 border'}))
    generic_name = django_filters.CharFilter(label="GENERIC NAME",field_name='generic_name', lookup_expr='icontains')
    trade_name = django_filters.CharFilter(label="TRADE NAME",field_name='trade_name', lookup_expr='icontains')
   
    class Meta:
        model = Drug
        fields = ['category','generic_name','trade_name',]


class DrugFilter(django_filters.FilterSet):
    category = django_filters.ChoiceFilter(label="CLASS", field_name='category__name', lookup_expr='iexact', choices=Category.DRUG_CLASSES,widget=forms.Select(attrs={'class': 'text-center text-xs focus:outline-none w-1/3 sm:w-fit text-indigo-800 rounded shadow-sm shadow-indigo-600 border-indigo-600 border'}))
    name = django_filters.CharFilter(label="DRUG",field_name='generic_name', lookup_expr='icontains')    
    dosage_form = django_filters.ChoiceFilter(label="DOSAGE FORM",field_name='dosage_form',choices=Drug.dosage, lookup_expr='iexact',widget=forms.Select(attrs={'class': 'text-center text-xs focus:outline-none w-1/3 sm:w-fit text-indigo-800 rounded shadow-sm shadow-indigo-600 border-indigo-600 border'}))
    generic_name = django_filters.CharFilter(label="GENERIC NAME",field_name='generic_name', lookup_expr='icontains')
    trade_name = django_filters.CharFilter(label="TRADE NAME",field_name='trade_name', lookup_expr='icontains')
    supplier = django_filters.CharFilter(label="SUPPLIER",field_name='supplier', lookup_expr='icontains')
    supply_date1 = django_filters.DateFilter(label="SUPPLY DATE R1",field_name='supply_date',lookup_expr='gte',widget=forms.DateInput(attrs={'type':'date'}),input_formats=['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y'])    
    supply_date2 = django_filters.DateFilter(label="SUPPLY DATE R2",field_name='supply_date',lookup_expr='lte',widget=forms.DateInput(attrs={'type':'date'}),input_formats=['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y'])
    pack_size = django_filters.CharFilter(label="PACK SIZE",field_name='pack_size', lookup_expr='icontains')
    expiration_date1 = django_filters.DateFilter(label="EXPIRY DATE R1",field_name='expiration_date',lookup_expr='gte',widget=forms.DateInput(attrs={'type':'date'}),input_formats=['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y'])
    expiration_date2 = django_filters.DateFilter(label="EXPIRY DATE R2",field_name='expiration_date',lookup_expr='lte',widget=forms.DateInput(attrs={'type':'date'}),input_formats=['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y'])        
    added_by = django_filters.CharFilter(label="ADDED BY",field_name='added_by__username', lookup_expr='iexact')
   
    class Meta:
        model = Drug
        exclude= ['date_added','supply_date','total_value','cost_price','updated_at','expiration_date','total_purchased_quantity',]


class RecordFilter(django_filters.FilterSet):
    generic_name = django_filters.CharFilter(label="GENERIC NAME",field_name='drug__generic_name', lookup_expr='icontains')
    trade_name = django_filters.CharFilter(label="TRADE NAME",field_name='drug__trade_name', lookup_expr='icontains')
    category = django_filters.ChoiceFilter(label="CLASS", field_name='drug__category__name', lookup_expr='iexact', choices=Category.DRUG_CLASSES,
                                           widget=forms.Select(attrs={'class': 'text-center text-xs focus:outline-none w-1/3 sm:w-fit text-indigo-800 rounded shadow-sm shadow-indigo-600 border-indigo-600 border'}))
    supplier = django_filters.CharFilter(label="SUPPLIER",field_name='drug__supplier', lookup_expr='icontains')
    unit_issued_to = django_filters.ModelChoiceFilter(
        label="UNIT ISSUED TO",
        queryset=Unit.objects.all(),
        field_name='unit_issued_to',
        to_field_name='id', lookup_expr='exact',widget=forms.Select(attrs={'class': 'text-center text-xs focus:outline-none w-1/3 sm:w-fit text-indigo-800 rounded shadow-sm shadow-indigo-600 border-indigo-600 border'}))
    date_issued1 = django_filters.DateFilter(label="DATE ISSUED R1",field_name='date_issued',lookup_expr='gte',widget=forms.DateInput(attrs={'type':'date'}),input_formats=['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y'])    
    date_issued2 = django_filters.DateFilter(label="DATE ISSUED R2",field_name='date_issued',lookup_expr='lte',widget=forms.DateInput(attrs={'type':'date'}),input_formats=['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y'])
    issued_by = django_filters.CharFilter(label="ISSUED BY",field_name='issued_by__username', lookup_expr='iexact')

    class Meta:
        model = Record
        exclude= ['date_issued','drug','balance','siv','srv','invoice_no','updated_at','remark','quantity']


class RestockFilter(django_filters.FilterSet):
    date1 = django_filters.DateFilter(label="DATE R1",field_name='date',lookup_expr='gte',widget=forms.DateInput(attrs={'type':'date'}),input_formats=['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y'])
    date2 = django_filters.DateFilter(label="DATE R2",field_name='date',lookup_expr='lte',widget=forms.DateInput(attrs={'type':'date'}),input_formats=['%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y'])    
    category = django_filters.ChoiceFilter(label="CATEGORY",field_name='drug__category__name', lookup_expr='iexact', choices=Category.DRUG_CLASSES,
                                           widget=forms.Select(attrs={'class': 'text-center text-xs focus:outline-none w-1/3 sm:w-fit text-indigo-800 rounded shadow-sm shadow-indigo-600 border-indigo-600 border'}))
    drug = django_filters.CharFilter(label="DRUG",field_name='drug__name', lookup_expr='icontains')

    class Meta:
        model = Restock
        exclude= ['updated','date','quantity','restocked_by']