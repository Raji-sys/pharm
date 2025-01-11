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
from django.views.generic import UpdateView, ListView, DetailView, TemplateView, CreateView
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Case, When, Value, CharField, Q
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from .models import Unit
from decimal import Decimal
from django.db.models import Sum, F
from .models import LoginActivity
from datetime import datetime
from django.db.models import Sum, F
from django.urls import reverse

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
    
from django.utils.timezone import now, timedelta

class MainStoreDashboardView(LoginRequiredMixin, StoreGroupRequiredMixin, TemplateView):
    template_name = 'store/main_store_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        today = timezone.now().date()
        six_months_later = today + timedelta(days=180)
        
        # Count expiring drugs
        expiring_drugs_count = Drug.objects.filter(
            expiration_date__gt=today,
            expiration_date__lte=six_months_later
        ).count()
        context['expiring_drugs_count'] = expiring_drugs_count
        
        # Count recent DrugRequest instances
        last_24_hours = now() - timedelta(hours=24)
        recent_drug_request_count = DrugRequest.objects.filter(updated__gte=last_24_hours).count()
        context['recent_drug_request_count'] = recent_drug_request_count
        
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
            Q(generic_name__icontains=query) | Q(trade_name__icontains=query) | Q(category__name__icontains=query) | Q(dosage_form__icontains=query) | Q(strength__icontains=query) | Q(pack_size__icontains=query)
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
    form_class=DrugUpdateForm
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
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
            Q(generic_name__icontains=query) |
            Q(trade_name__icontains=query)|
            Q(category__name__icontains=query)|
            Q(drug__dosage_form__icontains=query)|
            Q(drug__strength__icontains=query)
            )

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
        context['query'] = self.request.GET.get('q', '')       

        return context



@group_required('STORE')
def drug_report(request):
    # Initialize filter and get filtered queryset
    drugfilter = DrugFilter(request.GET, queryset=Drug.objects.all().order_by('generic_name'))    
    filtered_queryset = drugfilter.qs

    # Count the number of records in the filtered queryset
    total_appearance = filtered_queryset.count()

    # Pagination
    pgn = Paginator(filtered_queryset, 10)
    pn = request.GET.get('page')
    po = pgn.get_page(pn)

    # Calculate totals using model properties
    total_purchased_quantity = filtered_queryset.aggregate(Sum('total_purchased_quantity'))['total_purchased_quantity__sum'] or 0
    total_issued = sum(drug.total_issued for drug in filtered_queryset)
    total_quantity = sum(drug.current_balance for drug in filtered_queryset)
    total_value = sum(drug.total_value for drug in filtered_queryset)

    context = {
        'drugfilter': drugfilter,
        'po': po,
        'total_appearance': total_appearance,
        'total_quantity': total_quantity,
        'total_value': total_value,
    }
    
    return render(request, 'store/item_report.html', context)


@group_required('STORE')
def records(request):
    records = Record.objects.all().order_by('-updated_at')
    # Search functionality
    query = request.GET.get('q')
    if query:
        records = records.filter(
            Q(drug__generic_name__icontains=query) |
            Q(drug__trade_name__icontains=query)|
            Q(category__name__icontains=query)|
            Q(unit_issued_to__name__icontains=query)|
            Q(drug__dosage_form__icontains=query)|
            Q(drug__strength__icontains=query)
        )

    pgn=Paginator(records,10)
    pn=request.GET.get('page')
    po=pgn.get_page(pn)

    context = {'records': records, 'po':po,'query':query or ''}
    return render(request, 'store/record.html', context)


@group_required('STORE')
def create_record(request):
    RecordFormSet = modelformset_factory(Record, form=RecordForm, extra=10)
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
            except ValidationError as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            messages.error(request, "There were errors in the form. Please check and try again.")
    else:
        formset = RecordFormSet(queryset=Record.objects.none())
    return render(request, 'store/create_record.html', {'formset': formset})


class RecordUpdateView(LoginRequiredMixin, UpdateView):
    model = Record
    form_class = RecordForm
    template_name = 'store/update_record.html'
    success_url = reverse_lazy('record')

    def form_valid(self, form):
        try:
            with transaction.atomic():
                form.instance.issued_by = self.request.user
                self.object = form.save()
                messages.success(self.request, "Record updated successfully.")
                return super().form_valid(form)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error updating the record. Please check the form.")
        return super().form_invalid(form)
    

def get_drugs_by_category(request, category_id):
    drugs = Drug.objects.filter(category_id=category_id)
    drug_list = [{'id': drug.id, 'name': drug.trade_name} for drug in drugs]
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
    # Search functionality
    query = request.GET.get('q')
    if query:
        restock = restock.filter(
            Q(drug__generic_name__icontains=query) |
            Q(drug__trade_name__icontains=query)|
            Q(category__name__icontains=query)|
            Q(drug__dosage_form__icontains=query)|
            Q(drug__strength__icontains=query)
        )

    pgn=Paginator(restock,10)
    pn=request.GET.get('page')
    po=pgn.get_page(pn)

    context = {'restock': restock, 'po':po,'query':query or ''}
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
    ndate = datetime.now()
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
    ndate = datetime.now()
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
    ndate = datetime.now()
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


class StoreWorthView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return super().handle_no_permission()

    template_name = 'store/main_store_value.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.now()
        context['total_store_value'] = Drug.total_store_value()
        context['total_store_quantity'] = Drug.total_store_quantity()
        return context

class UnitWorthView(LoginRequiredMixin, DetailView):
    model = Unit
    template_name = 'store/unit_value.html'
    context_object_name = 'unit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit = self.object
        context['today'] = timezone.now()

        # Calculate store values using Python, not ORM
        store_value = sum(
            ((store.drug.cost_price or 0) / (store.drug.pack_size or 1)) * (store.quantity or 0)
            for store in unit.unit_store.all()
        )
        store_quantity = sum(store.quantity for store in unit.unit_store.all())

        locker_value = 0
        locker_quantity = 0
        if hasattr(unit, 'dispensary_locker'):
            # Calculate locker values dynamically in Python
            locker_value = sum(
                ((inventory.drug.cost_price or 0) / (inventory.drug.pack_size or 1)) * (inventory.quantity or 0)
                for inventory in unit.dispensary_locker.inventory.all()
            )
            locker_quantity = sum(inventory.quantity for inventory in unit.dispensary_locker.inventory.all())

        context['unit_worth'] = {
            'store_value': store_value,
            'store_quantity': store_quantity,
            'locker_value': locker_value,
            'locker_quantity': locker_quantity,
            'total_value': store_value + locker_value,
            'total_quantity': store_quantity + locker_quantity
        }
        return context

class InventoryWorthView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'store/worth.html'

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.now()

        context['total_store_value'] = Drug.total_store_value()
        context['combined_unit_value'] = Unit.combined_unit_value()
        context['grand_total_value'] = Unit.grand_total_value()

        units = Unit.objects.all().prefetch_related('unit_store__drug').select_related('dispensary_locker')
        unit_worths = {}

        for unit in units:
            store_value = sum(
                unit_store.drug.piece_unit_cost_price * unit_store.quantity
                for unit_store in unit.unit_store.all()
            )

            locker_value = 0
            if hasattr(unit, 'dispensary_locker'):
                locker_value = sum(
                    inventory.drug.piece_unit_cost_price * inventory.quantity
                    for inventory in unit.dispensary_locker.inventory.all()
                )

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
    

class UnitDashboardView(LoginRequiredMixin, UnitGroupRequiredMixin, DetailView):
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
        unit_store_drugs = UnitStore.objects.filter(unit=self.object).select_related('drug').order_by('drug__dosage_form')
        context['unit_store_drugs'] = unit_store_drugs
        context['drug_requests_url'] = reverse('unit_drug_requests', kwargs={'pk': self.object.pk})
        
        query = self.request.GET.get('q')
        if query:
            unit_store_drugs = unit_store_drugs.filter(
                Q(drug__generic_name__icontains=query) |
                Q(drug__trade_name__icontains=query)|
                Q(drug__category__name__icontains=query)|
                Q(drug__dosage_form__icontains=query)|
                Q(drug__strength__icontains=query)
            )        
        # Pagination
        paginator = Paginator(unit_store_drugs, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        today = timezone.now().date()
        one_month_later = today + timedelta(days=31)
        three_months_later = today + timedelta(days=90)
        six_months_later = today + timedelta(days=180)
        
        total_worth = 0
        total_expiring_in_1_month = 0
        total_expiring_in_3_months = 0
        total_expiring_in_6_months = 0
        
        for unit_store_drug in page_obj:
            total_worth += float(unit_store_drug.total_value)
            unit_store_drug.restock_info = Restock.objects.filter(drug=unit_store_drug.drug).order_by('-date').first()
            
            if unit_store_drug.drug.expiration_date:
                if unit_store_drug.drug.expiration_date <= one_month_later:
                    total_expiring_in_1_month += unit_store_drug.quantity
                elif unit_store_drug.drug.expiration_date <= three_months_later:
                    total_expiring_in_3_months += unit_store_drug.quantity
                elif unit_store_drug.drug.expiration_date <= six_months_later:
                    total_expiring_in_6_months += unit_store_drug.quantity
        
        context['page_obj'] = page_obj
        context['total_worth'] = total_worth
        context['total_expiring_in_6_months'] = total_expiring_in_6_months
        context['total_expiring_in_3_months'] = total_expiring_in_3_months
        context['total_expiring_in_1_month'] = total_expiring_in_1_month
        context['today'] = today
        context['one_month_later'] = one_month_later
        context['three_months_later'] = three_months_later
        context['six_months_later'] = six_months_later
        context['query'] = self.request.GET.get('q', '')       

        return context


class UnitDispensaryLockerView(LoginRequiredMixin, UnitGroupRequiredMixin, DetailView):
    model = Unit
    template_name = 'store/unit_dispensary_locker.html'
    context_object_name = 'store'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dispensary_drugs = LockerInventory.objects.filter(locker__unit=self.object).select_related('drug').order_by('-updated')

        # Calculate total worth
        # total_worth = dispensary_drugs.aggregate(
        #     total=Sum(F('drug__piece_unit_cost_price') * F('quantity'))
        # )['total'] or 0
         # Dynamically calculate total worth
          # Dynamically calculate total worth
        total_worth = round(sum(
            ((drug.drug.cost_price or 0) / (drug.drug.pack_size or 1)) * drug.quantity
            for drug in dispensary_drugs
        ), 2)
        query = self.request.GET.get('q')
        if query:
            dispensary_drugs = dispensary_drugs.filter(
                Q(drug__generic_name__icontains=query) |
                Q(drug__trade_name__icontains=query)|
                Q(drug__category__name__icontains=query)|
                Q(drug__dosage_form__icontains=query)|
                Q(drug__strength__icontains=query)
            )        
        # Order the drugs and paginate
        ordered_drugs = dispensary_drugs.order_by('drug__generic_name')
        paginator = Paginator(ordered_drugs, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['dispensary_drugs'] = page_obj
        context['total_worth'] = total_worth
        context['page_obj'] = page_obj
        context['query'] = self.request.GET.get('q', '')       
        return context


class UnitTransferView(LoginRequiredMixin, UnitGroupRequiredMixin, DetailView):
    model = Unit
    template_name = 'store/unit_transfer.html'
    context_object_name = 'store'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Fetch unit issue records where this unit is the issuing unit
        unit_issue_records = UnitIssueRecord.objects.filter(
            unit=self.object,
            issued_to__isnull=False, 
            issued_to_locker__isnull=True
        ).order_by('-date_issued')
        query = self.request.GET.get('q')
        if query:
            unit_issue_records = unit_issue_records.filter(
                Q(drug__generic_name__icontains=query) |
                Q(drug__trade_name__icontains=query)|
                Q(drug__category__name__icontains=query)|
                Q(issued_to__name__icontains=query)|
                Q(drug__dosage_form__icontains=query)|
                Q(drug__strength__icontains=query)
            )        
        # Paginate the results
        paginator = Paginator(unit_issue_records, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['unit_issue_records'] = page_obj
        context['page_obj'] = page_obj
        context['query'] = self.request.GET.get('q', '')       

        return context

class UnitReceivedRecordsView(LoginRequiredMixin, UnitGroupRequiredMixin, DetailView):
    model = Unit
    template_name = 'store/unit_received.html'
    context_object_name = 'store'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fetch unit issue records where this unit is the receiving unit
        received_records = UnitIssueRecord.objects.filter(
            issued_to=self.object
        ).order_by('-date_issued')

        query = self.request.GET.get('q')
        if query:
            received_records = received_records.filter(
                Q(drug__generic_name__icontains=query) |
                Q(drug__trade_name__icontains=query) |
                Q(drug__category__name__icontains=query) |
                Q(unit__name__icontains=query) |
                Q(drug__dosage_form__icontains=query) |
                Q(drug__strength__icontains=query)
            )

        # Paginate the results
        paginator = Paginator(received_records, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['received_records'] = page_obj
        context['page_obj'] = page_obj
        context['query'] = self.request.GET.get('q', '')

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
        extra=5
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
                    messages.success(request, 'Successfully Transfered')
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
        extra=5
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
                    messages.success(request, 'Dispensary Locker Restocked Successfully')
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
            initial=[{'unit': unit, 'issued_to_locker': unit_locker}] * 5
        )

    return render(request, 'store/create_dispensary_record.html', {'formset': formset, 'unit': unit})


@login_required
def unitissue_report(request, pk):
    unit = get_object_or_404(Unit, id=pk)
    
    
    # Initialize the filter with the queryset and manually set the initial value
    unitissuefilter = UnitIssueFilter(
        request.GET
    )
    
    # Set initial value for the unit filter
    unitissuefilter.form.initial['unit'] = pk
    
    filtered_queryset = unitissuefilter.qs
    total_quantity = filtered_queryset.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    if filtered_queryset.exists() and filtered_queryset.first().drug.piece_unit_selling_price:
        first_drug = filtered_queryset.first().drug.piece_unit_selling_price
    else:
        first_drug = 0

    total_price = total_quantity * first_drug
    total_appearance = filtered_queryset.count()

    pgn = Paginator(filtered_queryset, 10)
    pn = request.GET.get('page')
    po = pgn.get_page(pn)

    context = {
        'unit': unit,
        'unitissuefilter': unitissuefilter,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'po': po,
    }
    return render(request, 'store/unitissue_report.html', context)


@login_required
def unitissue_pdf(request):
    ndate = datetime.now()
    filename = ndate.strftime('on_%d_%m_%Y_at_%I_%M%p.pdf')
    f = UnitIssueFilter(request.GET, queryset=UnitIssueRecord.objects.all()).qs
    total_quantity = f.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    
    if f.exists() and f.first().drug.piece_unit_selling_price:
        first_drug = f.first().drug.piece_unit_selling_price
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
    
    pdf_buffer = generate_pdf(context, 'store/unitissue_pdf.html')
    
    if pdf_buffer is None:
        return HttpResponse('Error generating PDF', status=500)
    
    response = StreamingHttpResponse(pdf_generator(pdf_buffer), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="gen_by_{request.user}_{filename}"'
    return response


@login_required
def transfer_report(request, pk):
    unit = get_object_or_404(Unit, id=pk)
    
    # Initialize the filter with the queryset filtered by unit
    transferfilter = TransferFilter(
        request.GET,
        queryset=UnitIssueRecord.objects.filter(unit=unit).annotate(
            unit_price=ExpressionWrapper(
                models.F('drug__selling_price') / models.F('drug__pack_size'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            total_price=ExpressionWrapper(
                models.F('quantity') * (models.F('drug__selling_price') / models.F('drug__pack_size')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).order_by('-date_issued')
    )
    
    transferfilter.form.initial['unit'] = pk
    
    # Use the filtered queryset
    filtered_queryset = transferfilter.qs
    
    # Calculate totals
    totals = filtered_queryset.aggregate(
        total_quantity=models.Sum('quantity'),
        total_price=ExpressionWrapper(
            models.Sum(
                models.F('quantity') * (models.F('drug__selling_price') / models.F('drug__pack_size'))
            ),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        ),
    )
    
    total_quantity = totals['total_quantity'] or 0
    total_price = totals['total_price'] or 0
    total_appearance = filtered_queryset.count()

    # Pagination
    pgn = Paginator(filtered_queryset, 10)
    pn = request.GET.get('page')
    po = pgn.get_page(pn)

    context = {
        'unit': unit,
        'transferfilter': transferfilter,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'po': po
    }
    return render(request, 'store/transfer_report.html', context)

@login_required
def transfer_pdf(request, pk):
    unit = get_object_or_404(Unit, id=pk)
    
    # Use the same filtering logic with annotated fields
    transferfilter = TransferFilter(
        request.GET,
        queryset=UnitIssueRecord.objects.filter(unit=unit).annotate(
            unit_price=ExpressionWrapper(
                models.F('drug__selling_price') / models.F('drug__pack_size'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            total_price=ExpressionWrapper(
                models.F('quantity') * (models.F('drug__selling_price') / models.F('drug__pack_size')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).order_by('-date_issued')
    )
    
    filtered_queryset = transferfilter.qs
    
    # Calculate totals using the same annotations
    totals = filtered_queryset.aggregate(
        total_quantity=models.Sum('quantity'),
        total_price=ExpressionWrapper(
            models.Sum(
                models.F('quantity') * (models.F('drug__selling_price') / models.F('drug__pack_size'))
            ),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        ),
    )
    
    total_quantity = totals['total_quantity'] or 0
    total_price = totals['total_price'] or 0
    total_appearance = filtered_queryset.count()
    
    # Generate PDF metadata
    ndate = datetime.now()
    filename = ndate.strftime('on_%d_%m_%Y_at_%I_%M%p.pdf')
    keys = [key for key, value in request.GET.items() if value]
    result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"
    
    context = {
        'f': filtered_queryset,
        'pagesize': 'A4',
        'orientation': 'Portrait',
        'result': result,
        'keys': keys,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'unit': unit,
    }
    
    pdf_buffer = generate_pdf(context, 'store/transfer_pdf.html')
    if pdf_buffer is None:
        return HttpResponse('Error generating PDF', status=500)
    
    response = StreamingHttpResponse(pdf_generator(pdf_buffer), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="gen_by_{request.user}_{filename}"'
    return response


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
    DispensaryFormSet = modelformset_factory(DispenseRecord, form=DispenseRecordForm, extra=5)
    
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

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.dispensary_locker = get_object_or_404(DispensaryLocker, pk=kwargs['pk'])
        self.unit = self.dispensary_locker.unit

    def get_queryset(self):
        queryset = DispenseRecord.objects.filter(dispensary=self.dispensary_locker).order_by('-dispense_date')
        self.filterset = DispenseFilter(self.request.GET, queryset=queryset)
        self.filterset.form.initial['dispensary'] = self.dispensary_locker.pk
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_queryset = self.get_queryset()
        
        context['total_dispensed'] = filtered_queryset.count()
                
        price_totals = filtered_queryset.aggregate(
            total_cost=Sum(F('quantity') * (F('drug__cost_price') / F('drug__pack_size'))),
            total_selling=Sum(F('quantity') * (F('drug__selling_price') / F('drug__pack_size'))),
            total_quantity=Sum('quantity')
        )

        context['total_cost_price'] = price_totals['total_cost'] or Decimal('0.00')
        context['total_piece_unit_selling_price'] = price_totals['total_selling'] or Decimal('0.00')
        context['total_profit'] = context['total_piece_unit_selling_price'] - context['total_cost_price']

        context['percentage'] = (
            (context['total_profit'] / context['total_cost_price']) * 100
        ) if context['total_cost_price'] > 0 else Decimal('0.00')

        context['total_quantity'] = price_totals['total_quantity'] or 0

        context['total_price'] = context['total_piece_unit_selling_price']
        
        context['dispensary_locker'] = self.dispensary_locker
        context['dispensefilter'] = self.filterset
        
        return context

    def get_unit_for_mixin(self):
        return self.unit
    
@login_required
def dispense_report(request, pk):
    dispensary = get_object_or_404(DispensaryLocker, id=pk)
    
    # Initialize the filter with the queryset and manually set the initial value
    dispensefilter = DispenseFilter(
        request.GET,
        queryset=DispenseRecord.objects.filter(dispensary=dispensary).order_by('-updated')
    )
    
    # Set initial value for the dispensary filter
    dispensefilter.form.initial['dispensary'] = pk
    filtered_queryset = dispensefilter.qs
    
    # Calculate totals using annotate for accurate price calculations
    totals = filtered_queryset.aggregate(
        total_quantity=models.Sum('quantity'),
        total_price=ExpressionWrapper(
            models.Sum(models.F('quantity') * models.F('drug__piece_unit_selling_price')),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )
    
    total_quantity = totals['total_quantity'] or 0
    total_price = totals['total_price'] or 0
    total_appearance = filtered_queryset.count()

    pgn = Paginator(filtered_queryset, 10)
    pn = request.GET.get('page')
    po = pgn.get_page(pn)

    context = {
        'dispensary': dispensary,
        'dispensefilter': dispensefilter,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'po': po
    }
    return render(request, 'store/dispense_report.html', context)

@login_required
def dispense_pdf(request, pk):
    dispensary = get_object_or_404(DispensaryLocker, id=pk)
    
    # Use the same filtering logic as the report view
    dispensefilter = DispenseFilter(
        request.GET,
        queryset=DispenseRecord.objects.filter(dispensary=dispensary).order_by('-updated')
    )
    
    filtered_queryset = dispensefilter.qs
    
    # Calculate totals using annotate for accurate price calculations
    totals = filtered_queryset.aggregate(
        total_quantity=models.Sum('quantity'),
        total_price=ExpressionWrapper(
            models.Sum(
                models.F('quantity') * (models.F('drug__selling_price') / models.F('drug__pack_size'))
            ),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )
    
    total_quantity = totals['total_quantity'] or 0
    total_price = totals['total_price'] or 0
    total_appearance = filtered_queryset.count()

    # Generate PDF metadata
    ndate = datetime.now()
    filename = ndate.strftime('on_%d_%m_%Y_at_%I_%M%p.pdf')
    keys = [key for key, value in request.GET.items() if value]
    result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"

    context = {
        'f': filtered_queryset,
        'pagesize': 'A4',
        'orientation': 'Portrait',
        'result': result,
        'keys': keys,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'dispensary': dispensary,
    }
    
    # Generate PDF
    pdf_buffer = generate_pdf(context, 'store/dispense_pdf.html')
    if pdf_buffer is None:
        return HttpResponse('Error generating PDF', status=500)
        
    response = StreamingHttpResponse(pdf_generator(pdf_buffer), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="gen_by_{request.user}_{filename}"'
    return response

class BoxView(LoginRequiredMixin, UnitGroupRequiredMixin, DetailView):
    model = Unit
    template_name = 'store/unit_box.html'
    context_object_name = 'store'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Fetch unit issue records where this unit is the issuing unit
        unit_issue_records = UnitIssueRecord.objects.filter(
            unit=self.object,
            moved_to__isnull=False, 
            issued_to_locker__isnull=True
        ).order_by('-date_issued')
        query = self.request.GET.get('q')
        if query:
            unit_issue_records = unit_issue_records.filter(
                Q(drug__generic_name__icontains=query) |
                Q(drug__trade_name__icontains=query)|
                Q(drug__category__name__icontains=query)|
                Q(drug__dosage_form__icontains=query)|
                Q(drug__strength__icontains=query)|
                Q(moved_to__icontains=query)
            )        
        # Paginate the results
        paginator = Paginator(unit_issue_records, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['unit_issue_records'] = page_obj
        context['page_obj'] = page_obj
        context['query'] = self.request.GET.get('q', '')       

        return context

@unit_group_required
def boxrecord(request, unit_id):
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
        form=BoxRecordForm,
        formset=CustomUnitIssueFormSet,
        extra=5
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
                    messages.success(request, 'DRUGS MOVED TO DAMAGE AND EXPIRY BOX')
                    return redirect('unit_box', pk=unit_id)
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        formset = UnitIssueFormSet(
            queryset=UnitIssueRecord.objects.none(),
            issuing_unit=unit,
            initial=[{'unit': unit}] * 2
        )
    return render(request, 'store/boxrecord_form.html', {'formset': formset, 'unit': unit})


class BoxUpdateView(LoginRequiredMixin,UnitGroupRequiredMixin,UpdateView):
    model = UnitIssueRecord
    form_class = BoxRecordForm
    template_name = 'store/box_update.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['issuing_unit'] = self.object.unit
        return kwargs

    def get_success_url(self):
        return reverse_lazy('unit_box', kwargs={'pk': self.object.unit.pk})

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


class BoxView(LoginRequiredMixin, UnitGroupRequiredMixin, DetailView):
    model = Unit
    template_name = 'store/unit_box.html'
    context_object_name = 'store'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Fetch unit issue records where this unit is the issuing unit
        unit_issue_records = UnitIssueRecord.objects.filter(
            unit=self.object,
            moved_to__isnull=False, 
            issued_to_locker__isnull=True
        ).select_related('drug').order_by('-date_issued')
        
        # Store the base queryset for calculations
        self.filtered_queryset = unit_issue_records
        
        # Apply search filters if query exists
        query = self.request.GET.get('q')
        if query:
            unit_issue_records = unit_issue_records.filter(
                Q(drug__generic_name__icontains=query) |
                Q(drug__trade_name__icontains=query)|
                Q(drug__category__name__icontains=query)|
                Q(drug__dosage_form__icontains=query)|
                Q(drug__strength__icontains=query)|
                Q(moved_to__icontains=query)
            )
            self.filtered_queryset = unit_issue_records
            
        # Calculate totals
        total_quantity = self.filtered_queryset.aggregate(Sum('quantity'))['quantity__sum'] or 0
        total_appearance = self.filtered_queryset.count()
        
        # Calculate total price by summing (quantity * price) for each record
        total_price = sum(
            record.quantity * (record.drug.piece_unit_selling_price or 0)
            for record in self.filtered_queryset
        )
        
        # Paginate the results
        paginator = Paginator(unit_issue_records, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Update context with all data
        context.update({
            'unit_issue_records': page_obj,
            'page_obj': page_obj,
            'query': self.request.GET.get('q', ''),
            'total_appearance': total_appearance,
            'total_quantity': total_quantity,
            'total_price': total_price
        })

        return context

@login_required
def box_pdf(request, pk):
    unit = get_object_or_404(Unit, id=pk)
    
    # Fetch unit issue records with drug relationship
    unit_issue_records = UnitIssueRecord.objects.filter(
        unit=unit,
        moved_to__isnull=False, 
        issued_to_locker__isnull=True
    ).select_related('drug').order_by('-date_issued')
    
    # Prepare filter keys
    keys = []
    query = request.GET.get('q')
    if query:
        keys.append(f": {query}")
    
    # Apply search query if present
    if query:
        unit_issue_records = unit_issue_records.filter(
            Q(drug__generic_name__icontains=query) |
            Q(drug__trade_name__icontains=query) |
            Q(drug__category__name__icontains=query) |
            Q(drug__dosage_form__icontains=query)|
            Q(drug__strength__icontains=query)|
            Q(moved_to__icontains=query)
        )
    
    # Calculate totals
    total_quantity = unit_issue_records.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    total_appearance = unit_issue_records.count()
    
    # Calculate total price by summing (quantity * price) for each record
    total_price = sum(
        record.quantity * (record.drug.piece_unit_selling_price or 0)
        for record in unit_issue_records
    )
    
    # Prepare context for PDF
    context = {
        'f': unit_issue_records,
        'total_quantity': total_quantity,
        'total_appearance': total_appearance,
        'total_price': total_price,
        'keys': keys,
        'result': f"GENERATED ON: {datetime.now().strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}",
        'pagesize': 'A4',
        'orientation': 'Portrait',
    }
    
    # Generate PDF
    pdf_buffer = generate_pdf(context, 'store/box_pdf.html')
    
    if pdf_buffer is None:
        return HttpResponse('Error generating PDF', status=500)
    
    # Prepare response
    ndate = datetime.now()
    filename = ndate.strftime('on_%d_%m_%Y_at_%I_%M%p.pdf')
    response = StreamingHttpResponse(pdf_generator(pdf_buffer), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="gen_by_{request.user}_{filename}"'
    return response


@login_required
def return_drug(request, unit_id):
    unit = get_object_or_404(Unit, id=unit_id)
    ReturnDrugFormSet = modelformset_factory(ReturnedDrugs, form=ReturnDrugForm, extra=5)
    
    if request.method == 'POST':
        formset = ReturnDrugFormSet(request.POST, queryset=ReturnedDrugs.objects.none(), form_kwargs={'unit': unit})
        if formset.is_valid():
            try:
                with transaction.atomic():
                    instances = formset.save(commit=False)
                    for instance in instances:
                        if instance.drug and instance.quantity:
                            instance.unit = unit
                            instance.received_by = request.user
                            instance.save()

                            # Update DispensaryLocker inventory
                            locker_inventory, created = LockerInventory.objects.get_or_create(locker=unit.dispensary_locker, drug=instance.drug)
                            locker_inventory.quantity += instance.quantity
                            locker_inventory.save()

                    messages.success(request, 'Drugs returned successfully')
                    return redirect('return_drugs_list', unit_id=unit.id)

            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        formset = ReturnDrugFormSet(queryset=ReturnedDrugs.objects.none(), form_kwargs={'unit': unit})
    
    return render(request, 'store/return_drugs.html', {'formset': formset, 'unit': unit})


from django.db.models import Q, Sum

class ReturnedDrugsListView(ListView):
    model = ReturnedDrugs
    template_name = 'store/return_list.html'
    context_object_name = 'returned_drugs'
    paginate_by = 10

    def get_queryset(self):
        unit_id = self.kwargs.get('unit_id')
        self.unit = get_object_or_404(Unit, id=unit_id)
        queryset = ReturnedDrugs.objects.filter(unit=self.unit).order_by('-updated')

        # Get search parameters
        query = self.request.GET.get('q')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        # Apply text search filters
        if query:
            queryset = queryset.filter(
                Q(drug__generic_name__icontains=query) |
                Q(drug__trade_name__icontains=query) |
                Q(category__name__icontains=query) |
                Q(patient_info__icontains=query) |
                Q(drug__dosage_form__icontains=query) |
                Q(drug__strength__icontains=query)
            )

        # Apply date filters
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        self.filtered_queryset = queryset  # Save queryset for use in get_context_data
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate total price by summing (quantity * price) for each item
        total_price = sum(
            item.quantity * item.drug.piece_unit_selling_price 
            for item in self.filtered_queryset.select_related('drug')
        )
        
        # Calculate other totals
        total_quantity = self.filtered_queryset.aggregate(Sum('quantity'))['quantity__sum'] or 0
        total_appearance = self.filtered_queryset.count()

        # Add calculated data to the context
        context.update({
            'unit': self.unit,
            'query': self.request.GET.get('q', ''),
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', ''),
            'total_quantity': total_quantity,
            'total_appearance': total_appearance,
            'total_price': total_price,
        })
        return context

@login_required
def return_report(request, unit_id):
    unit = get_object_or_404(Unit, id=unit_id)
    returnfilter = ReturnDrugFilter(request.GET, queryset=ReturnedDrugs.objects.filter(unit=unit).order_by('-updated'))
    filtered_queryset = returnfilter.qs
    total_quantity = filtered_queryset.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    total_appearance = filtered_queryset.count()

    pgn = Paginator(filtered_queryset, 10)
    pn = request.GET.get('page')
    po = pgn.get_page(pn)

    context = {
        'unit': unit,
        'returnfilter': returnfilter,
        'total_appearance': total_appearance,
        'total_quantity': total_quantity,
        'po': po
    }
    return render(request, 'store/return_drugs_report.html', context)



class LoginActivityListView(LoginRequiredMixin, ListView):
    model = LoginActivity
    template_name = 'store/login_activity_list.html'
    context_object_name = 'logs'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-login_time')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(user__username__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(ip_address__icontains=query)
            )

        def format_duration(seconds):
            if seconds < 60:
                return f"{seconds} seconds"
            elif seconds < 3600:
                minutes, seconds = divmod(seconds, 60)
                return f"{minutes} minutes, {seconds} seconds"
            elif seconds < 86400:
                hours, remainder = divmod(seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{hours} hours, {minutes} minutes, {seconds} seconds"
            elif seconds < 604800:
                days, remainder = divmod(seconds, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
            elif seconds < 2592000:
                weeks, remainder = divmod(seconds, 604800)
                days, remainder = divmod(remainder, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{weeks} weeks, {days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
            elif seconds < 31536000:
                months, remainder = divmod(seconds, 2592000)
                weeks, remainder = divmod(remainder, 604800)
                days, remainder = divmod(remainder, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{months} months, {weeks} weeks, {days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
            else:
                years, remainder = divmod(seconds, 31536000)
                months, remainder = divmod(remainder, 2592000)
                weeks, remainder = divmod(remainder, 604800)
                days, remainder = divmod(remainder, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{years} years, {months} months, {weeks} weeks, {days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

        for log in queryset:
            if log.logout_time:
                duration = log.logout_time - log.login_time
            else:
                duration = timezone.now() - log.login_time

            seconds = int(duration.total_seconds())
            log.duration = format_duration(seconds)


        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        # Count the number of logged-in users
        context['logged_in_users_count'] = LoginActivity.objects.filter(logout_time__isnull=True).values('user_id').distinct().count()

        return context


@login_required
def receive_report(request, pk):
   unit = get_object_or_404(Unit, id=pk)
   
   # Initialize the filter with annotated queryset
   receivefilter = ReceiveFilter(
       request.GET,
       queryset=UnitIssueRecord.objects.filter(issued_to=unit).annotate(
           unit_price=ExpressionWrapper(
               models.F('drug__selling_price') / models.F('drug__pack_size'),
               output_field=DecimalField(max_digits=10, decimal_places=2)
           ),
           total_price=ExpressionWrapper(
               models.F('quantity') * (models.F('drug__selling_price') / models.F('drug__pack_size')),
               output_field=DecimalField(max_digits=10, decimal_places=2)
           )
       ).order_by('-date_issued')
   )
   
   receivefilter.form.initial['issued_to'] = pk
   filtered_queryset = receivefilter.qs
   
   # Calculate totals using annotated fields
   totals = filtered_queryset.aggregate(
       total_quantity=models.Sum('quantity'),
       total_price=ExpressionWrapper(
           models.Sum(
               models.F('quantity') * (models.F('drug__selling_price') / models.F('drug__pack_size'))
           ),
           output_field=DecimalField(max_digits=10, decimal_places=2)
       ),
   )
   
   total_quantity = totals['total_quantity'] or 0
   total_price = totals['total_price'] or 0
   total_appearance = filtered_queryset.count()

   paginator = Paginator(filtered_queryset, 10)
   page_number = request.GET.get('page')
   page_obj = paginator.get_page(page_number)

   context = {
       'unit': unit,
       'receivefilter': receivefilter,
       'total_appearance': total_appearance,
       'total_price': total_price,
       'total_quantity': total_quantity,
       'page_obj': page_obj,
   }
   return render(request, 'store/received_report.html', context)

@login_required
def receive_pdf(request, pk):
   unit = get_object_or_404(Unit, id=pk)
   
   # Use the same filtering logic with annotated fields
   receivefilter = ReceiveFilter(
       request.GET,
       queryset=UnitIssueRecord.objects.filter(issued_to=unit).annotate(
           unit_price=ExpressionWrapper(
               models.F('drug__selling_price') / models.F('drug__pack_size'),
               output_field=DecimalField(max_digits=10, decimal_places=2)
           ),
           total_price=ExpressionWrapper(
               models.F('quantity') * (models.F('drug__selling_price') / models.F('drug__pack_size')),
               output_field=DecimalField(max_digits=10, decimal_places=2)
           )
       ).order_by('-date_issued')
   )
   
   filtered_queryset = receivefilter.qs
   
   # Calculate totals using the same annotations
   totals = filtered_queryset.aggregate(
       total_quantity=models.Sum('quantity'),
       total_price=ExpressionWrapper(
           models.Sum(
               models.F('quantity') * (models.F('drug__selling_price') / models.F('drug__pack_size'))
           ),
           output_field=DecimalField(max_digits=10, decimal_places=2)
       ),
   )
   
   total_quantity = totals['total_quantity'] or 0
   total_price = totals['total_price'] or 0
   total_appearance = filtered_queryset.count()

   # Generate PDF metadata
   ndate = datetime.now()
   filename = ndate.strftime('received_on_%d_%m_%Y_at_%I_%M%p.pdf')
   keys = [key for key, value in request.GET.items() if value]
   result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"

   context = {
       'f': filtered_queryset,
       'pagesize': 'A4',
       'orientation': 'Portrait',
       'result': result,
       'keys': keys,
       'total_appearance': total_appearance,
       'total_price': total_price,
       'total_quantity': total_quantity,
       'unit': unit,
   }
   
   pdf_buffer = generate_pdf(context, 'store/receive_pdf.html')
   if pdf_buffer is None:
       return HttpResponse('Error generating PDF', status=500)
       
   response = StreamingHttpResponse(pdf_generator(pdf_buffer), content_type='application/pdf')
   response['Content-Disposition'] = f'attachment; filename="{filename}"'
   return response

class DrugRequestCreateView(LoginRequiredMixin, CreateView):
    model = DrugRequest
    form_class = DrugRequestForm
    template_name = 'store/request_form.html'
    
    def get_success_url(self):
        messages.success(self.request, 'Drug request created successfully.')
        return reverse_lazy('unit_bulk_locker', kwargs={'pk': self.unit.id})

    def dispatch(self, request, *args, **kwargs):
        # Get the unit from the URL or raise a 404 if not found
        self.unit = get_object_or_404(Unit, id=self.kwargs['unit_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.unit = self.unit  # Assign the unit from the URL
        form.instance.requested_by = self.request.user  # Associate the user making the request
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {'unit': self.unit}  # Pre-fill the unit field in the form
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.unit  # Add the unit to the template context
        return context


class DrugRequestListView(LoginRequiredMixin, ListView):
    model = DrugRequest
    template_name = 'store/request_list.html'
    context_object_name = 'drugrequests'
    paginate_by = 10

    def get_queryset(self):
        # Get all drug requests and optionally filter by search query
        queryset = DrugRequest.objects.select_related('unit', 'requested_by').order_by('-updated')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(unit__name__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for drug_request in context['drugrequests']:
            if drug_request.drugs:
                # Convert newline-separated `drugs` text into a list
                drug_request.drugs_list = drug_request.drugs.splitlines()
        context['query'] = self.request.GET.get('q', '')
        return context


class DrugRequestUpdateView(LoginRequiredMixin, UpdateView):
    model = DrugRequest
    form_class = DrugRequestForm
    template_name = 'store/drugrequest_form.html'

    def get_success_url(self):
        messages.success(self.request, 'Drug request updated successfully.')
        return reverse_lazy('unit_bulk_locker', kwargs={'pk': self.unit.id})

    def dispatch(self, request, *args, **kwargs):
        # Get the unit from the URL or raise a 404 if not found
        self.unit = get_object_or_404(Unit, id=self.kwargs['unit_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Ensure the queryset is limited to drug requests for the specific unit
        return DrugRequest.objects.filter(unit=self.unit)

    def form_valid(self, form):
        form.instance.unit = self.unit  # Assign the unit from the URL
        form.instance.requested_by = self.request.user  # Associate the user making the request
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {'unit': self.unit}  # Pre-fill the unit field in the form
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.unit  # Add the unit to the template context
        return context

class UnitDrugRequestListView(LoginRequiredMixin, UnitGroupRequiredMixin, ListView):
    model = DrugRequest
    template_name = 'store/unit_request_list.html'
    context_object_name = 'drugrequests'
    paginate_by = 10

    def get_queryset(self):
        # Filter drug requests by the unit
        unit = self.kwargs.get('pk')  # Assuming `pk` is the Unit's primary key
        return DrugRequest.objects.filter(unit_id=unit).select_related('unit', 'requested_by').order_by('-updated')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = Unit.objects.get(pk=self.kwargs.get('pk'))
        return context
