from django.urls import path,include
from . import views 
from .views import *


urlpatterns=[
    path('',views.index, name='index'),
    path('login/',CustomLoginView.as_view(), name='signin'),

    path('create-drug/', views.create_drug, name='create_drug'),
    path('list/', views.drugs_list, name='list'),
    path('update-drug/<int:pk>/',DrugUpdateView.as_view(),name='update_drug'),
    path('drug-report/', views.drug_report, name='drug_report'),
    path('drug-pdf/', views.drug_pdf, name='drug_pdf'),
    
    path('create-record/', views.create_record, name='create_record'),
    path('record/', views.records, name='record'),
    path('update-drug-issued-record/<int:pk>/',RecordUpdateView.as_view(),name='update_record'),
    path('record-report/', views.record_report, name='record_report'),
    path('record-pdf/', views.record_pdf, name='record_pdf'),
    
    path('restock-drugs/', views.restock, name='restock_drugs'),
    path('retocked-list/', views.restocked_list, name='restocked'),
    path('update-restocked-drug/<int:pk>/',RestockUpdateView.as_view(),name='update_restock'),
    path('restock-report/', views.restock_report, name='restock_report'),
    path('restock-pdf/', views.restock_pdf, name='restock_pdf'),
    
    path('worth/', views.worth, name='worth'),
    path('get_drugs_by_category/<int:category_id>/', views.get_drugs_by_category, name='get_drugs_by_category'),
    path('',include('django.contrib.auth.urls')),
]
