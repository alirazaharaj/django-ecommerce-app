# Django E-Commerce Platform

A feature-rich, scalable e-commerce web application built with Python and Django. This platform provides a seamless shopping experience with custom product variants, dynamic admin controls, and secure local payment gateway integration.

---

## 🚀 Key Features

* **Custom Product Variants:** Support for multiple product options (e.g., size, color, stock tracking).
* **Secure Authentication:** User registration, login, profile management, and role-based permissions.
* **Shopping Cart & Checkout:** Add to cart, update quantities, dynamic subtotal calculations, and order processing.
* **Payment Gateway Integration:** Integrated with **JazzCash** for secure local online transactions.
* **Dynamic Admin Panel:** Robust Django admin setup for managing products, categories, orders, and customer data.
* **Responsive Design:** Clean and mobile-friendly user interface.

---

## 🛠️ Tech Stack

* **Backend:** Python, Django, Django REST Framework (DRF)
* **Database:** SQLite3 (Development) / PostgreSQL (Production ready)
* **Frontend:** HTML5, CSS3, JavaScript, Bootstrap
* **Payment Integration:** JazzCash API Sandbox/Production
* **Utilities:** WhiteNoise (for static files), Pillow (for image processing)

---

## ⚙️ Installation & Setup Locally

Follow these steps to set up and run the project on your local machine:

### 1. Clone the Repository
```bash
git clone [https://github.com/alirazaharaj/django-ecommerce-app.git](https://github.com/alirazaharaj/django-ecommerce-app.git)
cd django-ecommerce-app
2. Create and Activate a Virtual Environment
Bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
3. Install Dependencies
Bash
pip install -r requirements.txt
4. Configure Environment Variables
Create a .env file in the root directory and add your configurations (database details, SECRET_KEY, JazzCash API credentials, etc.):

Code snippet
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
5. Run Database Migrations
Bash
python manage.py makemigrations
python manage.py migrate
6. Create a Superuser (For Admin Access)
Bash
python manage.py createsuperuser
7. Run the Development Server
Bash
python manage.py runserver
Open your browser and navigate to http://127.0.0.1:8000/ to view the application.

📂 Project Structure
Plaintext
django-ecommerce-app/
│
├── core/                # Main project settings and URL configurations
├── products/            # Product catalog, variants, and category management
├── cart/                # Shopping cart logic and session management
├── orders/              # Order processing and checkout workflows
├── payments/            # JazzCash payment gateway integration modules
├── templates/           # HTML frontend templates
├── static/              # CSS, JavaScript, and image assets
├── media/               # User-uploaded product images
├── manage.py            # Django project management script
└── requirements.txt     # Python package dependencies
🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.
