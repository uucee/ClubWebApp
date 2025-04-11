import os
import django
from django.utils import timezone
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FC92_Club.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Profile
from finances.models import Due, Payment

User = get_user_model()

def create_test_data():
    # Create admin user
    admin_user = User.objects.create_user(
        username='testadmin',
        email='testadmin@fc92club.com',
        password='adminpass123',
        first_name='Test',
        last_name='Admin',
        is_staff=True
    )
    admin_profile = Profile.objects.create(
        user=admin_user,
        role=Profile.Role.ADMIN,
        status='ACT',
        phone='1234567890',
        address='123 Admin Street',
        city='London',
        country='UK'
    )

    # Create financial secretary
    fs_user = User.objects.create_user(
        username='testfs',
        email='testfs@fc92club.com',
        password='fspass123',
        first_name='Test',
        last_name='Financial',
        middle_name='Secretary'
    )
    fs_profile = Profile.objects.create(
        user=fs_user,
        role=Profile.Role.FINANCIAL_SECRETARY,
        status='ACT',
        phone='0987654321',
        address='456 Finance Street',
        city='London',
        country='UK'
    )

    # Create regular members
    members = [
        {
            'username': 'testmember1',
            'email': 'testmember1@fc92club.com',
            'password': 'memberpass123',
            'first_name': 'John',
            'middle_name': 'A',
            'last_name': 'Doe',
            'phone': '1112223333',
            'address': '789 Member Street',
            'city': 'London',
            'country': 'UK'
        },
        {
            'username': 'testmember2',
            'email': 'testmember2@fc92club.com',
            'password': 'memberpass123',
            'first_name': 'Jane',
            'middle_name': 'B',
            'last_name': 'Smith',
            'phone': '4445556666',
            'address': '321 Member Avenue',
            'city': 'London',
            'country': 'UK'
        }
    ]

    for member_data in members:
        user = User.objects.create_user(
            username=member_data['username'],
            email=member_data['email'],
            password=member_data['password'],
            first_name=member_data['first_name'],
            middle_name=member_data['middle_name'],
            last_name=member_data['last_name']
        )
        profile = Profile.objects.create(
            user=user,
            role=Profile.Role.MEMBER,
            status='ACT',
            phone=member_data['phone'],
            address=member_data['address'],
            city=member_data['city'],
            country=member_data['country']
        )

        # Create some dues and payments for each member
        due = Due.objects.create(
            member=profile,
            amount_due=Decimal('50.00'),
            description='Monthly Membership Fee',
            due_date=timezone.now().date()
        )

        payment = Payment.objects.create(
            member=profile,
            amount_paid=Decimal('50.00'),
            payment_date=timezone.now().date(),
            recorded_by=fs_user,
            notes='Test payment'
        )

    print("Test data created successfully!")

if __name__ == '__main__':
    create_test_data() 