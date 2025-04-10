from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from .models import DryingRecord, Farmer
from .extensions import db
from werkzeug.security import generate_password_hash
from datetime import datetime


views = Blueprint('views', __name__)

# ==============================
# 🔍 Dashboard Route (Role-based)
# ==============================
@views.route('/')
@login_required
def dashboard():
    if hasattr(current_user, 'role'):
        # ✅ Google OAuth Users (Barangay or Municipal)
        if current_user.role == 'municipal':
            records = DryingRecord.query.order_by(DryingRecord.timestamp.desc()).all()
        elif current_user.role == 'barangay':
            records = DryingRecord.query \
                .filter_by(barangay_name=current_user.barangay_name) \
                .order_by(DryingRecord.timestamp.desc()).all()
        else:
            return "Invalid user role", 403
    else:
        # ✅ Farmer Login (Only sees own data)
        records = DryingRecord.query \
            .filter_by(farmer_id=current_user.id) \
            .order_by(DryingRecord.timestamp.desc()).all()

    return render_template("records.html", user=current_user, records=records)


# ============================
# 🔄 API Sync (POST from Local)
# ============================
@views.route('/api/sync', methods=['POST'])
@login_required
def api_sync():
    try:
        data = request.get_json()

        if not data or 'records' not in data:
            return jsonify({"status": "error", "message": "Invalid payload"}), 400

        for record in data['records']:
            new_record = DryingRecord(
                batch_name=record.get('batch_name'),
                initial_weight=record.get('initial_weight'),
                temperature=record.get('temperature'),
                humidity=record.get('humidity'),
                sensor_value=record.get('sensor_value'),
                initial_moisture=record.get('initial_moisture'),
                final_moisture=record.get('final_moisture'),
                drying_time=record.get('drying_time'),
                final_weight=record.get('final_weight'),
                shelf_life=record.get('shelf_life'),
                date_planted=record.get('date_planted'),
                date_harvested=record.get('date_harvested'),
                date_dried=record.get('date_dried'),
                farmer_name=record.get('farmer_name'),
                farmer_id=record.get('farmer_id'),
                user_id=current_user.id,
                barangay_name=current_user.barangay_name  
            )
            db.session.add(new_record)

        db.session.commit()
        return jsonify({"status": "success", "message": "Records synced."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@views.route("/farmers", methods=["GET"])
@login_required
def farmers():
    # Only barangay users should access this
    if not hasattr(current_user, "role") or current_user.role != "barangay":
        flash("Unauthorized access.", "error")
        return redirect(url_for("views.dashboard"))

    farmer_list = Farmer.query.filter_by(barangay_name=current_user.barangay_name).all()
    print(f"Farmers fetched: {[f'{farmer.first_name} {farmer.last_name}' for farmer in farmer_list]}")  # Debugging line
    return render_template("farmers.html", farmers=farmer_list, user=current_user)


@views.route("/add-farmer", methods=["POST"])
@login_required
def add_farmer():
    if not hasattr(current_user, "role") or current_user.role != "barangay":
        flash("Unauthorized access.", "error")
        return redirect(url_for("views.dashboard"))

    first_name = request.form.get("first_name")
    middle_name = request.form.get("middle_name")
    last_name = request.form.get("last_name")

    username = request.form.get("username")
    password = request.form.get("password")

    if Farmer.query.filter_by(username=username).first():
        flash("Username already exists.", "error")
        return redirect(url_for("views.farmers"))

    new_farmer = Farmer(
        username=username,
        password=generate_password_hash(password),
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        barangay_name=current_user.barangay_name,
        user_id=current_user.id
    )

    db.session.add(new_farmer)
    db.session.commit()
    flash("Farmer added successfully!", "success")
    return redirect(url_for("views.farmers"))


@views.route('/records')
@login_required
def records():
    if hasattr(current_user, 'role'):
        if current_user.role == 'barangay':
            records = DryingRecord.query \
                .filter_by(barangay_name=current_user.barangay_name) \
                .order_by(DryingRecord.timestamp.desc()).all()
        else:
            # Municipal users can see all records
            records = DryingRecord.query.order_by(DryingRecord.timestamp.desc()).all()
    else:
        records = DryingRecord.query.filter_by(farmer_id=current_user.id).order_by(DryingRecord.timestamp.desc()).all()

    return render_template('records.html', records=records, user=current_user)


@views.route('/add_record', methods=['GET', 'POST'])
@login_required
def add_record():
    if current_user.role not in ['barangay', 'farmer']:
        flash("You are not authorized to add records.", "error")
        return redirect(url_for('views.dashboard'))

    # Fetch the farmers for the current barangay if logged in as barangay
    if current_user.role == 'barangay':
        farmers = Farmer.query.filter_by(barangay_name=current_user.barangay_name).all()
    else:
        farmers = Farmer.query.all()  # For farmers, display all of them

    print(f"Farmers available: {[f'{farmer.first_name} {farmer.last_name}' for farmer in farmers]}")  # Debugging line

    if request.method == 'POST':
        batch_name = request.form['batch_name']
        initial_weight = request.form['initial_weight']
        final_weight = request.form['final_weight']
        farmer_id = request.form['farmer_id']  # Get selected farmer's ID
        barangay_name = current_user.barangay_name  # Automatically populated from logged-in user

        temperature = request.form.get('temperature', 0)
        humidity = request.form.get('humidity', 0)
        sensor_value = request.form.get('sensor_value', 0)
        initial_moisture = request.form.get('initial_moisture', 0)
        final_moisture = request.form.get('final_moisture', 0)
        drying_time = request.form.get('drying_time', '0')

        # Fetch farmer name using farmer_id
        farmer = Farmer.query.get(farmer_id)
        farmer_name = f"{farmer.first_name} {farmer.last_name}" if farmer else "Unknown"

        # Convert date strings to date objects
        due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else None
        date_planted = datetime.strptime(request.form.get('date_planted'), '%Y-%m-%d').date() if request.form.get('date_planted') else None
        date_harvested = datetime.strptime(request.form.get('date_harvested'), '%Y-%m-%d').date() if request.form.get('date_harvested') else None
        date_dried = datetime.strptime(request.form.get('date_dried'), '%Y-%m-%d').date() if request.form.get('date_dried') else None

        # Create a new DryingRecord
        new_record = DryingRecord(
            batch_name=batch_name,
            initial_weight=initial_weight,
            final_weight=final_weight,
            temperature=temperature,
            humidity=humidity,
            sensor_value=sensor_value,
            initial_moisture=initial_moisture,
            final_moisture=final_moisture,
            drying_time=drying_time,
            farmer_id=farmer_id,  # Link the record to the selected farmer
            farmer_name=farmer_name,  # Store farmer name
            barangay_name=barangay_name,
            user_id=current_user.id,  # Link the record to the logged-in user
            due_date=due_date,
            date_planted=date_planted,
            date_harvested=date_harvested,
            date_dried=date_dried
        )

        db.session.add(new_record)
        db.session.commit()

        flash("Record added successfully!", "success")
        return redirect(url_for('views.dashboard'))  # Redirect to dashboard after adding the record

    return render_template('add_record.html', farmers=farmers)  # Pass farmers to the template

@views.route('/select_farmer', methods=['GET'])
@login_required
def select_farmer():
    if current_user.role != 'barangay':
        flash("Unauthorized access.", "error")
        return redirect(url_for("views.dashboard"))

    farmers = Farmer.query.filter_by(barangay_name=current_user.barangay_name).all()
    return render_template('select_farmer.html', farmers=farmers)

@views.route('/barangay_dashboard')
@login_required
def barangay_dashboard():
    # Get view parameters
    view_type = request.args.get('view', 'total')
    time_period = request.args.get('period', 'month')
    
    if current_user.role == 'municipal':
        records = DryingRecord.query.all()
        
        if view_type == 'total':
            # Group data by barangay (total view)
            barangay_data = {}
            for record in records:
                barangay = record.barangay_name
                if not barangay:
                    continue
                    
                if barangay not in barangay_data:
                    barangay_data[barangay] = {'initial_weight': 0, 'final_weight': 0}
                barangay_data[barangay]['initial_weight'] += float(record.initial_weight)
                barangay_data[barangay]['final_weight'] += float(record.final_weight)
                
            return render_template('dashboard.html', 
                                   monthly_data=barangay_data, 
                                   user=current_user, 
                                   is_municipal=True,
                                   view_type=view_type,
                                   time_period=time_period)
        else:
            # Group data by barangay and time period
            time_data = {}
            for record in records:
                if not record.date_dried or not record.barangay_name:
                    continue
                
                # Get time key based on selected period (month or year)
                if time_period == 'month':
                    time_key = record.date_dried.strftime('%b %Y')
                else:
                    time_key = record.date_dried.strftime('%Y')
                
                barangay = record.barangay_name
                
                # Initialize nested structure if needed
                if time_key not in time_data:
                    time_data[time_key] = {}
                if barangay not in time_data[time_key]:
                    time_data[time_key][barangay] = {'initial_weight': 0, 'final_weight': 0}
                
                # Add weights
                time_data[time_key][barangay]['initial_weight'] += float(record.initial_weight)
                time_data[time_key][barangay]['final_weight'] += float(record.final_weight)
            
            # Sort by time periods
            sorted_time_data = dict(sorted(time_data.items()))
            
            return render_template('dashboard.html', 
                                   time_data=sorted_time_data,
                                   user=current_user, 
                                   is_municipal=True,
                                   view_type=view_type,
                                   time_period=time_period)
        
    elif current_user.role == 'barangay':
        records = DryingRecord.query.filter_by(barangay_name=current_user.barangay_name).all()
        
        # Group data by month
        monthly_data = {}
        for record in records:
            if record.date_dried:
                month = record.date_dried.strftime('%B')
                if month not in monthly_data:
                    monthly_data[month] = {'initial_weight': 0, 'final_weight': 0}
                monthly_data[month]['initial_weight'] += float(record.initial_weight)
                monthly_data[month]['final_weight'] += float(record.final_weight)

        return render_template('dashboard.html', monthly_data=monthly_data, user=current_user, is_municipal=False)
    else:
        # Handle other roles
        flash("Unauthorized access", "error")
        return redirect(url_for('views.dashboard'))

@views.route('/edit_record/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_record(record_id):
    record = DryingRecord.query.get_or_404(record_id)
    if request.method == 'POST':
        record.batch_name = request.form['batch_name']
        record.initial_weight = request.form['initial_weight']
        record.final_weight = request.form['final_weight']
        record.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else None
        record.date_planted = datetime.strptime(request.form.get('date_planted'), '%Y-%m-%d').date() if request.form.get('date_planted') else None
        record.date_harvested = datetime.strptime(request.form.get('date_harvested'), '%Y-%m-%d').date() if request.form.get('date_harvested') else None
        record.date_dried = datetime.strptime(request.form.get('date_dried'), '%Y-%m-%d').date() if request.form.get('date_dried') else None
        db.session.commit()
        flash('Record updated successfully!', 'success')
        return redirect(url_for('views.records'))
    return render_template('edit_record.html', record=record)

@views.route('/delete_record/<int:record_id>', methods=['POST'])
@login_required
def delete_record(record_id):
    record = DryingRecord.query.get_or_404(record_id)
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted successfully!', 'success')
    return redirect(url_for('views.records'))

@views.route('/analytics')
@login_required
def analytics():
    if current_user.role == 'municipal':
        # Get parameter for view type (year or month)
        view_type = request.args.get('view', 'year')
        
        records = DryingRecord.query.all()
        
        analytics_data = {}
        
        if view_type == 'year':
            # Group data by year
            for record in records:
                if record.date_dried:
                    year = record.date_dried.strftime('%Y')
                    if year not in analytics_data:
                        analytics_data[year] = 0
                    analytics_data[year] += float(record.final_weight)
        else:
            # Group data by month
            for record in records:
                if record.date_dried:
                    month_year = record.date_dried.strftime('%b %Y')
                    if month_year not in analytics_data:
                        analytics_data[month_year] = 0
                    analytics_data[month_year] += float(record.final_weight)
        
        # Sort data by key
        sorted_data = dict(sorted(analytics_data.items()))
        
        return render_template('analytics.html', 
                               analytics_data=sorted_data, 
                               view_type=view_type,
                               user=current_user)
    else:
        flash("Unauthorized access", "error")
        return redirect(url_for('views.dashboard'))
