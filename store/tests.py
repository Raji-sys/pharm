from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from .models import Drug, Record, Restock, Category
from .forms import DrugForm, RecordForm, RestockForm

