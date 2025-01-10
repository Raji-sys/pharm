from django.urls import path,include
from . import views 
from .views import *


urlpatterns=[
    path('',views.index, name='index'),

    path('login_activity_log/', views.LoginActivityListView.as_view(), name='login_activity_log'),
    
    path('login/',CustomLoginView.as_view(), name='signin'),
    path('main-store/', MainStoreDashboardView.as_view(), name='main_store'),

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
    
    path('stores/', StoreListView.as_view(), name='store_list'),
    path('stores/<int:pk>/', UnitDashboardView.as_view(), name='unit_dashboard'),
    path('stores/bulk-locker/<int:pk>/', UnitBulkLockerDetailView.as_view(), name='unit_bulk_locker'),
    path('stores/dispensary-locker/<int:pk>/', UnitDispensaryLockerView.as_view(), name='unit_dispensary'),

    path('stores/drug-transfer/<int:pk>/', UnitTransferView.as_view(), name='unit_transfer'),
    path('unit/<int:pk>/received-records/', UnitReceivedRecordsView.as_view(), name='unit_received_records'),

    path('stores/box/<int:pk>/', BoxView.as_view(), name='unit_box'),
    

    path('store/locker/<int:unit_id>/', views.dispensaryissuerecord, name='dispensary_record'),
    path('expiry-date-notification/', ExpiryNotificationView.as_view(), name='expiry_notification'),
    
    path('unit-issue-record/new/<int:unit_id>/', views.unitissuerecord, name='unit_issue_record_create'),
    path('box/new/<int:unit_id>/', views.boxrecord, name='box_record_create'),
    path('unit-issue-records/', UnitIssueRecordListView.as_view(), name='unit_issue_record_list'),
    path('unit-issue-report/<int:pk>/', views.unitissue_report, name='unitissue_report'),
    path('unitissue-pdf/', views.unitissue_pdf, name='unitissue_pdf'),

    path('unit-issue-record/update/<int:pk>/', TransferUpdateView.as_view(), name='transfer_update'),
    path('transfer-report/<int:pk>/', views.transfer_report, name='transfer_report'),
    
    path('transfer/<int:pk>/pdf/', transfer_pdf, name='transfer_pdf'),
    path('unit/<int:pk>/receive-report/', receive_report, name='receive_report'),
    path('receive/<int:pk>/pdf/', receive_pdf, name='receive_pdf'),
    
    path('box/update/<int:pk>/', BoxUpdateView.as_view(), name='box_update'),
    path('box-report/<int:pk>/', views.box_report, name='box_report'),
    # path('box-pdf/', views.box_pdf, name='box_pdf'),
    path('box_pdf/<int:pk>/', views.box_pdf, name='box_pdf'),

    path('worth/', InventoryWorthView.as_view(), name='worth'),
    
    path('main-store-worth/', StoreWorthView.as_view(), name='main_store_value'),
    path('unit-worth/<int:pk>', UnitWorthView.as_view(), name='unit_value'),

    path('unit/dispensary/<int:dispensary_id>/dispense/', views.dispenserecord, name='dispense'),
    path('unit/dispensary/dispensed-list/<int:pk>/', DispenseRecordView.as_view(), name='dispensed_list'),
    path('dispense-report/<int:pk>/', views.dispense_report, name='dispense_report'),
    path('dispense-pdf/', views.dispense_pdf, name='dispense_pdf'),
    path('unit/<int:unit_id>/return-drug/', return_drug, name='return_drug'),
    path('returned-drugs/<int:unit_id>/', ReturnedDrugsListView.as_view(), name='return_drugs_list'),
    path('return-report/<int:unit_id>/', views.return_report, name='return_report'),

    # path('sales-stats/', SalesStatsView.as_view(), name='sales_stats'),
    path('get_drugs_by_category/<int:category_id>/', views.get_drugs_by_category, name='get_drugs_by_category'),
    path('',include('django.contrib.auth.urls')),
]
