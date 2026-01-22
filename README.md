Sipzy – Premium Liquor eCommerce Platform
                                                        
Sipzy is a sophisticated eCommerce web application dedicated to the retail of premium spirits. Built using the Python Django framework and the MVT (Model-View-Template) architecture, the platform provides a seamless shopping experience with robust features including secure payments, real-time inventory management, and a comprehensive rewards system.

Live Project Links
Production Site: arjunj.online

Source Code: GitHub Repository

Core Features

User Experience

Authentication System: Secure user registration and login with OTP verification to ensure account safety.

Advanced Product Management: Product listings with multi-level categories and detailed variants for different sizes and prices.

Cart & Checkout Flow: A dynamic AJAX-powered cart system allowing users to update quantities and variants without page reloads.

Wallet System: Integrated digital wallet for users to maintain a balance, receive refunds, and make quick purchases.

Reviews & Ratings: A feedback system where verified customers can rate products and write reviews.

Promotions & Savings

Coupon Management: A flexible coupon system where users can apply promotional codes to receive flat or percentage-based discounts.

Offer Module: Dedicated product and category-based offers that automatically calculate and display discounted prices.

Order & Payment

Razorpay Integration: Secure and streamlined payment processing using the Razorpay gateway.

Order Tracking: Detailed order history and status updates for users to monitor their purchases from processing to delivery.

Tax & Shipping: Automatic calculation of GST and shipping fees based on the cart total.

Administration

Executive Dashboard: A powerful admin interface to manage inventory, monitor sales reports, and oversee user activity.

System Controls: Tools for creating coupons, managing product offers, and updating order fulfillment statuses.

Technical Stack

Backend: Python Django (MVT Architecture)

Frontend: HTML5, CSS3, JavaScript, Tailwind CSS

Database: PostgreSQL

Payment Gateway: Razorpay

Version Control: Git & GitHub

Project Structure

accounts: Handles user profiles, authentication, and wallet logic.

products: Manages the product catalog, variants, and stock levels.

cart: Contains the logic for session-based and database-persisted shopping carts.

orders: Manages checkout processes, shipping details, and order status.

coupons & offers: Handles the logic for discount validation and price deductions.

templates: Contains the Django HTML templates for the user interface.

Installation and Setup

Clone the Repository

git clone https://github.com/arjunj20/sipzy_project.git
cd sipzy_project
Set Up a Virtual Environment

python -m venv env
source env/bin/activate  # Linux/Mac
env\Scripts\activate     # Windows

Install Dependencies

pip install -r requirements.txt

Configure Environment Variables Create a .env file in the root directory and add your credentials:

SECRET_KEY

DATABASE_URL

RAZORPAY_KEY_ID

RAZORPAY_KEY_SECRET

Database Migration

python manage.py makemigrations
python manage.py migrate
Start the Development Server
python manage.py runserver

Author

Arjun Software Engineer | Django Developer Kerala, India