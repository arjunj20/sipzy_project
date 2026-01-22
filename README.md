Django eCommerce Application (MVT Based)

A Django-based eCommerce web application built using the Model–View–Template (MVT) architecture.
The project focuses on implementing real-world eCommerce features such as cart management, coupons, orders, and payment integration using Django’s standard approach.

Architecture

This project follows Django’s MVT (Model–View–Template) pattern:

Models – Database structure and business logic

Views – Request handling and application logic

Templates – User interface (HTML, CSS, JS)

Features
User Side

User authentication (Signup, Login, OTP verification)

Product listing & product detail pages

Product variants with stock & pricing

Cart functionality (Add, update, remove)

Coupon apply & discount calculation

Tax and shipping fee calculation

Order placement and order history

Razorpay payment integration

Breadcrumb navigation for better UX

Admin Side

Product & category management

Product variants

Offers & discounts

Coupon creation and deletion

Order management

User management

Tech Stack
Layer	Technology
Backend	Django (MVT)
Frontend	Django Templates, HTML, CSS, JavaScript
Database	PostgreSQL 
Payment Gateway	Razorpay
Authentication	Django Auth + OTP
Styling	Tailwind CSS / Custom CSS
📁 Project Structure
project_root/
│
├── accounts/        # Authentication & user profile
├── products/        # Products, categories, variants
├── cart/            # Cart logic
├── orders/          # Orders & checkout
├── coupons/         # Coupon system
├── offers/          # Product offers
├── templates/       # Django templates
├── static/          # CSS, JS, images
├── manage.py
└── README.md

Installation & Setup Clone Repository
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

 Create Virtual Environment
python -m venv env
source env/bin/activate   # Linux / Mac
env\Scripts\activate      # Windows

Install Dependencies
pip install -r requirements.txt

 Environment Variables

Create a .env file:

SECRET_KEY=your_secret_key
DEBUG=True
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_key_secret

5️⃣ Database Setup
python manage.py makemigrations
python manage.py migrate

6️⃣ Create Admin User
python manage.py createsuperuser

7️⃣ Run Server
python manage.py runserver


Open -> http://127.0.0.1:8000/

 Razorpay Payment Flow

User places an order

Razorpay checkout opens

Payment verification handled on server

Order status updated after successful payment

 Learning Outcome

This project helped in gaining hands-on experience with:

Django MVT workflow

Session-based cart handling

Decimal-safe price calculations

Coupon and offer logic

Payment gateway integration

Admin & user role separation

 Author

Arjun
Software Engineer | Django Developer
Kerala, India 
