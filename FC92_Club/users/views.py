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

# --- Permission Helper Functions ---
def is_admin(user):
    return user.is_authenticated and user.profile.is_admin

def is_financial_secretary_or_admin(user):
    return user.is_authenticated and user.profile.is_financial_secretary

# --- Member Views ---

@login_required
def profile_view(request):
    # Calculate financial status here
    user_profile = request.user.profile
    payments = Payment.objects.filter(member=user_profile)
    dues = Due.objects.filter(member=user_profile)

    total_paid = payments.aggregate(total=Coalesce(Sum('amount_paid'), 0, output_field=DecimalField()))['total']
    total_due = dues.aggregate(total=Coalesce(Sum('amount_due'), 0, output_field=DecimalField()))['total']
    balance = total_paid - total_due # Positive balance means overpaid, negative means owing

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
def profile_edit(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            # Optionally update first/last name on User model if needed
            # request.user.first_name = request.POST.get('first_name') ...
            # request.user.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile_view')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileUpdateForm(instance=profile)

    context = {
        'form': form,
        'user': request.user # Pass user for potentially editing first/last name etc.
    }
    return render(request, 'users/profile_form.html', context)


# --- Admin/FS Views ---

@user_passes_test(is_financial_secretary_or_admin)
def member_list(request):
    """Admin/FS view to list all members with their financial balance."""
    members = Profile.objects.select_related('user') \
        .exclude(role=Profile.Role.ADMIN) \
        .exclude(user__is_superuser=True) \
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

    context = {'members': members}
    return render(request, 'users/member_list_admin.html', context)

@user_passes_test(is_admin)
def toggle_member_access(request, user_id):
    """Admin view to toggle User.is_active"""
    target_user = get_object_or_404(User, pk=user_id)
    if target_user.is_superuser: # Prevent locking out superuser
         messages.error(request, 'Cannot block a superuser.')
         return redirect('member_list_admin') # Or wherever admin manages users

    if request.method == 'POST':
        target_user.is_active = not target_user.is_active
        target_user.save()
        status = "enabled" if target_user.is_active else "disabled"
        messages.success(request, f'Access for {target_user.username} has been {status}.')
        return redirect('member_list_admin') # Redirect back to the list

    # Avoid direct GET toggle for security, maybe show a confirmation page?
    # For simplicity here, we just redirect if accessed via GET
    return redirect('member_list_admin')


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

@user_passes_test(is_admin)
def member_management(request):
    """Admin view for managing members and sending invitations."""
    return render(request, 'users/member_management.html')

@user_passes_test(is_admin)
def add_single_member(request):
    """Add a single member and optionally send invitation."""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        role = request.POST.get('role')
        send_invite = request.POST.get('send_invite') == 'on'

        try:
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

                # Create profile with proper role value
                role_value = 'FS' if role == 'FINANCIAL_SECRETARY' else 'MEM'
                Profile.objects.create(
                    user=user,
                    role=role_value
                )

                if send_invite:
                    # Send invitation email
                    context = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'temp_password': temp_password,
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

    return redirect('member_management')

@user_passes_test(is_admin)
def bulk_upload_members(request):
    """Handle bulk member upload via CSV."""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        send_invite = request.POST.get('send_invite') == 'on'
        
        try:
            # Read CSV file
            csv_data = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(StringIO(csv_data))
            
            # Validate required columns
            required_columns = {'first_name', 'last_name', 'email', 'role'}
            if not required_columns.issubset(csv_reader.fieldnames):
                missing_columns = required_columns - set(csv_reader.fieldnames)
                messages.error(request, f'CSV file missing required columns: {", ".join(missing_columns)}')
                return redirect('member_management')
            
            success_count = 0
            error_count = 0
            error_details = []
            
            with transaction.atomic():
                for row_num, row in enumerate(csv_reader, start=2):  # start=2 because row 1 is header
                    try:
                        # Validate required fields
                        if not all(row.get(field) for field in required_columns):
                            raise ValueError(f"Missing required fields in row {row_num}")
                            
                        first_name = row['first_name'].strip()
                        last_name = row['last_name'].strip()
                        email = row['email'].strip().lower()  # Normalize email to lowercase
                        role = row['role'].strip().upper()
                        
                        # Validate email format
                        if not '@' in email:
                            raise ValueError(f"Invalid email format in row {row_num}")
                            
                        # Check if user already exists
                        if User.objects.filter(email=email).exists():
                            raise ValueError(f"User with email {email} already exists")
                        
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
                        
                        # Create profile with proper role value
                        role_value = 'FS' if role == 'FINANCIAL_SECRETARY' else 'MEM'
                        Profile.objects.create(
                            user=user,
                            role=role_value
                        )
                        
                        if send_invite:
                            # Send invitation email
                            context = {
                                'first_name': first_name,
                                'last_name': last_name,
                                'email': email,
                                'temp_password': temp_password,
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
                        error_details.append(f"Row {row_num}: {str(e)}")
                        continue
                
                if success_count > 0:
                    messages.success(request, f'Successfully added {success_count} members.')
                if error_count > 0:
                    messages.warning(request, f'Failed to add {error_count} members.')
                    # Show detailed error messages
                    for error in error_details:
                        messages.warning(request, error)
                if send_invite and success_count > 0:
                    messages.info(request, 'Invitation emails sent to new members.')
                    
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
    
    return redirect('member_management')

@user_passes_test(is_admin)
def send_bulk_invites(request):
    """Send invitations to potential new members."""
    if request.method == 'POST':
        emails = request.POST.get('emails', '').splitlines()
        success_count = 0
        error_count = 0
        error_details = []
        
        for email in emails:
            email = email.strip()
            if not email:
                continue
                
            try:
                # Validate email format
                if not '@' in email:
                    raise ValueError(f"Invalid email format: {email}")
                    
                # Check if user already exists
                if User.objects.filter(email=email).exists():
                    raise ValueError(f"User with email {email} already exists")
                
                # Generate temporary username and password
                temp_username = f"temp_{get_random_string(8)}"
                temp_password = get_random_string(12)
                
                # Create temporary user account
                user = User.objects.create_user(
                    username=temp_username,
                    email=email,
                    password=temp_password,
                    is_active=True
                )
                
                # Create temporary profile with correct status value
                profile = Profile.objects.create(
                    user=user,
                    role='MEM',  # Default to member role
                    status='PEN',  # Use the correct status code
                    invitation_token=get_random_string(32),
                    invitation_sent_at=timezone.now()
                )
                
                # Send invitation email
                context = {
                    'email': email,
                    'invitation_link': request.build_absolute_uri(f'/users/accept-invitation/{profile.invitation_token}/')
                }
                message = render_to_string('users/email/invitation_email.txt', context)
                send_mail(
                    'Invitation to Join FC92 Club',
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                error_details.append(f"Email {email}: {str(e)}")
                continue
        
        if success_count > 0:
            messages.success(request, f'Successfully sent {success_count} invitations.')
        if error_count > 0:
            messages.warning(request, f'Failed to send {error_count} invitations.')
            # Show detailed error messages
            for error in error_details:
                messages.warning(request, error)
    
    return redirect('member_management')

def accept_invitation(request, token):
    """Handle invitation acceptance and profile completion."""
    try:
        profile = Profile.objects.get(invitation_token=token)
        
        # Check if invitation is expired (7 days)
        if profile.invitation_sent_at and (timezone.now() - profile.invitation_sent_at) > timedelta(days=7):
            messages.error(request, 'This invitation link has expired. Please contact the club administrator for a new invitation.')
            return redirect('home')
            
        if request.method == 'POST':
            # Get form data directly from request.POST
            username = request.POST.get('username')
            password = request.POST.get('password')
            password_confirm = request.POST.get('password_confirm')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            
            # Validate all required fields
            if not all([username, password, password_confirm, first_name, last_name, phone, address]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('accept_invitation', token=token)
            
            # Validate password match
            if password != password_confirm:
                messages.error(request, 'Passwords do not match.')
                return redirect('accept_invitation', token=token)
            
            # Validate password strength
            if len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                return redirect('accept_invitation', token=token)
            
            # Check if username is already taken
            if User.objects.filter(username=username).exists():
                messages.error(request, 'This username is already taken. Please choose another one.')
                return redirect('accept_invitation', token=token)
            
            try:
                # Update user information
                user = profile.user
                user.username = username
                user.set_password(password)  # This hashes the password
                user.first_name = first_name
                user.last_name = last_name
                user.save()
                
                # Update profile
                profile.phone = phone
                profile.address = address
                profile.status = 'ACT'  # Activate the profile
                profile.invitation_token = None  # Clear the token
                profile.save()
                
                messages.success(request, 'Your profile has been updated successfully. You can now log in with your new username and password.')
                return redirect('login')
            except Exception as e:
                messages.error(request, f'Error updating profile: {str(e)}')
                return redirect('accept_invitation', token=token)
            
        context = {
            'profile': profile
        }
        return render(request, 'users/accept_invitation.html', context)
        
    except Profile.DoesNotExist:
        messages.error(request, 'Invalid invitation link.')
        return redirect('home')
