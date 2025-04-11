from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            return self.request.user.profile.role == 'ADM'
        return False

    def handle_no_permission(self):
        raise PermissionDenied("You must be an administrator to access this page.")

class FinancialSecretaryRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            return self.request.user.profile.role in ['FS', 'ADM']
        return False

    def handle_no_permission(self):
        raise PermissionDenied("You must be a financial secretary to access this page.")