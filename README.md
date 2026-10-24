# Django E-Commerce Web Application 🚀

A full-featured e-commerce web platform built with **Django** and **Django REST Framework (DRF)**. This platform features custom product variants, dynamic admin controls, and secure payment gateway integration (JazzCash).

---

## 🚀 Key Features

* **Dynamic Product Management:** Custom product variants and categories with powerful admin controls.
* **RESTful APIs:** Built using Django REST Framework for scalable backend operations.
* **Secure Authentication:** User registration, login, profile management, and role-based permissions.
* **Shopping Cart & Checkout:** Add to cart, update quantities, dynamic subtotal calculations, and order processing.
* **Payment Integration:** Integrated with **JazzCash** for secure local online transactions.
* **Dynamic Admin Panel:** Robust Django admin setup for managing products, categories, orders, and customer data.
* **Responsive UI:** Clean and mobile-friendly user interface.

---

## 🛠️ Tech Stack & Tools

* **Backend:** Python, Django, Django REST Framework (DRF)
* **Database:** SQLite3 (Development) / PostgreSQL (Production ready)
* **Frontend:** HTML5, CSS3, JavaScript, Bootstrap
* **Payment Integration:** JazzCash API Sandbox/Production
* **Utilities:** WhiteNoise (for static files), Pillow (for image processing)
* **Version Control:** Git & GitHub

---

## ⚙️ Installation & Setup Locally

Follow these steps to set up and run the project on your local machine.

### 1. Clone the Repository
```bash
git clone https://github.com/alirazaharaj/django-ecommerce-app.git
cd django-ecommerce-app
2. Create and Activate a Virtual Environment
bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
3. Install Dependencies
bash
pip install -r requirements.txt
4. Configure Environment Variables
Create a .env file in the root directory and add your configurations:

env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
5. Run Database Migrations
bash
python manage.py makemigrations
python manage.py migrate
6. Create a Superuser (For Admin Access)
bash
python manage.py createsuperuser
7. Run the Development Server
bash
python manage.py runserver
Open your browser and navigate to http://127.0.0.1:8000/ to view the application.

📂 Project Structure
text
django-ecommerce-app/
│
├── core/                # Main project settings and URL configurations
├── main_app/            # Product catalog, variants, and category management
├── templates/           # HTML frontend templates
├── static/              # CSS, JavaScript, and image assets
├── media/               # User-uploaded product images
├── manage.py            # Django project management script
└── requirements.txt     # Python package dependencies
🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.
