# Create your views here.
# users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.db import transaction
import csv
from io import StringIO
from .forms import ProfileUpdateForm, AdminProfileUpdateForm, ProfileCompletionForm
from .models import Profile, User
from finances.models import Payment, Due
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import get_user_model, login, authenticate
from django.contrib.auth.hashers import make_password
from django.utils.html import strip_tags
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.views.generic.edit import FormView
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views import View
from .decorators import admin_required, financial_secretary_required
from .mixins import AdminRequiredMixin, FinancialSecretaryRequiredMixin

# --- Permission Helper Functions ---
def is_admin(user):
    return user.is_authenticated and user.is_admin

def is_financial_secretary_or_admin(user):
    return user.is_authenticated and (user.profile.role == 'FS' or user.profile.role == 'ADM' or user.is_superuser)

# --- Member Views ---

@login_required
def profile_view(request, username=None):
    """View profile of current user or specified user."""
    if username:
        # Viewing another user's profile
        target_user = get_object_or_404(User, username=username)
        if not (request.user.profile.role == 'ADM' or request.user == target_user):
            raise PermissionDenied("You don't have permission to view this profile.")
        user_profile = target_user.profile
        is_viewing_own_profile = False
    else:
        # Viewing own profile
        user_profile = request.user.profile
        is_viewing_own_profile = True

    # Calculate financial status
    payments = Payment.objects.filter(member=user_profile)
    dues = Due.objects.filter(member=user_profile)

    total_paid = payments.aggregate(total=Coalesce(Sum('amount_paid'), 0, output_field=DecimalField()))['total']
    total_due = dues.aggregate(total=Coalesce(Sum('amount_due'), 0, output_field=DecimalField()))['total']
    balance = total_paid - total_due  # Positive balance means overpaid, negative means owing

    context = {
        'profile': user_profile,
        'payments': payments.order_by('-payment_date'),
        'dues': dues.order_by('-due_date'),
        'total_paid': total_paid,
        'total_due': total_due,
        'balance': balance,
        'is_viewing_own_profile': is_viewing_own_profile,
        'is_admin': request.user.profile.role == 'ADM'
    }
    return render(request, 'users/profile_detail.html', context)

@login_required
def profile_edit(request, username=None):
    """Edit profile of current user or specified user."""
    if username:
        # Editing another user's profile
        if not request.user.profile.is_admin:
            raise PermissionDenied("You don't have permission to edit this profile.")
        target_user = get_object_or_404(User, username=username)
        profile = target_user.profile
    else:
        # Editing own profile
        profile = request.user.profile

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile has been updated successfully.')
            if username:
                return redirect('users:profile', username=username)
            return redirect('users:profile_view')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileUpdateForm(instance=profile)

    context = {
        'form': form,
        'user': profile.user,
        'is_editing_other': username is not None
    }
    return render(request, 'users/profile_form.html', context)


# --- Admin/FS Views ---

@user_passes_test(is_financial_secretary_or_admin)
def member_list(request):
    """Admin/FS view to list all members with their financial balance."""
    # First get all non-superuser profiles
    profiles = Profile.objects.select_related('user') \
        .exclude(user__is_superuser=True) \
        .filter(user__is_superuser=False) \
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
            balance=F('total_dues') - F('total_payments') # Dues - Payments (Positive = Owed)
        ) \
        .order_by('user__last_name', 'user__first_name')

    context = {'profiles': profiles}
    return render(request, 'users/member_list_admin.html', context)

@login_required
@user_passes_test(lambda u: u.profile.role == 'ADM')
def toggle_member_access(request, user_id):
    """Admin view to toggle User.is_active"""
    target_user = get_object_or_404(User, pk=user_id)
    if target_user.is_superuser: # Prevent locking out superuser
         messages.error(request, 'Cannot block a superuser.')
         return redirect('users:member_list') # Or wherever admin manages users

    if request.method == 'POST':
        target_user.is_active = not target_user.is_active
        target_user.save()
        status = "enabled" if target_user.is_active else "disabled"
        messages.success(request, f'Access for {target_user.username} has been {status}.')
        return redirect('users:member_list') # Redirect back to the list

    # Avoid direct GET toggle for security, maybe show a confirmation page?
    # For simplicity here, we just redirect if accessed via GET
    return redirect('users:member_list')


@user_passes_test(is_financial_secretary_or_admin)
def member_financial_detail(request, user_id):
    """FS/Admin view of a specific member's financial details"""
    target_user = get_object_or_404(User, pk=user_id)
    profile = target_user.profile

    payments = Payment.objects.filter(member=profile)
    dues = Due.objects.filter(member=profile)
    total_paid = payments.aggregate(total=Coalesce(Sum('amount_paid'), 0, output_field=DecimalField()))['total']
    total_due = dues.aggregate(total=Coalesce(Sum('amount_due'), 0, output_field=DecimalField()))['total']
    balance = total_paid - total_due

    context = {
        'member_profile': profile,
        'payments': payments.order_by('-payment_date'),
        'dues': dues.order_by('-due_date'),
        'total_paid': total_paid,
        'total_due': total_due,
        'balance': balance,
    }
    # Could use a different template from member's own view if needed
    return render(request, 'users/member_financial_detail_fs.html', context)

@user_passes_test(is_financial_secretary_or_admin)
def update_member_status(request, profile_id):
    """FS/Admin view to update member's status (Active/Suspended/Removed)"""
    profile = get_object_or_404(Profile, pk=profile_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in [s[0] for s in Profile.STATUS_CHOICES]:
            profile.status = new_status
            profile.save()
            messages.success(request, f"{profile.user.username}'s status updated to {profile.get_status_display()}.")
            # Redirect to the financial detail page or member list
            return redirect('member_financial_detail_fs', user_id=profile.user.id)
        else:
            messages.error(request, "Invalid status selected.")

    # Typically this would be part of another view (like member_financial_detail_fs)
    # or handled via Django Admin. Adding a dedicated page might be overkill.
    # Redirect if accessed via GET.
    return redirect('member_financial_detail_fs', user_id=profile.user.id)

@user_passes_test(is_financial_secretary_or_admin)
@csrf_protect
def member_management(request):
    """Admin/FS view for managing members and sending invitations."""
    return render(request, 'users/member_management.html')

@user_passes_test(is_financial_secretary_or_admin)
@csrf_protect
def add_single_member(request):
    """Add a single member and optionally send invitation."""
    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            role = request.POST.get('role', 'MEM')  # Default to MEM if not specified
            send_invite = request.POST.get('send_invite') == 'on'

            # Validate required fields
            if not all([first_name, last_name, email]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('users:member_management')

            # Financial secretaries can only add regular members
            if request.user.profile.role == 'FS' and role != 'MEM':
                messages.error(request, 'Financial secretaries can only add regular members.')
                return redirect('users:member_management')

            # Check if user already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, f'User with email {email} already exists.')
                return redirect('users:member_management')

            # Validate role
            if role not in [choice[0] for choice in Profile.ROLES]:
                messages.error(request, 'Invalid role specified.')
                return redirect('users:member_management')

            with transaction.atomic():
                # Create user with temporary password
                temp_password = get_random_string(12)
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=temp_password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True
                )

                profile = user.profile # Get the profile created by the signal
                profile.role = role # Set the role specified in the form

                email_sent_successfully = False # Flag to track email status
                email_error_message = None # Store specific email error

                if send_invite:
                    try:
                        # Prepare email context
                    
                        profile.invitation_token = get_random_string(32)
                        profile.invitation_sent_at = timezone.now()
                        context = {
                            'first_name': first_name,
                            'last_name': last_name,
                            'email': email,
                            'invitation_link': request.build_absolute_uri(f'/users/accept-invitation/{profile.invitation_token}/'),
                        '   site_url': request.build_absolute_uri('/')
                        }
                        # Render email body
                        message = render_to_string('users/email/invitation_email.txt', context)
                        # Attempt to send email
                        send_mail(
                            'Welcome to FC92 Club',
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            fail_silently=False,
                        )
                        email_sent_successfully = True # Mark as success if no exception

                    except Exception as email_error: # Catch ANY exception during email process
                        # Log the specific email error for debugging
                        print(f"ERROR sending invitation email to {email}: {email_error}")
                        # Optionally use logging module: import logging; logging.exception(f"ERROR sending invitation email to {email}")
                        email_error_message = str(email_error) # Store error message for user feedback

                profile.save() # Save the profile changes (role, token, sent_at)
         # Display messages outside the transaction block
            messages.success(request, f'Member {first_name} {last_name} added successfully.')
            if send_invite:
                if email_sent_successfully:
                    messages.info(request, 'Invitation email sent.')
                else:
                    # Provide specific feedback if email failed
                    messages.warning(request, f'Member added, but failed to send invitation email: {email_error_message or "Unknown error"}')

        except Exception as e: # Catch other potential errors (e.g., user creation)
             # Avoid catching the email error again if it was already handled
            if 'email_error' not in locals() or e is not email_error:
                 messages.error(request, f'Error adding member: {str(e)}')


    return redirect('users:member_management')

@user_passes_test(is_financial_secretary_or_admin)
@csrf_protect
def bulk_upload_members(request):
    """Handle bulk member upload via CSV file."""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        send_invite = request.POST.get('send_invite') == 'on'
        
        if not csv_file:
            messages.error(request, 'Please select a CSV file to upload.')
            return redirect('users:member_management')
            
        try:
            # Read CSV file
            csv_data = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(StringIO(csv_data))
            
            success_count = 0
            error_count = 0
            
            for row in csv_reader:
                try:
                    # Validate required fields
                    if not all(k in row for k in ['first_name', 'last_name', 'email']):
                        raise ValueError('Missing required fields in CSV row')
                        
                    # Check if user already exists
                    if User.objects.filter(email=row['email']).exists():
                        raise ValueError(f"User with email {row['email']} already exists")
                        
                    # Determine role (default to MEM if not specified or not admin)
                    role = row.get('role', 'MEM')
                    if not request.user.profile.is_admin:
                        role = 'MEM'  # Force member role for non-admin users
                    elif role not in ['MEM', 'ADM', 'FS']:
                        role = 'MEM'  # Default to member if invalid role specified
                        
                    with transaction.atomic():
                        # Create user with temporary password
                        temp_password = get_random_string(12)
                        user = User.objects.create_user(
                            username=row['email'],
                            email=row['email'],
                            password=temp_password,
                            first_name=row['first_name'],
                            last_name=row['last_name'],
                            is_active=True
                        )
                        
                        profile = user.profile # Get the profile created by the signal
                        profile.role = role # Set the role specified in the form

                        if send_invite:
                            profile.invitation_token = get_random_string(32)
                            profile.invitation_sent_at = timezone.now()
                            # Send invitation email
                            context = {
                                'first_name': row['first_name'],
                                'last_name': row['last_name'],
                                'email': row['email'],
                                'invitation_link': request.build_absolute_uri(f'/users/accept-invitation/{profile.invitation_token}/'),
                                'site_url': request.build_absolute_uri('/')
                            }
                            message = render_to_string('users/email/invitation_email.txt', context)
                            send_mail(
                                'Welcome to FC92 Club',
                                message,
                                settings.DEFAULT_FROM_EMAIL,
                                [row['email']],
                                fail_silently=False,
                            )
                        profile.save() # Save the profile changes (role, token, sent_at)
                        
                        success_count += 1
                except Exception as e:
                    error_count += 1
                    messages.error(request, f'Error processing {row.get("email", "unknown")}: {str(e)}')
            
            
            
            if success_count > 0:
                messages.success(request, f'Successfully processed {success_count} member(s).')
            if error_count > 0:
                messages.warning(request, f'Failed to process {error_count} member(s).')
                
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            
    return redirect('users:member_management')

@user_passes_test(is_financial_secretary_or_admin)
@csrf_protect
def send_bulk_invites(request):
    """Send invitations to multiple members."""
    if request.method == 'POST':
        try:
            emails = request.POST.get('emails', '').strip()
            if not emails:
                messages.error(request, 'Please enter at least one email address.')
                return redirect('users:member_management')
                
            email_list = [email.strip() for email in emails.split('\n') if email.strip()]
            success_count = 0
            error_count = 0
            
            for email in email_list:
                try:
                    # Check if user already exists
                    if User.objects.filter(email=email).exists():
                        raise ValueError(f"User with email {email} already exists")
                        
                    # Create user with temporary password
                    temp_password = get_random_string(12)
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=temp_password,
                        is_active=True
                    )
                    
                    profile = user.profile # Get the profile created by the signal
                    profile.role = 'MEM' # Set the role specified in the form

                    # Send invitation email
                    profile.invitation_token = get_random_string(32)
                    profile.invitation_sent_at = timezone.now()
                    
                    context = {
                        'email': email,
                        'invitation_link': request.build_absolute_uri(f'/users/accept-invitation/{profile.invitation_token}/'),
                        'site_url': request.build_absolute_uri('/')
                    }
                    message = render_to_string('users/email/invitation_email.txt', context)
                    send_mail(
                        'Welcome to FC92 Club',
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    profile.save() # Save the profile changes (role, token, sent_at)
                    
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    messages.error(request, f'Error sending invitation to {email}: {str(e)}')
            
            if success_count > 0:
                messages.success(request, f'Successfully sent {success_count} invitation(s).')
            if error_count > 0:
                messages.warning(request, f'Failed to send {error_count} invitation(s).')
                
        except Exception as e:
            messages.error(request, f'Error processing invitations: {str(e)}')
            
    return redirect('users:member_management')

@login_required
@user_passes_test(lambda u: u.profile.role == 'ADM')
def delete_member(request, user_id):
    """Admin view to delete a member and their profile."""
    target_user = get_object_or_404(User, pk=user_id)
    
    # Prevent deleting superusers
    if target_user.is_superuser:
        messages.error(request, 'Cannot delete a superuser.')
        return redirect('users:member_list')
    
    if request.method == 'POST':
        try:
            # Delete the user (this will cascade delete the profile)
            target_user.delete()
            messages.success(request, f'Member {target_user.username} has been deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting member: {str(e)}')
        
        return redirect('users:member_list')

@user_passes_test(is_financial_secretary_or_admin)
def financial_report(request):
    # Get filter status from request
    filter_status = request.GET.get('status', '')
    download = request.GET.get('download', False)

    # Get all profiles excluding admins and superusers
    profiles = Profile.objects.filter(
        user__is_superuser=False,
        user__is_staff=False
    ).select_related('user').annotate(
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
    ).annotate(
        balance=F('total_dues') - F('total_payments')
    ).order_by('user__last_name', 'user__first_name')

    # Apply filter if specified
    if filter_status == 'up_to_date':
        profiles = profiles.filter(balance__lte=0)  # Balance <= 0 means up to date
    elif filter_status == 'overdue':
        profiles = profiles.filter(balance__gt=0)  # Balance > 0 means overdue

    # Calculate totals
    total_dues = profiles.aggregate(total=Sum('total_dues'))['total'] or Decimal('0.00')
    total_payments = profiles.aggregate(total=Sum('total_payments'))['total'] or Decimal('0.00')
    total_balance = total_dues - total_payments

    # Calculate up to date members count
    up_to_date_count = profiles.filter(balance__lte=0).count()
    total_members = profiles.count()

    context = {
        'profiles': profiles,
        'total_dues': total_dues,
        'total_payments': total_payments,
        'total_balance': total_balance,
        'is_financial_secretary': request.user.profile.role == 'financial_secretary',
        'up_to_date_count': up_to_date_count,
        'total_members': total_members,
        'filter_status': filter_status,
    }

    # Handle download request
    if download:
        import csv
        from django.http import HttpResponse
        from io import StringIO

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="financial_report.csv"'

        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        
        # Write header
        writer.writerow([
            'Member Name',
            'Total Dues (₦)',
            'Total Payments (₦)',
            'Balance (₦)',
            'Status',
            'Financial Status'
        ])

        # Write data
        for profile in profiles:
            writer.writerow([
                profile.user.get_full_name(),
                profile.total_dues,
                profile.total_payments,
                profile.balance,
                profile.get_status_display(),
                'Up to Date' if profile.balance <= 0 else 'Overdue'
            ])

        # Write summary
        writer.writerow([])
        writer.writerow(['Summary'])
        writer.writerow(['Total Dues:', total_dues])
        writer.writerow(['Total Payments:', total_payments])
        writer.writerow(['Total Balance:', total_balance])
        writer.writerow(['Up to Date Members:', f'{up_to_date_count}/{total_members}'])

        response.write(csv_buffer.getvalue())
        return response

    return render(request, 'users/financial_report.html', context)

@login_required
@user_passes_test(lambda u: u.profile.role == 'ADM')
def admin_reset_password(request, user_id):
    User = get_user_model()
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Generate a random password
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(alphabet) for i in range(12))
        
        # Update user's password
        user.password = make_password(new_password)
        user.save()
        
        # Send email to user
        subject = 'Your password has been reset'
        html_message = render_to_string('users/password_reset_email.html', {
            'user': user,
            'new_password': new_password,
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            messages.success(request, f'Password has been reset for {user.username}. An email has been sent with the new password.')
        except Exception as e:
            messages.error(request, f'Password was reset but email could not be sent: {str(e)}')
        
        return redirect('users:member_list')
    
    return render(request, 'users/admin_reset_password.html', {'user': user})

@csrf_protect
def accept_invitation(request, token):
    """Handle user accepting an invitation and completing their profile."""
    try:
        # Get profile by token, ensure token isn't expired (7 days)
        profile = get_object_or_404(
            Profile,
            invitation_token=token,
            invitation_sent_at__gte=timezone.now() - timedelta(days=7)
        )
        user = profile.user

        # If user is already active, redirect to login
        if user.is_active:
            messages.info(request, 'This invitation has already been used.')
            return redirect('users:login')

        if request.method == 'POST':
            form = ProfileCompletionForm(
                request.POST,
                instance=profile,
                user_instance=user
            )
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # Update User data first
                        user.username = form.cleaned_data['username']
                        user.email = form.cleaned_data['email']
                        user.first_name = form.cleaned_data['first_name']
                        user.middle_name = form.cleaned_data.get('middle_name', '')
                        user.last_name = form.cleaned_data['last_name']
                        user.set_password(form.cleaned_data['password'])
                        user.is_active = True
                        user.save()

                        # Update Profile data
                        profile = form.save(commit=False)
                        profile.invitation_token = None
                        profile.invitation_sent_at = None
                        profile.save()

                        # Create a new session
                        request.session.create()
                        
                        # Log the user in
                        login(request, user)
                        
                        messages.success(request, 'Welcome! Your profile has been created successfully.')
                        return redirect('users:dashboard')

                except Exception as e:
                    messages.error(request, f'Error updating profile: {str(e)}')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            form = ProfileCompletionForm(instance=profile, user_instance=user)

        return render(request, 'users/accept_invitation.html', {
            'form': form,
            'token': token,
        })

    except Profile.DoesNotExist:
        messages.error(request, 'Invalid or expired invitation token.')
        return redirect('users:login')
