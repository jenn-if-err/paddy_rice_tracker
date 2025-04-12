from flask import Blueprint, redirect, url_for, flash, render_template, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User, Farmer, Municipality, Barangay, User
import os

auth = Blueprint('auth', __name__)

# 🔐 Google OAuth for Barangay & Municipal
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["profile", "email"],
    redirect_to="auth.google_login"
)

# ✅ Google Login (Barangay & Municipal)
@auth.route("/login/google")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return redirect(url_for("auth.login"))

    user_info = resp.json()
    email = user_info.get("email")
    name = user_info.get("name", "User")

    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for("auth.login"))

    login_user(user)
    return redirect(url_for("views.dashboard"))

# ✅ Main Login Page
@auth.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        # Check if input is a farmer username (no @ symbol)
        if '@' not in email:
            farmer = Farmer.query.filter_by(username=email).first()
            if farmer and check_password_hash(farmer.password, password):
                login_user(farmer)
                return redirect(url_for("views.dashboard"))
            else:
                flash("Invalid username or password.", "error")
                return redirect(url_for("auth.login"))
        else:
            # Regular user (email format)
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for("views.dashboard"))
            else:
                flash("Invalid email or password.", "error")
                return redirect(url_for("auth.login"))

    return render_template("login.html")

# ✅ Barangay Sign-Up
@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    from .models import Municipality, Barangay, User
    from .extensions import db
    from werkzeug.security import generate_password_hash

    # ✅ Insert demo municipality if DB is empty (for testing)
    if Municipality.query.count() == 0:
        demo = Municipality(name='Demo Town')
        db.session.add(demo)
        db.session.commit()
        print("✅ Inserted demo municipality")

    municipalities = Municipality.query.all()
    print("📦 Municipalities available for dropdown:", municipalities)

    if request.method == 'POST':
        print("📥 POST received to /barangay-signup-test")
        print("Form data:", request.form)

        email = request.form.get('email')
        municipality_name = request.form.get('municipality', '').strip().title()
        barangay_name = request.form.get('barangay_name', '').strip().title()
        password = request.form.get('password1')

        try:
            # Get or create the municipality
            municipality = Municipality.query.filter_by(name=municipality_name).first()
            if not municipality:
                municipality = Municipality(name=municipality_name)
                db.session.add(municipality)
                db.session.commit()
                print(f"✅ Created municipality: {municipality.name}")
            else:
                print(f"ℹ️ Municipality already exists: {municipality.name}")

            # Get or create the barangay
            barangay = Barangay.query.filter_by(name=barangay_name, municipality_id=municipality.id).first()
            if not barangay:
                barangay = Barangay(name=barangay_name, municipality_id=municipality.id)
                db.session.add(barangay)
                db.session.commit()
                print(f"✅ Created barangay: {barangay.name}")
            else:
                print(f"ℹ️ Barangay already exists: {barangay.name}")

            # Create the barangay user
            new_user = User(
                email=email,
                role='barangay',
                barangay_id=barangay.id,
                full_name="Barangay Officer",
                password=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()
            print("✅ Barangay user created")

            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            print(f"❌ Error during barangay signup: {e}")
            return "Internal Server Error", 500

    return render_template('sign_up.html', municipalities=municipalities)


# ✅ Municipal Sign-Up
@auth.route('/sign-up-municipal', methods=['GET', 'POST'])
def signup_municipal():
    if request.method == 'POST':
        print("📥 POST received to /municipal-signup")
        print(f"Form data: {request.form}")

        email = request.form.get('email')
        municipality_name = request.form.get('municipality', '').strip().title()
        password = request.form.get('password1')
        full_name = "Municipal Officer"

        if not municipality_name:
            print("❌ No municipality provided.")
            return "Please provide a municipality name", 400

        try:
            municipality = Municipality.query.filter_by(name=municipality_name).first()
            if not municipality:
                municipality = Municipality(name=municipality_name)
                db.session.add(municipality)
                db.session.commit()
                print(f"✅ Municipality created: {municipality.name}")
            else:
                print(f"ℹ️ Municipality already exists: {municipality.name}")

            # 🔧 Make sure to assign municipality_id here
            new_user = User(
                email=email,
                full_name=full_name,
                role='municipal',
                municipality_id=municipality.id,
                password=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()

            print("✅ Municipal user created.")
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            print(f"❌ Error during municipal signup: {e}")
            return "Internal server error", 500

    return render_template('sign_up_municipal.html')


# ✅ Logout
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/choose-role')
def choose_role():
    return render_template('role_selection.html')
