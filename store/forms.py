from django import forms
from .models import *
from django.forms import DateInput

class DrugForm(forms.ModelForm):
    expiration_date=forms.DateField(widget=forms.DateInput(attrs={'type':'date'}))
    
    class Meta:
        model = Drug
        fields = ['name','generic_name','brand_name','category','supplier','dosage_form','pack_size','cost_price','total_purchased_quantity','supply_date','expiration_date']  
        widgets = {
            'date': DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        super(DrugForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required=True    
            field.widget.attrs.update({'class':'text-center text-xs md:text-sm focus:outline-none border border-blue-300 p-2 sm:p-3 rounded shadow-lg hover:shadow-xl p-2'})



class RecordForm(forms.ModelForm):
    class Meta:
        model = Record
        fields = ['category', 'drug', 'unit_issued_to', 'quantity', 'date_issued']
        widgets = {
            'date_issued': DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].widget.attrs.update({'onchange': 'load_drugs()'})
        for field in self.fields.values():
            field.required = True
            field.widget.attrs.update({'class': 'text-center text-sm focus:outline-none border border-blue-300 p-3 rounded shadow-lg hover:shadow-xl'})

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        drug = cleaned_data.get('drug')

        if drug and quantity:
            available_quantity = drug.current_balance
            if quantity > available_quantity:
                if available_quantity > 0:
                    # Raise a non-field error to display a warning
                    self.add_error(None, f"Warning: Only {available_quantity} units available. The issued quantity will be adjusted.")
                else:
                    raise ValidationError("Not enough drugs available in the store.")
            
        return cleaned_data    
    
class RestockForm(forms.ModelForm):
    class Meta:
        model = Restock
        fields = ['category', 'drug', 'quantity', 'date']
        widgets = {
            'date': DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].widget.attrs.update({'onchange': 'load_drugs()'})
        for field in self.fields.values():
            field.required = True
            field.widget.attrs.update({
                'class': 'text-center text-sm focus:outline-none border border-blue-300 p-3 rounded shadow-lg hover:shadow-xl'
            })