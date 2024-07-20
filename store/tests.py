from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from .models import Drug, Record, Restock, Category
from .forms import DrugForm, RecordForm, RestockForm


    # def test_restock_view_post_invalid(self):
    #     self.client.login(username='testuser', password='12345')
    #     restock_data = {
    #         'form-TOTAL_FORMS': '1',
    #         'form-INITIAL_FORMS': '0',
    #         'form-MIN_NUM_FORMS': '0',
    #         'form-MAX_NUM_FORMS': '1000',
    #         'form-0-drug': '',
    #         'form-0-quantity': '',
    #     }
    #     response = self.client.post(self.restock_url, data=restock_data)
    #     if response.status_code != 302:
    #         formset = response.context['formset']
    #         print(formset.errors)
    #         print(formset.non_form_errors())

import json

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.paginator import Page
from django.db import models
from .models import Drug, Record, Restock
from .filters import DrugFilter, RecordFilter, RestockFilter