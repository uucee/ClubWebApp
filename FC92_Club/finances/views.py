# Create your views here.
# finances/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, F, DecimalField # Removed Coalesce from here
from django.db.models.functions import Coalesce # Import Coalesce from here
from django.http import Http404, HttpResponseForbidden # Import for errors
from decimal import Decimal # Import Decimal for calculations
from .forms import PaymentForm, DueForm, BulkDueForm
from .models import Payment, Due
from users.models import Profile
from django.utils import timezone
from django.db.models import DecimalField # Import DecimalField for annotations

# --- Permission Helper ---
def is_financial_secretary_or_admin(user):
    # Avoid circular import if defined elsewhere, else define here
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.is_financial_secretary

# --- Financial Secretary Views ---

@user_passes_test(is_financial_secretary_or_admin)
def financial_dashboard(request):
    # Overview for FS - maybe list members needing attention?
    # For now, just links to actions
    return render(request, 'finances/financial_dashboard.html')

@user_passes_test(is_financial_secretary_or_admin)
def record_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                payment = form.save(commit=False)
                payment.recorded_by = request.user
                payment.save()
                messages.success(request, f"Payment of ₦{payment.amount_paid} recorded for {payment.member.user.get_full_name()}.")
                return redirect('finances:record_payment')  # Redirect back to clear form
            except Exception as e:
                messages.error(request, f"Error recording payment: {str(e)}")
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentForm()
        # Pre-fill date
        form.fields['payment_date'].initial = timezone.now().date()

    context = {'form': form}
    return render(request, 'finances/record_payment_form.html', context)

@user_passes_test(is_financial_secretary_or_admin)
def manage_dues(request):
    """View to add individual or bulk dues"""
    individual_due_form = DueForm(prefix="individual")
    bulk_due_form = BulkDueForm(prefix="bulk")

    # Get recent dues excluding superusers
    recent_dues = Due.objects.select_related('member__user') \
        .filter(member__user__is_superuser=False) \
        .order_by('-created_at')[:10]

    if request.method == 'POST':
        print("POST request received")  # Debug log
        print("POST data:", request.POST)  # Debug log
        
        # Check which form was submitted based on button name or hidden field
        if 'submit_individual' in request.POST:
            print("Individual form submitted")  # Debug log
            individual_due_form = DueForm(request.POST, prefix="individual")
            if individual_due_form.is_valid():
                try:
                    print("Individual form is valid")  # Debug log
                    due = individual_due_form.save(commit=False)
                    due.created_at = timezone.now()
                    due.save()
                    print(f"Due saved: {due}")  # Debug log
                    messages.success(request, f"Due '{due.description}' added for {due.member.user.username}.")
                    return redirect('finances:manage_dues')
                except Exception as e:
                    print(f"Error saving individual due: {str(e)}")  # Debug log
                    messages.error(request, f"Error saving individual due: {str(e)}")
            else:
                print("Individual form validation failed")  # Debug log
                print("Form errors:", individual_due_form.errors)  # Debug log
                messages.error(request, 'Error in individual due form. Please check the details entered.')
                bulk_due_form = BulkDueForm(prefix="bulk")
        elif 'submit_bulk' in request.POST:
            print("Bulk form submitted")  # Debug log
            bulk_due_form = BulkDueForm(request.POST, prefix="bulk")
            if bulk_due_form.is_valid():
                print("Bulk form is valid")  # Debug log
                amount = bulk_due_form.cleaned_data['amount_due']
                description = bulk_due_form.cleaned_data['description']
                due_date = bulk_due_form.cleaned_data['due_date']

                # Get active members excluding superusers
                active_members = Profile.objects.filter(
                    status=Profile.Status.ACTIVE,
                    user__is_superuser=False
                )
                dues_to_create = []
                for profile in active_members:
                    dues_to_create.append(
                        Due(member=profile, amount_due=amount, description=description, due_date=due_date)
                    )

                if dues_to_create:
                    try:
                        Due.objects.bulk_create(dues_to_create)
                        messages.success(request, f"Added dues of ₦{amount} to {len(dues_to_create)} active members.")
                        return redirect('finances:manage_dues')
                    except Exception as e:
                        messages.error(request, f"Error creating bulk dues: {str(e)}")
            else:
                messages.error(request, 'Error in bulk due form. Please check the details entered.')
                individual_due_form = DueForm(prefix="individual")

    context = {
        'individual_form': individual_due_form,
        'bulk_form': bulk_due_form,
        'recent_dues': recent_dues
    }
    return render(request, 'finances/manage_dues.html', context)

# --- Member Financial Status View ---

@login_required
def member_financial_status(request, profile_id=None):
    """Display financial status for a member using annotations for consistency."""
    target_profile_pk = None
    can_view_others = request.user.profile.is_financial_secretary or request.user.profile.is_admin

    if profile_id:
        if not can_view_others:
            return HttpResponseForbidden("You do not have permission to view this member's financial status.")
        target_profile_pk = profile_id
    else:
        target_profile_pk = request.user.profile.pk

    if not target_profile_pk:
        messages.error(request, "Could not determine the member profile.")
        return redirect('pages:home')

    # Fetch the specific profile with annotated financial totals
    try:
        profile_with_totals = Profile.objects.select_related('user') \
            .annotate(
                total_dues=Coalesce(
                    Sum('dues__amount_due', distinct=True),
                    Decimal('0.00'),
                    output_field=DecimalField()
                ),
                total_payments=Coalesce(
                    Sum('payments__amount_paid', distinct=True),
                    Decimal('0.00'),
                    output_field=DecimalField()
                )
            ) \
            .annotate(
                balance=F('total_dues') - F('total_payments') # Dues - Payments
            ) \
            .get(pk=target_profile_pk)
    except Profile.DoesNotExist:
        messages.error(request, "Member profile not found.")
        return redirect('users:member_list_admin' if can_view_others else 'pages:home')

    # Fetch detailed dues and payments separately for display
    dues = Due.objects.filter(member=profile_with_totals).order_by('-due_date', '-created_at')
    payments = Payment.objects.filter(member=profile_with_totals).order_by('-payment_date', '-recorded_at')

    context = {
        'target_profile': profile_with_totals, # Profile now includes annotated totals
        'dues': dues, # Detailed list for display
        'payments': payments, # Detailed list for display
        'dues_total': profile_with_totals.total_dues, # From annotation
        'payments_total': profile_with_totals.total_payments, # From annotation
        'balance': profile_with_totals.balance, # From annotation
        'can_view_others': can_view_others,
    }

    return render(request, 'finances/member_financial_status.html', context)
