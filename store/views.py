from .filters import DrugFilter, RecordFilter, RestockFilter, DrugSearchFilter
from django.shortcuts import render, redirect
from .forms import *
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from .models import *
import datetime
from django.http import HttpResponse
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings
import os
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.forms import modelformset_factory, BaseModelFormSet
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.generic import UpdateView, ListView, DetailView, CreateView, TemplateView
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect, HttpResponseRedirect

class CustomLoginView(LoginView):
    template_name='login.html'
    success_url=reverse_lazy('/')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)

@login_required
def index(request):
    return render(request, 'store/index.html')

@login_required
def create_drug(request):
    if request.method == 'POST':
        form = DrugForm(request.POST)
        if form.is_valid():
            new_drug=form.save(commit=False)
            new_drug.added_by=request.user
            new_drug.save()
            messages.success(request,'drug added to inventory')
            return redirect('list')
    else:
        form = DrugForm()
    return render(request, 'store/create_item.html', {'form': form})

@login_required
def drugs_list(request):
    drugs = Drug.objects.all().order_by('category')
    today = timezone.now().date()
    six_months_later = today + timedelta(days=180)
    
    for drug in drugs:
        if drug.expiration_date:
            drug.expires_soon = drug.expiration_date <= six_months_later
        else:
            drug.expires_soon = False
          
    drugsearchfilter=DrugSearchFilter(request.GET, queryset=Drug.objects.all().order_by('category'))    
    pgtn=drugsearchfilter.qs
    pgn=Paginator(pgtn,10)

    pn=request.GET.get('page')
    po=pgn.get_page(pn)

    context = {'drugsearchfilter': drugsearchfilter,'po':po}
    return render(request, 'store/items_list.html', context)


class DrugUpdateView(UpdateView):
    model=Drug
    form_class=DrugForm
    template_name='store/create_item.html'
    success_url=reverse_lazy('list')
  
    def form_valid(self, form):
        form.instance.added_by = self.request.user
        messages.success(self.request, "Drug updated successfully.")
        return super().form_valid(form)

@login_required
def drug_report(request):
    drugfilter=DrugFilter(request.GET, queryset=Drug.objects.all().order_by('category'))    
    pgtn=drugfilter.qs
    pgn=Paginator(pgtn,10)
    pn=request.GET.get('page')
    po=pgn.get_page(pn)

    context = {'drugfilter': drugfilter,'po':po}
    return render(request, 'store/item_report.html', context)


@login_required
def create_record(request):
    RecordFormSet = modelformset_factory(Record, form=RecordForm, extra=5)
    if request.method == 'POST':
        formset = RecordFormSet(request.POST)
        if formset.is_valid():
            try:
                with transaction.atomic():
                    instances = formset.save(commit=False)
                    any_saved = False
                    for instance in instances:
                        if instance.drug and instance.quantity:
                            instance.issued_by = request.user
                            instance.save()
                            any_saved = True
                    if any_saved:
                        messages.success(request, 'Drugs issued successfully.')
                        return redirect('record')
                    else:
                        messages.warning(request, 'No drugs were issued. Please fill in at least one form.')
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        formset = RecordFormSet(queryset=Record.objects.none())
    
    return render(request, 'store/create_record.html', {'formset': formset})

@login_required
def records(request):
    records = Record.objects.all().order_by('-updated_at')
    pgn=Paginator(records,10)
    pn=request.GET.get('page')
    po=pgn.get_page(pn)

    context = {'records': records, 'po':po}
    return render(request, 'store/record.html', context)


class RecordUpdateView(UpdateView):
    model = Record
    form_class = RecordForm
    template_name = 'store/update_record.html'
    success_url = reverse_lazy('record')

    def form_valid(self, form):
        try:
            form.instance.issued_by = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, "Record updated successfully.")
            return response
        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error updating the record. Please check the form.")
        return super().form_invalid(form)

def get_drugs_by_category(request, category_id):
    drugs = Drug.objects.filter(category_id=category_id)
    drug_list = [{'id': drug.id, 'name': drug.generic_name} for drug in drugs]
    return JsonResponse({'drugs': drug_list})


@login_required
def record_report(request):
    recordfilter = RecordFilter(request.GET, queryset=Record.objects.all().order_by('-updated_at'))
    filtered_queryset = recordfilter.qs
    total_quantity = filtered_queryset.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    
    if filtered_queryset.exists():
        first_drug = filtered_queryset.first().drug.cost_price
        if first_drug is None:
            first_drug = 0
    else:
        first_drug = 0
    
    total_price = total_quantity * first_drug
    total_appearance = filtered_queryset.count()
    pgn = Paginator(filtered_queryset, 10)
    pn = request.GET.get('page')
    po = pgn.get_page(pn)
    
    context = {
        'recordfilter': recordfilter,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'po': po
    }
    return render(request, 'store/record_report.html', context)

@login_required
def restock(request):
    RestockFormSet = modelformset_factory(Restock, form=RestockForm, extra=5)

    if request.method == 'POST':
        formset = RestockFormSet(request.POST)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.restocked_by = request.user
                instance.save()
            messages.success(request,'drugs restocked')
            return redirect('restocked')
    else:
        formset = RestockFormSet(queryset=Restock.objects.none())

    return render(request, 'store/restock.html', {'formset': formset})


class RestockUpdateView(UpdateView):
    model=Restock
    form_class=RestockForm
    template_name='store/update_restock.html'
    success_url=reverse_lazy('restocked')
    success_message = "Drug restocked successfully."
    
    def form_valid(self, form):
        form.instance.restocked_by = self.request.user
        return super().form_valid(form)
    
@login_required
def restocked_list(request):
    restock = Restock.objects.all().order_by('-updated')
    pgn=Paginator(restock,10)
    pn=request.GET.get('page')
    po=pgn.get_page(pn)

    context = {'restock': restock, 'po':po}
    return render(request, 'store/restocked_list.html', context)
    

@login_required
def restock_report(request):
    restockfilter = RestockFilter(request.GET, queryset=Restock.objects.all().order_by('-updated'))
    filtered_queryset = restockfilter.qs
    total_quantity = filtered_queryset.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    if filtered_queryset.exists() and filtered_queryset.first().drug.cost_price:
        first_drug=filtered_queryset.first().drug.cost_price
    else:
        first_drug=0
    total_price=total_quantity*first_drug
    total_appearance=filtered_queryset.count()
    pgn=Paginator(filtered_queryset,10)
    pn=request.GET.get('page')
    po=pgn.get_page(pn)

    context = {
        'restockfilter': restockfilter,
        'total_appearance': total_appearance,
        'total_price':total_price,
        'total_quantity':total_quantity,
        'po':po
    }
    return render(request, 'store/restock_report.html', context)


def fetch_resources(uri, rel):
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    else:
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    return path


@login_required
def drug_pdf(request):
    ndate = datetime.datetime.now()
    filename = ndate.strftime('on_%d/%m/%Y_at_%I.%M%p.pdf')
    drugfilter = DrugFilter(request.GET, queryset=Drug.objects.all().order_by('-updated_at'))
    f=drugfilter.qs
    keys = [key for key, value in request.GET.items() if value]

    result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"

    context = {'f': f, 'pagesize': 'A4', 'orientation': 'Potrait','result':result,'keys':keys}

    response = HttpResponse(content_type='application/pdf', headers={'Content-Disposition': f'filename="gen_by_{request.user}_{filename}"'})
    buffer = BytesIO()

    pisa_status = pisa.CreatePDF(get_template('store/item_pdf.html').render(context), dest=buffer, encoding='utf-8', link_callback=fetch_resources)

    if not pisa_status.err:
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response
    return HttpResponse('Error generating PDF', status=500)


@login_required
def record_pdf(request):
    ndate = datetime.datetime.now()
    filename = ndate.strftime('on_%d/%m/%Y_at_%I.%M%p.pdf')
    f = RecordFilter(request.GET, queryset=Record.objects.all()).qs
    
    total_quantity = f.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    if f.exists() and f.first().drug.cost_price:
        first_drug=f.first().drug.cost_price
    else:
        first_drug=0
        
    total_price=total_quantity*first_drug
    total_appearance=f.count()
    keys = [key for key, value in request.GET.items() if value]
    result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"
    context = {'f': f, 'pagesize': 'A4', 'orientation': 'Potrait','result':result,'keys':keys,'total_appearance': total_appearance,'total_price':total_price,'total_quantity':total_quantity,}
    response = HttpResponse(content_type='application/pdf', headers={'Content-Disposition': f'filename="gen_by_{request.user}_{filename}"'})
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(get_template('store/record_pdf.html').render(context), dest=buffer, encoding='utf-8', link_callback=fetch_resources)

    if not pisa_status.err:
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response
    return HttpResponse('Error generating PDF', status=500)


@login_required
def restock_pdf(request):
    ndate = datetime.datetime.now()
    filename = ndate.strftime('on_%d/%m/%Y_at_%I.%M%p.pdf')
    f = RestockFilter(request.GET, queryset=Restock.objects.all()).qs
    
    total_quantity = f.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    if f.exists() and f.first().drug.cost_price:
        first_drug=f.first().drug.cost_price
    else:
        first_drug=0
        
    total_price=total_quantity*first_drug
    total_appearance=f.count()
    keys = [key for key, value in request.GET.items() if value]
    result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"
    context = {'f': f, 'pagesize': 'A4', 'orientation': 'Potrait','result':result,'keys':keys,'total_appearance': total_appearance,'total_price':total_price,'total_quantity':total_quantity,}
    response = HttpResponse(content_type='application/pdf', headers={'Content-Disposition': f'filename="gen_by_{request.user}_{filename}"'})
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(get_template('store/restock_pdf.html').render(context), dest=buffer, encoding='utf-8', link_callback=fetch_resources)

    if not pisa_status.err:
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response
    return HttpResponse('Error generating PDF', status=500)


class InventoryWorthView(TemplateView):
    template_name = 'store/worth.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.now()
        context['total_store_value'] = Drug.total_store_value()
        context['combined_unit_value'] = Unit.combined_unit_value()
        context['grand_total_value'] = Unit.grand_total_value()
        
        unit_worths = {}
        for unit in Unit.objects.all().order_by('name'):
            store_value = sum(store.total_value for store in unit.unit_store.all() if store.total_value is not None)
            locker_value = 0
            if hasattr(unit, 'dispensary_locker'):
                locker_value = unit.dispensary_locker.inventory.aggregate(
                    total=Sum(F('drug__cost_price') * F('quantity'))
                )['total'] or 0
            unit_worths[unit.name] = {
                'store_value': store_value,
                'locker_value': locker_value,
                'total_value': store_value + locker_value
            }
        
        context['unit_worths'] = unit_worths
        return context


class StoreListView(ListView):
    model = Unit
    template_name = 'store/store_list.html'
    context_object_name = 'stores'
    paginate_by = 10  # Adjust as needed

    def get_queryset(self):
        return Unit.objects.all().order_by('name')
    

class UnitDashboardView(DetailView):
    model = Unit
    template_name = 'store/unit_dashboard.html'
    context_object_name = 'store'


class UnitBulkLockerDetailView(DetailView):
    model = Unit
    template_name = 'store/unit_bulk_locker.html'
    context_object_name = 'store'
    paginate_by=10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit_store_drugs = UnitStore.objects.filter(unit=self.object).select_related('drug')
        # Calculate total worth by summing up the total_value of all UnitStore objects
        total_worth = sum(drug.total_value for drug in unit_store_drugs)
        # Fetch the drugs available in this store
        context['unit_store_drugs'] = UnitStore.objects.filter(unit=self.object).order_by('drug__generic_name')
        
        context['total_worth'] = total_worth
        return context

class UnitDispensaryLockerView(DetailView):
    model = Unit
    template_name = 'store/unit_dispensary_locker.html'
    context_object_name = 'store'
    paginate_by=10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dispensary_drugs = LockerInventory.objects.filter(locker__unit=self.object).select_related('drug')

     # Calculate total worth
        total_worth = dispensary_drugs.aggregate(
            total=Sum(F('drug__cost_price') * F('quantity'))
        )['total'] or 0        # Calculate total worth by summing up the total_value of all UnitStore objects
        # Fetch the drugs available in this store
        context['dispensary_drugs'] = LockerInventory.objects.filter(locker__unit=self.object).order_by('drug__generic_name')
        context['total_worth'] = total_worth
        return context

class UnitTransferView(DetailView):
    model = Unit
    template_name = 'store/unit_transfer.html'
    context_object_name = 'store'
    paginate_by=10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch unit issue records where this unit is the issuing unit
        context['unit_issue_records'] = UnitIssueRecord.objects.filter(unit=self.object,issued_to__isnull=False, issued_to_locker__isnull=True).order_by('-date_issued')
        return context


@login_required
def unitissuerecord(request, unit_id):
    unit = get_object_or_404(Unit, id=unit_id)
        # Create a custom formset that passes the issuing_unit to each form
    class CustomUnitIssueFormSet(BaseModelFormSet):
        def __init__(self, *args, **kwargs):
            self.issuing_unit = kwargs.pop('issuing_unit', None)
            super().__init__(*args, **kwargs)

        def _construct_form(self, i, **kwargs):
            kwargs['issuing_unit'] = self.issuing_unit
            return super()._construct_form(i, **kwargs)
    UnitIssueFormSet = modelformset_factory(UnitIssueRecord, form=UnitIssueRecordForm, formset=CustomUnitIssueFormSet, extra=1)

    if request.method == 'POST':
        formset = UnitIssueFormSet(request.POST, issuing_unit=unit)
        if formset.is_valid():
            try:
                with transaction.atomic():
                    instances = formset.save(commit=False)
                    for instance in instances:
                        instance.issued_by = request.user
                        instance.unit = unit
                        instance.save()
                        if instance.issued_to_locker:
                            locker_inventory, created = LockerInventory.objects.get_or_create(
                                locker=instance.issued_to_locker,
                                drug=instance.drug,
                                defaults={'quantity': 0}
                            )
                            locker_inventory.quantity += instance.quantity
                            locker_inventory.save()
                    messages.success(request, 'Drugs restocked')
                    return redirect('unit_transfer', pk=unit_id)
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        formset = UnitIssueFormSet(
            queryset=UnitIssueRecord.objects.none(),
            issuing_unit=unit,
            initial=[{'unit': unit}] * 1
        )

    return render(request, 'store/unitissuerecord_form.html', {'formset': formset, 'unit': unit})    

class TransferUpdateView(UpdateView):
    model = UnitIssueRecord
    form_class = UnitIssueRecordForm
    template_name = 'store/transfer_update.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['issuing_unit'] = self.object.unit
        return kwargs

    def get_success_url(self):
        return reverse_lazy('unit_transfer', kwargs={'pk': self.object.unit.pk})

    def form_valid(self, form):
        try:
            form.instance.issued_by = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, "Record updated successfully.")
            return response
        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error updating the record. Please check the form.")
        return super().form_invalid(form)


@login_required
def dispensaryissuerecord(request, unit_id):
    unit = get_object_or_404(Unit, id=unit_id)
    unit_locker = DispensaryLocker.objects.filter(unit=unit).first()

    class CustomUnitIssueFormSet(BaseModelFormSet):
        def __init__(self, *args, **kwargs):
            self.issuing_unit = kwargs.pop('issuing_unit', None)
            super().__init__(*args, **kwargs)

        def _construct_form(self, i, **kwargs):
            kwargs['issuing_unit'] = self.issuing_unit
            return super()._construct_form(i, **kwargs)

    UnitIssueFormSet = modelformset_factory(
        UnitIssueRecord,
        form=DispensaryIssueRecordForm,
        formset=CustomUnitIssueFormSet,
        extra=1
    )

    if request.method == 'POST':
        formset = UnitIssueFormSet(request.POST, issuing_unit=unit)
        if formset.is_valid():
            try:
                with transaction.atomic():
                    instances = formset.save(commit=False)
                    for instance in instances:
                        instance.issued_by = request.user
                        instance.unit = unit
                        instance.save()
                        # Update locker inventory if issued to locker
                        if instance.issued_to_locker:
                            locker_inventory, created = LockerInventory.objects.get_or_create(
                                locker=instance.issued_to_locker,
                                drug=instance.drug,
                                defaults={'quantity': 0}
                            )
                            locker_inventory.quantity += instance.quantity
                            locker_inventory.save()
                    messages.success(request, 'Drugs restocked')
                    return redirect('unit_bulk_locker', pk=unit_id)
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            for form in formset:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.capitalize()}: {error}")
    else:
        formset = UnitIssueFormSet(
            queryset=UnitIssueRecord.objects.none(),
            issuing_unit=unit,
            initial=[{'unit': unit, 'issued_to_locker': unit_locker}] * 1
        )

    return render(request, 'store/create_dispensary_record.html', {'formset': formset, 'unit': unit})



class UnitIssueRecordListView(ListView):
    model = UnitIssueRecord
    template_name = 'store/unitissuerecord_list.html'
    context_object_name = 'unit_issue_records'
    paginate_by = 10  # Optional: for pagination

    def get_queryset(self):
        return UnitIssueRecord.objects.all().order_by('-date_issued')