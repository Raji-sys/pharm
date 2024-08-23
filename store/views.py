from .filters import *
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
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404, redirect, HttpResponseRedirect
from django.db.models import Case, When, Value, CharField, Q
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from .models import Unit
from decimal import Decimal


def group_required(group_name):
    def decorator(view_func):
        @login_required
        @user_passes_test(lambda u: u.groups.filter(name=group_name).exists())
        def _wrapped_view(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def unit_group_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        unit_id = kwargs.get('unit_id')  # Use 'unit_id' instead of 'pk'
        if unit_id is None:
            raise PermissionDenied

        unit = Unit.objects.get(pk=unit_id)
        if request.user.groups.filter(name=unit.name).exists():
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return login_required(_wrapped_view)

class UnitGroupRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if hasattr(self, 'get_unit_for_mixin'):
            unit = self.get_unit_for_mixin()
        else:
            unit = get_object_or_404(Unit, pk=self.kwargs['pk'])
        return self.request.user.groups.filter(name=unit.name).exists()
    
class CustomLoginView(LoginView):
    template_name='login.html'
    success_url=reverse_lazy('/')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)


@login_required
def index(request):
    today = timezone.now().date()
    six_months_later = today + timedelta(days=180)

    expiring_drugs_count = Drug.objects.filter(
        expiration_date__gt=today,
        expiration_date__lte=six_months_later
    ).count()

    context = {
        'expiring_drugs_count': expiring_drugs_count
    }
    return render(request, 'store/index.html', context)


class StoreGroupRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.groups.filter(name='STORE').exists()
    
class MainStoreDashboardView(LoginRequiredMixin, StoreGroupRequiredMixin,TemplateView):
    template_name = 'store/main_store_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        six_months_later = today + timedelta(days=180)

        expiring_drugs_count = Drug.objects.filter(
            expiration_date__gt=today,
            expiration_date__lte=six_months_later
        ).count()
        context['expiring_drugs_count'] = expiring_drugs_count
        return context


@group_required('STORE')
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


@group_required('STORE')
def drugs_list(request):
    drugs = Drug.objects.all().order_by('category')
    query = request.GET.get('q')
    
    if query:
        drugs = drugs.filter(
            Q(generic_name__icontains=query) | Q(trade_name__icontains=query)
        )
    
    today = timezone.now().date()
    one_month_later = today + timedelta(days=31)
    three_months_later = today + timedelta(days=90)
    six_months_later = today + timedelta(days=180)
    
    for drug in drugs:
        if drug.expiration_date:
            if drug.expiration_date <= today:
                drug.expiry_status = 'expired'  # Drug has expired
            elif drug.expiration_date <= one_month_later:
                drug.expiry_status = 'urgent'  # Expiring within 31 days
            elif drug.expiration_date <= three_months_later:
                drug.expiry_status = 'critical'  # Expiring within 3 months
            elif drug.expiration_date <= six_months_later:
                drug.expiry_status = 'expiring_soon'  # Expiring within 6 months
            else:
                drug.expiry_status = 'ok'
        else:
            drug.expiry_status = 'unknown'
    
    paginator = Paginator(drugs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'po': page_obj,
        'query': query,
        'total_expiring_in_6_months': drugs.filter(expiration_date__lte=six_months_later).count(),
        'total_expiring_in_3_months': drugs.filter(expiration_date__lte=three_months_later).count(),
        'total_expiring_in_1_month': drugs.filter(expiration_date__lte=one_month_later).count(),
    }
    return render(request, 'store/items_list.html', context)



class DrugUpdateView(LoginRequiredMixin, StoreGroupRequiredMixin, UpdateView):
    model=Drug
    form_class=DrugForm
    template_name='store/create_item.html'
    success_url=reverse_lazy('list')
  
    def form_valid(self, form):
        form.instance.added_by = self.request.user
        messages.success(self.request, "Drug updated successfully.")
        return super().form_valid(form)


class ExpiryNotificationView(LoginRequiredMixin, ListView):
    model = Drug
    template_name = 'store/expiry_notification.html'
    context_object_name = 'drugs'
    paginate_by = 10

    def get_queryset(self):
        today = timezone.now().date()
        six_months_later = today + timedelta(days=180)

        # Annotate the queryset with an expiration status
        queryset = Drug.objects.filter(
            expiration_date__lte=six_months_later
        ).annotate(
            status=Case(
                When(expiration_date__lte=today, then=Value('expired')),
                When(expiration_date__lte=today + timedelta(days=31), then=Value('urgent')),
                When(expiration_date__lte=today + timedelta(days=90), then=Value('critical')),
                When(expiration_date__lte=six_months_later, then=Value('expiring_soon')),
                default=Value('ok'),
                output_field=CharField(),
            )
        ).order_by('expiration_date')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        one_month_later = today + timedelta(days=31)
        three_months_later = today + timedelta(days=90)
        six_months_later = today + timedelta(days=180)

        queryset = self.get_queryset()

        context['total_expired'] = queryset.filter(expiration_date__lte=today).count()
        context['total_expiring_in_1_month'] = queryset.filter(expiration_date__gt=today, expiration_date__lte=one_month_later).count()
        context['total_expiring_in_3_months'] = queryset.filter(expiration_date__gt=one_month_later, expiration_date__lte=three_months_later).count()
        context['total_expiring_in_6_months'] = queryset.filter(expiration_date__gt=three_months_later, expiration_date__lte=six_months_later).count()

        return context



@group_required('STORE')
def drug_report(request):
    drugfilter=DrugFilter(request.GET, queryset=Drug.objects.all().order_by('generic_name'))    
    filtered_queryset = drugfilter.qs

    # Calculate total quantity across all filtered records
    total_quantity = filtered_queryset.aggregate(models.Sum('total_purchased_quantity'))['total_purchased_quantity__sum'] or 0
    
        # Attempt to get the cost price of the first drug in the filtered queryset
    first_drug_cost = Decimal('0')
    if filtered_queryset.exists():
        first_drug = filtered_queryset.first()
        if first_drug and first_drug.cost_price is not None:
            first_drug_cost = first_drug.cost_price

    # Calculate total price (assuming all drugs have the same price as the first one)
    total_price = total_quantity * first_drug_cost

    # Count the number of records in the filtered queryset
    total_appearance = filtered_queryset.count()

    pgtn=drugfilter.qs
    pgn=Paginator(pgtn,10)
    pn=request.GET.get('page')
    po=pgn.get_page(pn)

    context = {
        'drugfilter': drugfilter,
        'po':po,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,

               }
    return render(request, 'store/item_report.html', context)


@group_required('STORE')
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


@group_required('STORE')
def records(request):
    records = Record.objects.all().order_by('-updated_at')
    pgn=Paginator(records,10)
    pn=request.GET.get('page')
    po=pgn.get_page(pn)

    context = {'records': records, 'po':po}
    return render(request, 'store/record.html', context)


class RecordUpdateView(LoginRequiredMixin, StoreGroupRequiredMixin, UpdateView):
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


@group_required('STORE')
def record_report(request):
    # Apply the filter to all records, ordered by most recently updated
    recordfilter = RecordFilter(request.GET, queryset=Record.objects.all().order_by('-updated_at'))
    filtered_queryset = recordfilter.qs

    # Calculate total quantity across all filtered records
    total_quantity = filtered_queryset.aggregate(models.Sum('quantity'))['quantity__sum'] or 0

    # Attempt to get the cost price of the first drug in the filtered queryset
    first_drug_cost = Decimal('0')
    if filtered_queryset.exists():
        first_drug = filtered_queryset.first().drug
        if first_drug and first_drug.cost_price is not None:
            first_drug_cost = first_drug.cost_price

    # Calculate total price (assuming all drugs have the same price as the first one)
    total_price = total_quantity * first_drug_cost

    # Count the number of records in the filtered queryset
    total_appearance = filtered_queryset.count()

    # Paginate the results
    paginator = Paginator(filtered_queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'recordfilter': recordfilter,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'page_obj': page_obj
    }

    return render(request, 'store/record_report.html', context)


@group_required('STORE')
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


class RestockUpdateView(LoginRequiredMixin, StoreGroupRequiredMixin,UpdateView):
    model=Restock
    form_class=RestockForm
    template_name='store/update_restock.html'
    success_url=reverse_lazy('restocked')
    success_message = "Drug restocked successfully."
    
    def form_valid(self, form):
        form.instance.restocked_by = self.request.user
        return super().form_valid(form)
    

@group_required('STORE')
def restocked_list(request):
    restock = Restock.objects.all().order_by('-updated')
    pgn=Paginator(restock,10)
    pn=request.GET.get('page')
    po=pgn.get_page(pn)

    context = {'restock': restock, 'po':po}
    return render(request, 'store/restocked_list.html', context)
    

@group_required('STORE')
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

def generate_pdf(context, template_name):
    template = get_template(template_name)
    html = template.render(context)
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer, encoding='utf-8', link_callback=fetch_resources)
    
    if pisa_status.err:
        return None
    
    buffer.seek(0)
    return buffer

def pdf_generator(buffer):
    chunk_size = 8192
    while True:
        chunk = buffer.read(chunk_size)
        if not chunk:
            break
        yield chunk


@group_required('STORE')
def drug_pdf(request):
    ndate = datetime.datetime.now()
    filename = ndate.strftime('on_%d_%m_%Y_at_%I_%M%p.pdf')
    drugfilter = DrugFilter(request.GET, queryset=Drug.objects.all().order_by('-updated_at'))
    f = drugfilter.qs
    keys = [key for key, value in request.GET.items() if value]
    result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"
    context = {'f': f, 'pagesize': 'A4', 'orientation': 'Portrait', 'result': result, 'keys': keys}
    
    pdf_buffer = generate_pdf(context, 'store/item_pdf.html')
    
    if pdf_buffer is None:
        return HttpResponse('Error generating PDF', status=500)
    
    response = StreamingHttpResponse(pdf_generator(pdf_buffer), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="gen_by_{request.user}_{filename}"'
    return response


@group_required('STORE')
def record_pdf(request):
    ndate = datetime.datetime.now()
    filename = ndate.strftime('on_%d_%m_%Y_at_%I_%M%p.pdf')
    f = RecordFilter(request.GET, queryset=Record.objects.all()).qs
    total_quantity = f.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    
    if f.exists() and f.first().drug.cost_price:
        first_drug = f.first().drug.cost_price
    else:
        first_drug = 0
    
    total_price = total_quantity * first_drug
    total_appearance = f.count()
    keys = [key for key, value in request.GET.items() if value]
    result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"
    
    context = {
        'f': f,
        'pagesize': 'A4',
        'orientation': 'Portrait',
        'result': result,
        'keys': keys,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
    }
    
    pdf_buffer = generate_pdf(context, 'store/record_pdf.html')
    
    if pdf_buffer is None:
        return HttpResponse('Error generating PDF', status=500)
    
    response = StreamingHttpResponse(pdf_generator(pdf_buffer), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="gen_by_{request.user}_{filename}"'
    return response


@group_required('STORE')
def restock_pdf(request):
    ndate = datetime.datetime.now()
    filename = ndate.strftime('on_%d_%m_%Y_at_%I_%M%p.pdf')
    f = RestockFilter(request.GET, queryset=Restock.objects.all()).qs
    total_quantity = f.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    
    if f.exists() and f.first().drug.cost_price:
        first_drug = f.first().drug.cost_price
    else:
        first_drug = 0
    
    total_price = total_quantity * first_drug
    total_appearance = f.count()
    keys = [key for key, value in request.GET.items() if value]
    result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"
    
    context = {
        'f': f,
        'pagesize': 'A4',
        'orientation': 'Portrait',
        'result': result,
        'keys': keys,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
    }
    
    pdf_buffer = generate_pdf(context, 'store/restock_pdf.html')
    
    if pdf_buffer is None:
        return HttpResponse('Error generating PDF', status=500)
    
    response = StreamingHttpResponse(pdf_generator(pdf_buffer), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="gen_by_{request.user}_{filename}"'
    return response


class InventoryWorthView(LoginRequiredMixin, TemplateView):
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


class StoreListView(LoginRequiredMixin, ListView):
    model = Unit
    template_name = 'store/store_list.html'
    context_object_name = 'stores'
    paginate_by = 10  # Adjust as needed

    def get_queryset(self):
        return Unit.objects.all().order_by('name')
    

class UnitDashboardView(LoginRequiredMixin, UnitGroupRequiredMixin,DetailView):
    model = Unit
    template_name = 'store/unit_dashboard.html'
    context_object_name = 'store'


class UnitBulkLockerDetailView(LoginRequiredMixin, UnitGroupRequiredMixin, DetailView):
    model = Unit
    template_name = 'store/unit_bulk_locker.html'
    context_object_name = 'store'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit_store_drugs = UnitStore.objects.filter(unit=self.object).select_related('drug')

        today = timezone.now().date()
        one_month_later = today + timedelta(days=31)
        three_months_later = today + timedelta(days=90)
        six_months_later = today + timedelta(days=180)

        total_worth = 0
        total_expiring_in_1_month = 0
        total_expiring_in_3_months = 0
        total_expiring_in_6_months = 0

        for unit_store_drug in unit_store_drugs:
            total_worth += unit_store_drug.total_value

            # Assign restock info if available
            unit_store_drug.restock_info = Restock.objects.filter(drug=unit_store_drug.drug).order_by('-date').first()

            # Calculate expiry status for original drug (removed as we'll handle this in the template)
            if unit_store_drug.drug.expiration_date:
                if unit_store_drug.drug.expiration_date <= one_month_later:
                    total_expiring_in_1_month += unit_store_drug.quantity
                elif unit_store_drug.drug.expiration_date <= three_months_later:
                    total_expiring_in_3_months += unit_store_drug.quantity
                elif unit_store_drug.drug.expiration_date <= six_months_later:
                    total_expiring_in_6_months += unit_store_drug.quantity

            # Calculate expiry status for restocked drug (if required)
            if unit_store_drug.restock_info and unit_store_drug.restock_info.expiration_date:
                # Optionally process restock expiry status in the template
                pass

        # Order by generic name
        context['unit_store_drugs'] = unit_store_drugs.order_by('drug__generic_name')
        context['total_worth'] = total_worth
        context['total_expiring_in_6_months'] = total_expiring_in_6_months
        context['total_expiring_in_3_months'] = total_expiring_in_3_months
        context['total_expiring_in_1_month'] = total_expiring_in_1_month

        # Pass date ranges to the template for comparison
        context['today'] = today
        context['one_month_later'] = one_month_later
        context['three_months_later'] = three_months_later
        context['six_months_later'] = six_months_later

        return context


class UnitDispensaryLockerView(LoginRequiredMixin, UnitGroupRequiredMixin, DetailView):
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

class UnitTransferView(LoginRequiredMixin,UnitGroupRequiredMixin,DetailView):
    model = Unit
    template_name = 'store/unit_transfer.html'
    context_object_name = 'store'
    paginate_by=10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch unit issue records where this unit is the issuing unit
        context['unit_issue_records'] = UnitIssueRecord.objects.filter(unit=self.object,issued_to__isnull=False, issued_to_locker__isnull=True).order_by('-date_issued')
        return context


@unit_group_required
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
    
    UnitIssueFormSet = modelformset_factory(
        UnitIssueRecord,
        form=UnitIssueRecordForm,
        formset=CustomUnitIssueFormSet,
        extra=2
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
            initial=[{'unit': unit}] * 2
        )

    return render(request, 'store/unitissuerecord_form.html', {'formset': formset, 'unit': unit})    

class TransferUpdateView(LoginRequiredMixin,UnitGroupRequiredMixin,UpdateView):
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


@unit_group_required
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
        extra=2
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
            initial=[{'unit': unit, 'issued_to_locker': unit_locker}] * 2
        )

    return render(request, 'store/create_dispensary_record.html', {'formset': formset, 'unit': unit})


class UnitIssueRecordListView(LoginRequiredMixin,UnitGroupRequiredMixin,ListView):
    model = UnitIssueRecord
    template_name = 'store/unitissuerecord_list.html'
    context_object_name = 'unit_issue_records'
    paginate_by = 10  # Optional: for pagination

    def get_queryset(self):
        return DispenseRecord.objects.all().order_by('-date_issued')
    

@login_required
def dispenserecord(request, dispensary_id):
    dispensary = get_object_or_404(DispensaryLocker, id=dispensary_id)
    DispensaryFormSet = modelformset_factory(DispenseRecord, form=DispenseRecordForm, extra=2)
    
    if request.method == 'POST':
        formset = DispensaryFormSet(request.POST, queryset=DispenseRecord.objects.none(), form_kwargs={'dispensary': dispensary})
        if formset.is_valid():
            try:
                with transaction.atomic():
                    instances = formset.save(commit=False)
                    for instance in instances:
                        instance.dispensary = dispensary
                        instance.dispensed_by = request.user
                        instance.save()

                    messages.success(request, 'Drugs dispensed successfully')
                    return redirect('unit_dispensary', pk=dispensary.unit.id)
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        formset = DispensaryFormSet(queryset=DispenseRecord.objects.none(), form_kwargs={'dispensary': dispensary})
    return render(request, 'store/dispense_form.html', {'formset': formset, 'dispensary': dispensary})


class DispenseRecordView(LoginRequiredMixin, UnitGroupRequiredMixin, ListView):
    model = DispenseRecord
    template_name = 'store/dispensed_list.html'
    context_object_name = 'dispensed_list'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        self.dispensary_locker = get_object_or_404(DispensaryLocker, pk=kwargs['pk'])
        self.unit = self.dispensary_locker.unit  # Assuming DispensaryLocker has a relation to Unit
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return DispenseRecord.objects.filter(dispensary=self.dispensary_locker).order_by('-updated')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_dispensed'] = self.get_queryset().count()
        context['dispensary_locker'] = self.dispensary_locker
        return context

    def get_unit_for_mixin(self):
        return self.unit
    
    
@login_required
def dispense_report(request, pk):
    dispensary = get_object_or_404(DispensaryLocker, id=pk)
    
    # Initialize the filter with the queryset and manually set the initial value
    dispensefilter = DispenseFilter(request.GET, queryset=DispenseRecord.objects.filter(dispensary=dispensary).order_by('-updated'))
    
    # Set initial value for the dispensary filter
    dispensefilter.form.initial['dispensary'] = pk
    
    filtered_queryset = dispensefilter.qs
    total_quantity = filtered_queryset.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    if filtered_queryset.exists() and filtered_queryset.first().drug.selling_price:
        first_drug = filtered_queryset.first().drug.selling_price
    else:
        first_drug = 0

    total_price = total_quantity * first_drug
    total_appearance = filtered_queryset.count()

    pgn = Paginator(filtered_queryset, 10)
    pn = request.GET.get('page')
    po = pgn.get_page(pn)

    context = {
        'dispensary':dispensary,
        'dispensefilter': dispensefilter,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'po': po
    }
    return render(request, 'store/dispense_report.html', context)


@login_required
def dispense_pdf(request):
    ndate = datetime.datetime.now()
    filename = ndate.strftime('on_%d_%m_%Y_at_%I_%M%p.pdf')
    f = DispenseFilter(request.GET, queryset=DispenseRecord.objects.all()).qs
    total_quantity = f.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    
    if f.exists() and f.first().drug.selling_price:
        first_drug = f.first().drug.selling_price
    else:
        first_drug = 0
    
    total_price = total_quantity * first_drug
    total_appearance = f.count()
    keys = [key for key, value in request.GET.items() if value]
    result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"
    
    context = {
        'f': f,
        'pagesize': 'A4',
        'orientation': 'Portrait',
        'result': result,
        'keys': keys,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
    }
    
    pdf_buffer = generate_pdf(context, 'store/dispense_pdf.html')
    
    if pdf_buffer is None:
        return HttpResponse('Error generating PDF', status=500)
    
    response = StreamingHttpResponse(pdf_generator(pdf_buffer), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="gen_by_{request.user}_{filename}"'
    return response