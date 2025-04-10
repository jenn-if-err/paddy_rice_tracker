from flask import Blueprint, redirect, url_for, flash, render_template, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User, Farmer
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
        flash("Failed to fetch user info from Google.", "error")
        return redirect(url_for("auth.login"))

    user_info = resp.json()
    email = user_info.get("email")
    name = user_info.get("name", "User")

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Unauthorized email. You are not registered.", "error")
        return redirect(url_for("auth.login"))

    login_user(user)
    flash(f"Logged in as {user.role.title()}!", "success")
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
                flash("Logged in as Farmer!", "success")
                return redirect(url_for("views.dashboard"))
            else:
                flash("Invalid username or password.", "error")
        else:
            # Regular user (email format)
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                flash(f"Logged in as {user.role.title()}!", "success")
                return redirect(url_for("views.dashboard"))
            else:
                flash("Invalid email or password.", "error")

    return render_template("login.html")

# ✅ Barangay Sign-Up
@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get("email")
        barangay_name = request.form.get("barangay_name")
        municipality = request.form.get("municipality")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if password1 != password2:
            flash("Passwords do not match.", "error")
            return redirect(url_for('auth.sign_up'))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for('auth.sign_up'))

        hashed_pw = generate_password_hash(password1)
        new_user = User(
            email=email,
            full_name="Barangay Staff",
            role="barangay",
            barangay_name=barangay_name,
            password=hashed_pw
        )

        db.session.add(new_user)
        db.session.commit()
        flash("Barangay account created successfully!", "success")
        return redirect(url_for('auth.login'))

    return render_template("sign_up.html")

# ✅ Municipal Sign-Up
@auth.route('/sign-up/municipal', methods=['GET', 'POST'])
def sign_up_municipal():
    if request.method == 'POST':
        email = request.form.get("email")
        municipality = request.form.get("municipality")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if password1 != password2:
            flash("Passwords do not match.", "error")
            return redirect(url_for('auth.sign_up_municipal'))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for('auth.sign_up_municipal'))

        hashed_pw = generate_password_hash(password1)
        new_user = User(
            email=email,
            full_name="Municipal Officer",
            role="municipal",
            barangay_name=None,
            password=hashed_pw
        )

        db.session.add(new_user)
        db.session.commit()
        flash("Municipal account created successfully!", "success")
        return redirect(url_for('auth.login'))

    return render_template("sign_up_municipal.html")

# ✅ Logout
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
