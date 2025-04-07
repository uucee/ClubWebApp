from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.urls import resolve

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for the admin site
        if request.path.startswith('/admin/'):
            # Allow access to login page
            if request.path == '/admin/login/' or request.path == '/admin/logout/':
                return self.get_response(request)
            
            # Check if user is authenticated and is a superuser
            if not request.user.is_authenticated or not request.user.is_superuser:
                raise PermissionDenied("You do not have permission to access the admin site.")
        
        return self.get_response(request) 