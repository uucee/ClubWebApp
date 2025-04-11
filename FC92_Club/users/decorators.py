from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps

def admin_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            if request.user.profile.role == 'ADM':
                return function(request, *args, **kwargs)
        raise PermissionDenied
    return wrap

def financial_secretary_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            if request.user.profile.role in ['FS', 'ADM']:  # Allow both FS and Admin
                return function(request, *args, **kwargs)
        raise PermissionDenied
    return wrap