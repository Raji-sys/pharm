from django import forms
from .models import *
from django.forms import DateInput

class DrugForm(forms.ModelForm):
    expiration_date=forms.DateField(widget=forms.DateInput(attrs={'type':'date'}))
    
    class Meta:
        model = Drug
        fields = ['generic_name','trade_name','strength','category','supplier','dosage_form','pack_size','cost_price','selling_price','total_purchased_quantity','supply_date','expiration_date']  
        widgets = {
            'supply_date': DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        super(DrugForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required=True    
            field.widget.attrs.update({'class':'text-center text-xs md:text-xs focus:outline-none border border-blue-300 p-2 sm:p-3 rounded shadow-lg hover:shadow-xl p-2'})



class RecordForm(forms.ModelForm):
    class Meta:
        model = Record
        fields = ['category', 'drug', 'unit_issued_to', 'quantity']
        # widgets = {
        #     'date_issued': forms.DateInput(attrs={'type': 'date'})
        # }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].widget.attrs.update({'onchange': 'load_drugs()'})
        for field in self.fields.values():
            field.required = True
            field.widget.attrs.update({'class': 'text-center text-xs focus:outline-none border border-blue-300 p-3 rounded shadow-lg hover:shadow-xl'})

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        drug = cleaned_data.get('drug')
        if drug and quantity is not None:
            available_quantity = drug.current_balance
            # If this is an update, add back the original quantity
            if self.instance.pk:
                available_quantity += self.instance.quantity
            if quantity > available_quantity:
                if available_quantity > 0:
                    self.add_error('quantity', f"Warning: Only {available_quantity} units available. Please adjust the issued quantity.")
                else:
                    self.add_error('quantity', "Not enough available in the store.")
        return cleaned_data

class RestockForm(forms.ModelForm):
    class Meta:
        model = Restock
        fields = ['category', 'drug', 'quantity']
        # widgets = {
        #     'date': DateInput(attrs={'type': 'date'})
        # }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].widget.attrs.update({'onchange': 'load_drugs()'})
        for field in self.fields.values():
            field.required = True
            field.widget.attrs.update({
                'class': 'text-center text-xs focus:outline-none border border-blue-300 p-3 rounded shadow-lg hover:shadow-xl'
            })


class UnitIssueRecordForm(forms.ModelForm):
    class Meta:
        model = UnitIssueRecord
        fields = ['unit', 'category', 'drug', 'quantity', 'issued_to']
        # widgets = {
        #     'date_issued': forms.DateInput(attrs={'type': 'date'}),
        # }

    def __init__(self, *args, **kwargs):
        self.issuing_unit = kwargs.pop('issuing_unit', None)
        super(UnitIssueRecordForm, self).__init__(*args, **kwargs)
        self.fields['unit'].widget.attrs['readonly'] = True
        self.fields['category'].widget.attrs.update({'onchange': 'load_drugs()'})
        if self.issuing_unit:
            self.fields['issued_to'].queryset = Unit.objects.exclude(id=self.issuing_unit.id)
        for field in self.fields.values():
            field.required = False
            field.widget.attrs.update({'class':'text-center text-xs md:text-xs focus:outline-none border border-blue-300 p-2 sm:p-3 rounded shadow-lg hover:shadow-xl p-2'})

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is None:
            raise forms.ValidationError("Quantity is required.")
        if quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        unit = cleaned_data.get('unit')
        issued_to = cleaned_data.get('issued_to')
        issued_to_locker = cleaned_data.get('issued_to_locker')
        drug = cleaned_data.get('drug')
        quantity = cleaned_data.get('quantity')

        if issued_to and issued_to_locker:
            self.add_error(None, "Cannot issue to both a unit and a locker at the same time.")
        if not issued_to and not issued_to_locker:
            self.add_error(None, "Must issue to either a unit or a locker.")
        if unit and issued_to and unit == issued_to:
            self.add_error(None, "A unit cannot issue drugs to itself.")

        # Skip validation if any required field is missing
        if not all([unit, drug, quantity]):
            return cleaned_data

        # Validate that the unit has enough of the drug available
        unit_store = UnitStore.objects.filter(unit=unit, drug=drug).first()
        if not unit_store:
            self.add_error('drug', f"{drug.generic_name} is not available in {unit.name}'s store.")
        elif unit_store.quantity < quantity:
            self.add_error('quantity', f"Not enough {drug.generic_name} in {unit.name}'s store. Available: {unit_store.quantity}")

        return cleaned_data


class DispensaryIssueRecordForm(forms.ModelForm):
    class Meta:
        model = UnitIssueRecord
        fields = ['unit', 'category', 'drug', 'quantity', 'issued_to_locker']
        widgets = {
            'date_issued': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.issuing_unit = kwargs.pop('issuing_unit', None)
        super(DispensaryIssueRecordForm, self).__init__(*args, **kwargs)
        self.fields['unit'].widget.attrs['readonly'] = True
        self.fields['issued_to_locker'].widget.attrs['readonly'] = True
        self.fields['category'].widget.attrs.update({'onchange': 'load_drugs()'})
        if self.issuing_unit:
            self.fields['issued_to_locker'].queryset = DispensaryLocker.objects.filter(unit=self.issuing_unit)
        for field in self.fields.values():
            field.required = False
            field.widget.attrs.update({'class':'text-center text-xs md:text-xs focus:outline-none border border-blue-300 p-2 sm:p-3 rounded shadow-lg hover:shadow-xl p-2'})

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is None:
            raise forms.ValidationError("Quantity is required.")
        if quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        unit = cleaned_data.get('unit')
        issued_to = cleaned_data.get('issued_to')
        issued_to_locker = cleaned_data.get('issued_to_locker')
        drug = cleaned_data.get('drug')
        quantity = cleaned_data.get('quantity')

        if issued_to and issued_to_locker:
            self.add_error(None, "Cannot issue to both a unit and a locker at the same time.")
        if not issued_to and not issued_to_locker:
            self.add_error(None, "Must issue to either a unit or a locker.")
        if unit and issued_to and unit == issued_to:
            self.add_error(None, "A unit cannot issue drugs to itself.")

        # Skip validation if any required field is missing
        if not all([unit, drug, quantity]):
            return cleaned_data

        # Validate that the unit has enough of the drug available
        unit_store = UnitStore.objects.filter(unit=unit, drug=drug).first()
        if not unit_store:
            self.add_error('drug', f"{drug.generic_name} is not available in {unit.name}'s store.")
        elif unit_store.quantity < quantity:
            self.add_error('quantity', f"Not enough {drug.generic_name} in {unit.name}'s store. Available: {unit_store.quantity}")

        return cleaned_data
    


class DispenseRecordForm(forms.ModelForm):
    class Meta:
        model = DispenseRecord
        fields = ['category','drug', 'quantity', 'patient_info']

    def __init__(self, *args, **kwargs):
        self.dispensary = kwargs.pop('dispensary', None)
        super(DispenseRecordForm, self).__init__(*args, **kwargs)
        self.fields['category'].widget.attrs.update({'onchange': 'load_drugs()'})
        
        if self.dispensary:
            self.fields['drug'].queryset = Drug.objects.filter(
                lockerinventory__locker=self.dispensary,
                lockerinventory__quantity__gt=0
            ).distinct()

        for field in self.fields.values():
            field.widget.attrs.update({'class': 'text-center text-xs md:text-xs focus:outline-none border border-blue-300 p-2 sm:p-3 rounded shadow-lg hover:shadow-xl p-2'})

    def clean(self):
        cleaned_data = super().clean()
        drug = cleaned_data.get('drug')
        quantity = cleaned_data.get('quantity')

        if not drug or not quantity:
            return cleaned_data

        if quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")

        try:
            inventory = LockerInventory.objects.get(locker=self.dispensary, drug=drug)
            if quantity > inventory.quantity:
                raise forms.ValidationError(f"Not enough {drug} in inventory. Available: {inventory.quantity}")
        except LockerInventory.DoesNotExist:
            raise forms.ValidationError(f"{drug} is not available in this dispensary.")

        return cleaned_data