# FC92 Club Web Application

A Django-based web application for managing FC92 Club membership and finances.

## Features

- User Management
  - Member registration and profile management
  - Role-based access control (Admin, Financial Secretary, Members)
  - Email-based invitation system for new members

- Financial Management
  - Track member dues and payments
  - Financial dashboard for administrators
  - Individual member financial status
  - Payment recording system

## Technology Stack

- Python 3.13
- Django 5.2
- PostgreSQL
- Bootstrap 5
- Crispy Forms

## Installation

1. Clone the repository:
```bash
git clone https://github.com/uucee/ClubWebApp.git
cd ClubWebApp
```

2. Create and activate a virtual environment:
```bash
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the database:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Environment Variables

The following environment variables need to be set:

- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to True for development
- `DATABASE_URL`: PostgreSQL database URL
- `EMAIL_HOST`: SMTP server host
- `EMAIL_PORT`: SMTP server port
- `EMAIL_HOST_USER`: SMTP username
- `EMAIL_HOST_PASSWORD`: SMTP password

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 