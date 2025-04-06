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
from .forms import ProfileUpdateForm
from .models import Profile, User
from finances.models import Payment, Due # Import finance models
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal # Import Decimal
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_protect

# --- Permission Helper Functions ---
def is_admin(user):
    return user.is_authenticated and user.is_admin

def is_financial_secretary_or_admin(user):
    return user.is_authenticated and (user.is_financial_secretary or user.is_admin or user.is_superuser)

# --- Member Views ---

@login_required
def profile_view(request, username=None):
    """View profile of current user or specified user."""
    if username:
        # Viewing another user's profile
        target_user = get_object_or_404(User, username=username)
        if not (request.user.is_staff or request.user.profile.is_financial_secretary or request.user == target_user):
            raise PermissionDenied("You don't have permission to view this profile.")
        user_profile = target_user.profile
    else:
        # Viewing own profile
        user_profile = request.user.profile

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

@user_passes_test(is_admin)
def toggle_member_access(request, user_id):
    """Admin view to toggle User.is_active"""
    target_user = get_object_or_404(User, pk=user_id)
    if target_user.is_superuser: # Prevent locking out superuser
         messages.error(request, 'Cannot block a superuser.')
         return redirect('users:member_list_admin') # Or wherever admin manages users

    if request.method == 'POST':
        target_user.is_active = not target_user.is_active
        target_user.save()
        status = "enabled" if target_user.is_active else "disabled"
        messages.success(request, f'Access for {target_user.username} has been {status}.')
        return redirect('users:member_list_admin') # Redirect back to the list

    # Avoid direct GET toggle for security, maybe show a confirmation page?
    # For simplicity here, we just redirect if accessed via GET
    return redirect('users:member_list_admin')


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
        if new_status in [s[0] for s in Profile.Status.choices]:
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
            role = request.POST.get('role')
            send_invite = request.POST.get('send_invite') == 'on'

            # Financial secretaries can only add regular members
            if request.user.profile.is_financial_secretary and role == 'FINANCIAL_SECRETARY':
                messages.error(request, 'Financial secretaries cannot add other financial secretaries.')
                return redirect('users:member_management')

            # Check if user already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, f'User with email {email} already exists.')
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

                # Create profile with proper role value and invitation token
                role_value = 'FS' if role == 'FINANCIAL_SECRETARY' else ('ADM' if role == 'ADMIN' else 'MEM')
                profile = Profile.objects.create(
                    user=user,
                    role=role_value,
                    invitation_token=get_random_string(32),
                    invitation_sent_at=timezone.now()
                )

                if send_invite:
                    # Send invitation email
                    context = {
                        'first_name': first_name,
                        'last_name': last_name,
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

                messages.success(request, f'Member {first_name} {last_name} added successfully.')
                if send_invite:
                    messages.info(request, 'Invitation email sent.')
        except Exception as e:
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
                        
                    # Determine role (default to MEMBER if not specified or not admin)
                    role = row.get('role', 'MEMBER')
                    if not request.user.profile.is_admin:
                        role = 'MEMBER'  # Force member role for non-admin users
                        
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
                        
                        # Create profile with proper role value
                        role_value = 'FS' if role == 'FINANCIAL_SECRETARY' else ('ADM' if role == 'ADMIN' else 'MEM')
                        profile = Profile.objects.create(
                            user=user,
                            role=role_value,
                            invitation_token=get_random_string(32) if send_invite else None,
                            invitation_sent_at=timezone.now() if send_invite else None
                        )
                        
                        if send_invite:
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
                    
                    # Create profile with invitation token
                    profile = Profile.objects.create(
                        user=user,
                        role='MEM',  # Regular member
                        invitation_token=get_random_string(32),
                        invitation_sent_at=timezone.now()
                    )
                    
                    # Send invitation email
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

@csrf_protect
def accept_invitation(request, token):
    """Handle invitation acceptance and profile completion."""
    try:
        profile = Profile.objects.get(invitation_token=token)
        
        # Check if invitation is expired (7 days)
        if profile.invitation_sent_at and (timezone.now() - profile.invitation_sent_at) > timedelta(days=7):
            messages.error(request, 'This invitation link has expired. Please contact the club administrator for a new invitation.')
            return redirect('pages:home')
            
        if request.method == 'POST':
            # Get form data directly from request.POST
            username = request.POST.get('username')
            password = request.POST.get('password')
            password_confirm = request.POST.get('password_confirm')
            first_name = request.POST.get('first_name')
            middle_name = request.POST.get('middle_name')
            last_name = request.POST.get('last_name')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            city = request.POST.get('city')
            country = request.POST.get('country')
            
            # Validate all required fields
            if not all([username, password, password_confirm, first_name, last_name, phone, address, city, country]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('users:accept_invitation', token=token)
            
            # Validate password match
            if password != password_confirm:
                messages.error(request, 'Passwords do not match.')
                return redirect('users:accept_invitation', token=token)
            
            # Validate password strength
            if len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                return redirect('users:accept_invitation', token=token)
            
            # Check if username is already taken by another user
            if User.objects.filter(username=username).exclude(id=profile.user.id).exists():
                messages.error(request, 'This username is already taken. Please choose another one.')
                return redirect('users:accept_invitation', token=token)
            
            try:
                # Update user information
                user = profile.user
                user.username = username
                user.set_password(password)  # This hashes the password
                user.first_name = first_name
                user.middle_name = middle_name
                user.last_name = last_name
                user.save()
                
                # Update profile
                profile.phone = phone
                profile.address = address
                profile.city = city
                profile.country = country
                profile.status = 'ACT'  # Activate the profile
                profile.invitation_token = None  # Clear the token
                profile.save()
                
                # Log the user in with their new credentials
                from django.contrib.auth import login
                login(request, user)
                
                messages.success(request, 'Your profile has been updated successfully.')
                return redirect('users:profile_view')
            except Exception as e:
                messages.error(request, f'Error updating profile: {str(e)}')
                return redirect('users:accept_invitation', token=token)
            
        # Pre-populate form with existing user data
        user = profile.user
        context = {
            'profile': profile,
            'initial_data': {
                'first_name': user.first_name,
                'middle_name': user.middle_name,
                'last_name': user.last_name,
                'email': user.email,
                'username': user.email,  # Default username to email
            }
        }
        return render(request, 'users/accept_invitation.html', context)
        
    except Profile.DoesNotExist:
        messages.error(request, 'Invalid invitation link.')
        return redirect('pages:home')

@user_passes_test(is_admin)
def delete_member(request, user_id):
    """Admin view to delete a member and their profile."""
    target_user = get_object_or_404(User, pk=user_id)
    
    # Prevent deleting superusers
    if target_user.is_superuser:
        messages.error(request, 'Cannot delete a superuser.')
        return redirect('users:member_list_admin')
    
    if request.method == 'POST':
        try:
            # Delete the user (this will cascade delete the profile)
            target_user.delete()
            messages.success(request, f'Member {target_user.username} has been deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting member: {str(e)}')
        
        return redirect('users:member_list_admin')

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
