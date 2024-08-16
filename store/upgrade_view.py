from .filters import DrugFilter, RestockFilter, DrugSearchFilter
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
from django.forms import modelformset_factory
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.views.generic import DetailView, ListView, UpdateView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import get_object_or_404


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


# @login_required
# def create_record(request):
#     RecordFormSet = modelformset_factory(Record, form=RecordForm, extra=5)
    
#     if request.method == 'POST':
#         formset = RecordFormSet(request.POST)
#         if formset.is_valid():
#             instances = formset.save(commit=False)
#             any_saved = False
#             for instance in instances:
#                 if instance.drug and instance.quantity:
#                     try:
#                         instance.issued_by = request.user
#                         instance.save()
#                         any_saved = True
#                     except ValidationError as e:
#                         formset.add_error(None, str(e))
          
#             if any_saved:
#                 messages.success(request, 'Drugs issued successfully. Some quantities may have been adjusted.')
#                 return redirect('record')  # Make sure 'record' is the correct name for your URL
#     else:
#         formset = RecordFormSet(queryset=Record.objects.none())    
#     return render(request, 'store/create_record.html', {'formset': formset})


# @login_required
# def records(request):
#     records = Record.objects.all().order_by('-updated_at')
#     pgn=Paginator(records,10)
#     pn=request.GET.get('page')
#     po=pgn.get_page(pn)

#     context = {'records': records, 'po':po}
#     return render(request, 'store/record.html', context)


# class RecordUpdateView(UpdateView):
#     model = Record
#     form_class = RecordForm
#     template_name = 'store/update_record.html'
#     success_url = reverse_lazy('record')

#     def form_valid(self, form):
#         try:
#             form.instance.issued_by = self.request.user
#             response = super().form_valid(form)
#             messages.success(self.request, "Record updated successfully.")
#             return response
#         except ValidationError as e:
#             form.add_error(None, str(e))
#             return self.form_invalid(form)

#     def form_invalid(self, form):
#         messages.error(self.request, "There was an error updating the record. Please check the form.")
#         return super().form_invalid(form)

def get_drugs_by_category(request, category_id):
    drugs = Drug.objects.filter(category_id=category_id)
    drug_list = [{'id': drug.id, 'name': drug.generic_name} for drug in drugs]
    return JsonResponse({'drugs': drug_list})


# @login_required
# def record_report(request):
#     recordfilter = RecordFilter(request.GET, queryset=Record.objects.all().order_by('-updated_at'))
#     filtered_queryset = recordfilter.qs
#     total_quantity = filtered_queryset.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    
#     if filtered_queryset.exists():
#         first_drug = filtered_queryset.first().drug.cost_price
#         if first_drug is None:
#             first_drug = 0
#     else:
#         first_drug = 0
    
#     total_price = total_quantity * first_drug
#     total_appearance = filtered_queryset.count()
#     pgn = Paginator(filtered_queryset, 10)
#     pn = request.GET.get('page')
#     po = pgn.get_page(pn)
    
#     context = {
#         'recordfilter': recordfilter,
#         'total_appearance': total_appearance,
#         'total_price': total_price,
#         'total_quantity': total_quantity,
#         'po': po
#     }
#     return render(request, 'store/record_report.html', context)

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


# @login_required
# def record_pdf(request):
#     ndate = datetime.datetime.now()
#     filename = ndate.strftime('on_%d/%m/%Y_at_%I.%M%p.pdf')
#     f = RecordFilter(request.GET, queryset=Record.objects.all()).qs
    
#     total_quantity = f.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
#     if f.exists() and f.first().drug.cost_price:
#         first_drug=f.first().drug.cost_price
#     else:
#         first_drug=0
        
#     total_price=total_quantity*first_drug
#     total_appearance=f.count()
#     keys = [key for key, value in request.GET.items() if value]
#     result = f"GENERATED ON: {ndate.strftime('%d-%B-%Y at %I:%M %p')}\nBY: {request.user}"
#     context = {'f': f, 'pagesize': 'A4', 'orientation': 'Potrait','result':result,'keys':keys,'total_appearance': total_appearance,'total_price':total_price,'total_quantity':total_quantity,}
#     response = HttpResponse(content_type='application/pdf', headers={'Content-Disposition': f'filename="gen_by_{request.user}_{filename}"'})
#     buffer = BytesIO()
#     pisa_status = pisa.CreatePDF(get_template('store/record_pdf.html').render(context), dest=buffer, encoding='utf-8', link_callback=fetch_resources)

#     if not pisa_status.err:
#         pdf = buffer.getvalue()
#         buffer.close()
#         response.write(pdf)
#         return response
#     return HttpResponse('Error generating PDF', status=500)


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


@login_required
def worth(request):
    total_store_value = Drug.total_store_value()
    ndate = datetime.datetime.now()
    today = ndate.strftime('%d-%B-%Y: %I:%M %p')
    context = {'total_store_value': total_store_value,'today':today}
    return render(request, 'store/worth.html', context)


@login_required
def create_distribution(request):
    if request.method == 'POST':
        form = DistributionForm(request.POST)
        if form.is_valid():
            distribution = form.save(commit=False)
            distribution.issued_by = request.user
            distribution.save()
            return redirect('distribution_detail', pk=distribution.pk)
    else:
        form = DistributionForm()
    
    return render(request, 'create_distribution.html', {'form': form})


class UnitDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Unit
    template_name = 'unit_detail.html'
    context_object_name = 'unit'

    def test_func(self):
        unit = self.get_object()
        return self.request.user.groups.filter(name=unit.group.name).exists() or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit = self.get_object()
        context['inventory'] = UnitStore.objects.filter(unit=unit)
        context['distributions_from'] = Distribution.objects.filter(from_unit=unit).order_by('-timestamp')[:10]
        context['distributions_to'] = Distribution.objects.filter(to_unit=unit).order_by('-timestamp')[:10]
        return context

class MainStoreView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Unit
    template_name = 'main_store.html'
    context_object_name = 'unit'

    def test_func(self):
        return self.request.user.groups.filter(name__endswith='Main Store Group').exists() or self.request.user.is_superuser

    def get_object(self):
        return get_object_or_404(Unit, unit_type='MAIN')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['inventory'] = UnitStore.objects.filter(unit=self.get_object())
        context['distributions'] = Distribution.objects.filter(from_unit=self.get_object()).order_by('-timestamp')[:20]
        return context

class LocalStoreListView(LoginRequiredMixin, ListView):
    model = Unit
    template_name = 'local_store_list.html'
    context_object_name = 'units'

    def get_queryset(self):
        return Unit.objects.filter(unit_type='LOCAL')

class DispensaryLockerListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Unit
    template_name = 'dispensary_locker_list.html'
    context_object_name = 'units'

    def test_func(self):
        return self.request.user.groups.filter(name__endswith='Local Store Group').exists() or self.request.user.is_superuser

    def get_queryset(self):
        local_store = get_object_or_404(Unit, group__in=self.request.user.groups.all(), unit_type='LOCAL')
        return Unit.objects.filter(parent_unit=local_store, unit_type='DISPENSARY')