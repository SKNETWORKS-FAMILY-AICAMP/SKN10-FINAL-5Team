from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.conf import settings

# Create your views here.
def login_view(request):
    return render(request, 'user/login.html')