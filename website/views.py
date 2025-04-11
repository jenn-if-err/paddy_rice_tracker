from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from .models import DryingRecord, Farmer, Municipality, Barangay, User
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
    # Check role directly
    if current_user.role == 'municipal':
        # Redirect municipal users to their specific dashboard view
        return redirect(url_for('views.barangay_dashboard')) 
    elif current_user.role == 'barangay':
        # Redirect barangay users to their specific dashboard view
        return redirect(url_for('views.barangay_dashboard'))
    elif current_user.role == 'farmer':
        # === Farmer Dashboard Logic (Aggregated by Batch Name) ===
        records = DryingRecord.query.filter_by(farmer_id=current_user.id).all()
        batch_data = {}
        for record in records:
            batch = record.batch_name
            if not batch: # Should ideally not happen if batch_name is required
                batch = "(Unnamed Batch)"
                
            if batch not in batch_data:
                batch_data[batch] = {'initial_weight': 0, 'final_weight': 0}
            # Ensure weights are treated as floats
            try:
                batch_data[batch]['initial_weight'] += float(record.initial_weight)
                batch_data[batch]['final_weight'] += float(record.final_weight)
            except (ValueError, TypeError):
                pass # Or log an error

        return render_template('dashboard.html', 
                               monthly_data=batch_data, # Pass as monthly_data for template
                               user=current_user, 
                               is_municipal=False,
                               view_type='batch_bar') # New view_type for farmer dashboard
    else:
        # Should not happen
        return redirect(url_for('auth.login'))


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
    if not hasattr(current_user, "role") or current_user.role != "barangay":
        return redirect(url_for("views.dashboard"))

    farmer_list = Farmer.query.filter_by(barangay_name=current_user.barangay_name).all()
    return render_template("farmers.html", farmers=farmer_list, user=current_user)


@views.route("/add-farmer", methods=["POST"])
@login_required
def add_farmer():
    if not hasattr(current_user, "role") or current_user.role != "barangay":
        return redirect(url_for("views.dashboard"))

    first_name = request.form.get("first_name")
    middle_name = request.form.get("middle_name")
    last_name = request.form.get("last_name")
    username = request.form.get("username")
    password = request.form.get("password")

    if Farmer.query.filter_by(username=username).first():
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
    return redirect(url_for("views.farmers"))


@views.route('/records')
@login_required
def records():
    # Check role directly
    if current_user.role == 'municipal':
        # Municipal users see all records
        records = DryingRecord.query.order_by(DryingRecord.timestamp.desc()).all()
    elif current_user.role == 'barangay':
        # Barangay users see records for their barangay
        records = DryingRecord.query \
            .filter_by(barangay_name=current_user.barangay_name) \
            .order_by(DryingRecord.timestamp.desc()).all()
    elif current_user.role == 'farmer':
        # Farmers see only their own records
        records = DryingRecord.query \
            .filter_by(farmer_id=current_user.id) \
            .order_by(DryingRecord.timestamp.desc()).all()
    else:
        # Unknown role
        records = []

    return render_template('records.html', records=records, user=current_user)


@views.route('/add_record', methods=['GET', 'POST'])
@login_required
def add_record():
    if current_user.role not in ['barangay', 'farmer']:
        if hasattr(current_user, 'role'):
            return redirect(url_for('views.barangay_dashboard'))
        else:
            return redirect(url_for('auth.login'))

    farmers = None
    
    if current_user.role == 'barangay':
        farmers = Farmer.query.filter_by(barangay_name=current_user.barangay_name).all()

    if request.method == 'POST':
        record_farmer_id_str = request.form.get('farmer_id')

        if current_user.role == 'farmer':
            if not record_farmer_id_str or record_farmer_id_str != str(current_user.id):
                return redirect(url_for('views.records'))
            record_farmer_id = current_user.id
            target_farmer = current_user
        elif current_user.role == 'barangay':
            if not record_farmer_id_str:
                farmers = Farmer.query.filter_by(barangay_name=current_user.barangay_name).all()
                return render_template('add_record.html', farmers=farmers, user=current_user)
            
            try:
                record_farmer_id = int(record_farmer_id_str)
                target_farmer = Farmer.query.get(record_farmer_id)
                if not target_farmer or target_farmer.barangay_name != current_user.barangay_name:
                    farmers = Farmer.query.filter_by(barangay_name=current_user.barangay_name).all()
                    return render_template('add_record.html', farmers=farmers, user=current_user)
            except (ValueError, TypeError):
                farmers = Farmer.query.filter_by(barangay_name=current_user.barangay_name).all()
                return render_template('add_record.html', farmers=farmers, user=current_user)

        record_farmer_name = target_farmer.full_name
        record_barangay_name = target_farmer.barangay_name
        batch_name = request.form['batch_name']
        initial_weight = request.form['initial_weight']
        final_weight = request.form['final_weight']
        temperature = request.form.get('temperature', 0)
        humidity = request.form.get('humidity', 0)
        sensor_value = request.form.get('sensor_value', 0)
        initial_moisture = request.form.get('initial_moisture', 0)
        final_moisture = request.form.get('final_moisture', 0)
        drying_time = request.form.get('drying_time', '0')
        due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else None
        date_planted = datetime.strptime(request.form.get('date_planted'), '%Y-%m-%d').date() if request.form.get('date_planted') else None
        date_harvested = datetime.strptime(request.form.get('date_harvested'), '%Y-%m-%d').date() if request.form.get('date_harvested') else None
        date_dried = datetime.strptime(request.form.get('date_dried'), '%Y-%m-%d').date() if request.form.get('date_dried') else None

        new_record = DryingRecord(
            batch_name=batch_name, initial_weight=initial_weight, final_weight=final_weight,
            temperature=temperature, humidity=humidity, sensor_value=sensor_value,
            initial_moisture=initial_moisture, final_moisture=final_moisture, drying_time=drying_time,
            farmer_id=record_farmer_id, farmer_name=record_farmer_name, barangay_name=record_barangay_name,
            user_id=current_user.id, 
            due_date=due_date, date_planted=date_planted, date_harvested=date_harvested, date_dried=date_dried
        )
        db.session.add(new_record)
        db.session.commit()
        return redirect(url_for('views.records'))

    return render_template('add_record.html',
                           farmers=farmers,
                           user=current_user)

@views.route('/barangay_dashboard')
@login_required
def barangay_dashboard():
    if current_user.role == 'municipal':
        # === Municipal View Logic (Always Total Aggregated View) ===
        records = DryingRecord.query.all()
        barangay_data = {}
        for record in records:
            barangay = record.barangay_name
            if not barangay:
                continue # Skip records without a barangay name
            if barangay not in barangay_data:
                barangay_data[barangay] = {'initial_weight': 0, 'final_weight': 0}
            # Ensure weights are treated as floats
            try:
                barangay_data[barangay]['initial_weight'] += float(record.initial_weight)
                barangay_data[barangay]['final_weight'] += float(record.final_weight)
            except (ValueError, TypeError):
                pass # Or log an error
                
        return render_template('dashboard.html', 
                               monthly_data=barangay_data, # Pass as monthly_data
                               user=current_user, 
                               is_municipal=True,
                               view_type='total') # Indicate it's the total view
        
    elif current_user.role == 'barangay':
        # === Barangay View Logic (Original Monthly Bar Chart) ===
        records = DryingRecord.query.filter_by(barangay_name=current_user.barangay_name).all()
        monthly_data = {}
        for record in records:
            if record.date_dried:
                month = record.date_dried.strftime('%B %Y') # Include year
                if month not in monthly_data:
                    monthly_data[month] = {'initial_weight': 0, 'final_weight': 0}
                try:
                    monthly_data[month]['initial_weight'] += float(record.initial_weight)
                    monthly_data[month]['final_weight'] += float(record.final_weight)
                except (ValueError, TypeError):
                    pass
        sorted_monthly_data = {}
        try: 
            sorted_keys = sorted(monthly_data.keys(), key=lambda d: datetime.strptime(d, '%B %Y'))
            for month_str in sorted_keys:
                sorted_monthly_data[month_str] = monthly_data[month_str]
        except ValueError:
            sorted_monthly_data = monthly_data
            
        return render_template('dashboard.html', 
                               monthly_data=sorted_monthly_data, 
                               user=current_user, 
                               is_municipal=False,
                               view_type='monthly_bar')
    else:
        # Handle other roles (e.g., Farmer)
        return redirect(url_for('views.records'))

# === NEW Barangay Analytics Route ===
@views.route('/barangay_analytics')
@login_required
def barangay_analytics():
    if current_user.role != 'barangay':
        return redirect(url_for('views.dashboard'))

    time_period = request.args.get('period', 'month') # Default to month
    records = DryingRecord.query.filter_by(barangay_name=current_user.barangay_name).all()
    
    analytics_data = {}
    if time_period == 'year':
        # Group data by year
        for record in records:
            if record.date_dried:
                year = record.date_dried.strftime('%Y')
                if year not in analytics_data:
                    analytics_data[year] = 0
                analytics_data[year] += float(record.final_weight)
    else: # time_period == 'month'
        # Group data by month
        for record in records:
            if record.date_dried:
                month_year = record.date_dried.strftime('%b %Y')
                if month_year not in analytics_data:
                    analytics_data[month_year] = 0
                analytics_data[month_year] += float(record.final_weight)
    
    # Sort data by time key
    sorted_data = {}
    try:
        if time_period == 'month':
            sorted_keys = sorted(analytics_data.keys(), key=lambda d: datetime.strptime(d, '%b %Y'))
        else:
            sorted_keys = sorted(analytics_data.keys(), key=int) # Sort years numerically
        for key in sorted_keys:
            sorted_data[key] = analytics_data[key]
    except ValueError:
         sorted_data = analytics_data # Fallback

    return render_template('barangay_analytics.html', 
                           analytics_data=sorted_data, 
                           time_period=time_period,
                           user=current_user)

# === Farmer Analytics Route ===
@views.route('/farmer_analytics')
@login_required
def farmer_analytics():
    if current_user.role != 'farmer':
        # Redirect non-farmers appropriately
        if hasattr(current_user, 'role') and current_user.role in ['municipal', 'barangay']:
             return redirect(url_for('views.barangay_dashboard'))
        else:
            return redirect(url_for('auth.login'))

    time_period = request.args.get('period', 'month') # Default to month
    # Query only records for the current farmer
    records = DryingRecord.query.filter_by(farmer_id=current_user.id).all()
    
    analytics_data = {}
    if time_period == 'year':
        # Group data by year
        for record in records:
            if record.date_dried:
                year = record.date_dried.strftime('%Y')
                if year not in analytics_data:
                    analytics_data[year] = 0
                # Use final_weight for yield
                try:
                     analytics_data[year] += float(record.final_weight)
                except (ValueError, TypeError): pass 
    else: # time_period == 'month'
        # Group data by month
        for record in records:
            if record.date_dried:
                month_year = record.date_dried.strftime('%b %Y')
                if month_year not in analytics_data:
                    analytics_data[month_year] = 0
                # Use final_weight for yield
                try:
                     analytics_data[month_year] += float(record.final_weight)
                except (ValueError, TypeError): pass
    
    # Sort data by time key
    sorted_data = {}
    try:
        if time_period == 'month':
            sorted_keys = sorted(analytics_data.keys(), key=lambda d: datetime.strptime(d, '%b %Y'))
        else:
            sorted_keys = sorted(analytics_data.keys(), key=int) # Sort years numerically
        for key in sorted_keys:
            sorted_data[key] = analytics_data[key]
    except ValueError:
         sorted_data = analytics_data # Fallback

    return render_template('farmer_analytics.html', 
                           analytics_data=sorted_data, 
                           time_period=time_period,
                           user=current_user)

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
        return redirect(url_for('views.records'))
    return render_template('edit_record.html', record=record)

@views.route('/delete_record/<int:record_id>', methods=['POST'])
@login_required
def delete_record(record_id):
    record = DryingRecord.query.get_or_404(record_id)
    db.session.delete(record)
    db.session.commit()
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
        return redirect(url_for('views.dashboard'))

@views.route('/municipality_dashboard/<int:municipality_id>')
@login_required
def municipality_dashboard(municipality_id):
    municipality = Municipality.query.get(municipality_id)
    barangays = Barangay.query.filter_by(municipality_id=municipality.id).all()
    return render_template('dashboard.html', municipality=municipality, barangays=barangays)

@views.route('/municipality_analytics/<int:municipality_id>')
@login_required
def municipality_analytics(municipality_id):
    municipality = Municipality.query.get(municipality_id)
    drying_records = DryingRecord.query.join(Barangay).filter(Barangay.municipality_id == municipality.id).all()
    return render_template('analytics.html', records=drying_records)



