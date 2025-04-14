from flask import Blueprint, render_template, redirect, url_for, request, jsonify, session
from flask_login import login_required, current_user
from .models import DryingRecord, Farmer, Municipality, Barangay, User
from .extensions import db
from werkzeug.security import generate_password_hash
from datetime import datetime


views = Blueprint('views', __name__)

@views.route('/')
@login_required
def dashboard():
    if current_user.role == 'municipal':
        municipality = current_user.municipality
        if not municipality:
            print("Municipality not set for user")
            return redirect(url_for('auth.login'))

        barangays = Barangay.query.filter_by(municipality_id=municipality.id).all()
        barangay_data = {}
        for barangay in barangays:
            barangay_data[barangay.name] = {
                'initial_weight': sum(record.initial_weight for record in barangay.drying_records),
                'final_weight': sum(record.final_weight for record in barangay.drying_records)
            }

        return render_template('dashboard.html', 
                               monthly_data=barangay_data, 
                               user=current_user, 
                               is_municipal=True,
                               view_type='barangay_bar')  
    elif current_user.role == 'barangay':
        return redirect(url_for('views.barangay_dashboard'))
    elif current_user.role == 'farmer':
        records = DryingRecord.query.filter_by(farmer_id=current_user.id).all()
        batch_data = {}
        for record in records:
            batch = record.batch_name or "(Unnamed Batch)"
            if batch not in batch_data:
                batch_data[batch] = {'initial_weight': 0, 'final_weight': 0}
            try:
                batch_data[batch]['initial_weight'] += float(record.initial_weight)
                batch_data[batch]['final_weight'] += float(record.final_weight)
            except (ValueError, TypeError):
                pass

        return render_template('dashboard.html', 
                               monthly_data=batch_data, 
                               user=current_user, 
                               is_municipal=False,
                               view_type='batch_bar')
    else:
        return redirect(url_for('auth.login'))



@views.route("/farmers", methods=["GET"])
@login_required
def farmers():
    if not hasattr(current_user, "role") or current_user.role != "barangay":
        return redirect(url_for("views.dashboard"))

    farmer_list = Farmer.query.filter_by(barangay_id=current_user.barangay_id).all()
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
        barangay_id=current_user.barangay_id,
        user_id=current_user.id
    )

    db.session.add(new_farmer)
    db.session.commit()
    return redirect(url_for("views.farmers"))


@views.route('/records')
@login_required
def records():
    if current_user.role == 'municipal':
        # Municipal users see records for their municipality only
        records = DryingRecord.query.join(Barangay).filter(Barangay.municipality_id == current_user.municipality_id).order_by(DryingRecord.timestamp.desc()).all()
    elif current_user.role == 'barangay':
        # Barangay users see records for their barangay only
        records = DryingRecord.query \
            .filter_by(barangay_id=current_user.barangay_id) \
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
    if current_user.role == 'municipal':
        return redirect(url_for('views.records'))

    if current_user.role not in ['barangay', 'farmer']:
        return redirect(url_for('auth.login'))

    farmers = None

    if current_user.role == 'barangay':
        farmers = Farmer.query.filter_by(barangay_id=current_user.barangay_id).all()

    if request.method == 'POST':
        record_farmer_id_str = request.form.get('farmer_id')

        if current_user.role == 'farmer':
            if not record_farmer_id_str or record_farmer_id_str != str(current_user.id):
                return redirect(url_for('views.records'))
            record_farmer_id = current_user.id
            target_farmer = current_user
        elif current_user.role == 'barangay':
            if not record_farmer_id_str:
                farmers = Farmer.query.filter_by(barangay_id=current_user.barangay_id).all()
                return render_template('add_record.html', farmers=farmers, user=current_user)

            try:
                record_farmer_id = int(record_farmer_id_str)
                target_farmer = Farmer.query.get(record_farmer_id)
                if not target_farmer or target_farmer.barangay_id != current_user.barangay_id:
                    farmers = Farmer.query.filter_by(barangay_id=current_user.barangay_id).all()
                    return render_template('add_record.html', farmers=farmers, user=current_user)
            except (ValueError, TypeError):
                farmers = Farmer.query.filter_by(barangay_id=current_user.barangay_id).all()
                return render_template('add_record.html', farmers=farmers, user=current_user)

        if current_user.role == 'farmer':
            staff_user = User.query.filter_by(barangay_id=current_user.barangay_id).first()
            user_id = staff_user.id if staff_user else None
        else:
            user_id = current_user.id

        record_farmer_name = target_farmer.full_name
        record_barangay_id = current_user.barangay_id
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
            batch_name=batch_name,
            initial_weight=initial_weight,
            final_weight=final_weight,
            temperature=temperature,
            humidity=humidity,
            sensor_value=sensor_value,
            initial_moisture=initial_moisture,
            final_moisture=final_moisture,
            drying_time=drying_time,
            farmer_id=record_farmer_id,
            farmer_name=record_farmer_name,
            barangay_id=record_barangay_id,
            user_id=user_id,  
            due_date=due_date,
            date_planted=date_planted,
            date_harvested=date_harvested,
            date_dried=date_dried
        )
        db.session.add(new_record)
        db.session.commit()
        return redirect(url_for('views.records'))

    return render_template('add_record.html', farmers=farmers, user=current_user)


@views.route('/barangay_dashboard')
@login_required
def barangay_dashboard():
    if current_user.role == 'municipal':
        records = DryingRecord.query.all()
        barangay_data = {}
        for record in records:
            barangay = record.barangay_id
            if not barangay:
                continue 
            if barangay not in barangay_data:
                barangay_data[barangay] = {'initial_weight': 0, 'final_weight': 0}
            
            try:
                barangay_data[barangay]['initial_weight'] += float(record.initial_weight)
                barangay_data[barangay]['final_weight'] += float(record.final_weight)
            except (ValueError, TypeError):
                pass 

        return render_template('dashboard.html', 
                               monthly_data=barangay_data, 
                               user=current_user, 
                               is_municipal=True,
                               view_type='total') 

    elif current_user.role == 'barangay':
        records = DryingRecord.query.filter_by(barangay_id=current_user.barangay_id).all()
        farmer_data = {}

        for record in records:
            if not record.farmer_name:
                continue
            farmer_name = record.farmer_name

            if farmer_name not in farmer_data:
                farmer_data[farmer_name] = {'initial_weight': 0, 'final_weight': 0}
            
            try:
                farmer_data[farmer_name]['initial_weight'] += float(record.initial_weight)
                farmer_data[farmer_name]['final_weight'] += float(record.final_weight)
            except (ValueError, TypeError):
                pass

        return render_template('dashboard.html', 
                               monthly_data=farmer_data, 
                               user=current_user, 
                               is_municipal=False,
                               view_type='farmer_bar')  

    else:
        return redirect(url_for('views.records'))


@views.route('/barangay_analytics')
@login_required
def barangay_analytics():
    if current_user.role != 'barangay':
        return redirect(url_for('views.dashboard'))

    time_period = request.args.get('period', 'month')  # Default to month
    records = DryingRecord.query.filter_by(barangay_id=current_user.barangay_id).all()

    analytics_data = {}

    # Step 1: Populate analytics_data
    for record in records:
        if record.date_dried:
            if time_period == 'month':
                key = record.date_dried.strftime('%b %Y')
            else:
                key = record.date_dried.strftime('%Y')

            if key not in analytics_data:
                analytics_data[key] = 0
            try:
                analytics_data[key] += float(record.final_weight)
            except (ValueError, TypeError):
                pass

    # Step 2: Sort analytics_data keys chronologically
    try:
        if time_period == 'month':
            sorted_keys = sorted(analytics_data.keys(), key=lambda d: datetime.strptime(d, '%b %Y'))
        else:
            sorted_keys = sorted(analytics_data.keys(), key=int)
        sorted_data = {key: analytics_data[key] for key in sorted_keys}
    except ValueError:
        sorted_data = analytics_data  # Fallback

    # Step 3: Render chart
    return render_template('barangay_analytics.html',
                           analytics_data=sorted_data,
                           time_period=time_period,
                           user=current_user)


@views.route('/farmer_analytics')
@login_required
def farmer_analytics():
    # Redirect non-farmers
    if current_user.role != 'farmer':
        if hasattr(current_user, 'role') and current_user.role in ['municipal', 'barangay']:
            return redirect(url_for('views.barangay_dashboard'))
        else:
            return redirect(url_for('auth.login'))

    time_period = request.args.get('period', 'month')  # Default to 'month'
    records = DryingRecord.query.filter_by(farmer_id=current_user.id).all()

    analytics_data = {}

    # Step 1: Populate analytics_data
    for record in records:
        if record.date_dried:
            if time_period == 'month':
                key = record.date_dried.strftime('%b %Y')
            else:
                key = record.date_dried.strftime('%Y')

            if key not in analytics_data:
                analytics_data[key] = 0
            try:
                analytics_data[key] += float(record.final_weight)
            except (ValueError, TypeError):
                pass

    # Step 2: Sort chronologically
    try:
        if time_period == 'month':
            sorted_keys = sorted(analytics_data.keys(), key=lambda d: datetime.strptime(d, '%b %Y'))
        else:
            sorted_keys = sorted(analytics_data.keys(), key=int)
        sorted_data = {key: analytics_data[key] for key in sorted_keys}
    except ValueError:
        sorted_data = analytics_data  # Fallback

    # Step 3: Render
    return render_template('farmer_analytics.html',
                           analytics_data=sorted_data,
                           time_period=time_period,
                           user=current_user)


@login_required
@views.route('/edit_record/<int:record_id>', methods=['GET', 'POST'])
def edit_record(record_id):
    if current_user.role == 'municipal':
        return redirect(url_for('views.records'))
    
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
        view_type = request.args.get('view', 'year')

        # ✅ Filter only records from the municipal user's assigned municipality
        records = DryingRecord.query.join(Barangay).filter(
            Barangay.municipality_id == current_user.municipality_id
        ).all()

        analytics_data = {}

        # Step 1: Populate analytics_data
        for record in records:
            if record.date_dried:
                if view_type == 'month':
                    key = record.date_dried.strftime('%b %Y')
                else:
                    key = record.date_dried.strftime('%Y')

                if key not in analytics_data:
                    analytics_data[key] = 0
                try:
                    analytics_data[key] += float(record.final_weight)
                except (ValueError, TypeError):
                    pass

        # Step 2: Sort keys correctly
        try:
            if view_type == 'month':
                sorted_keys = sorted(analytics_data.keys(), key=lambda d: datetime.strptime(d, '%b %Y'))
            else:
                sorted_keys = sorted(analytics_data.keys(), key=int)
            sorted_data = {key: analytics_data[key] for key in sorted_keys}
        except Exception:
            sorted_data = analytics_data  # fallback

        return render_template('analytics.html', 
                               analytics_data=sorted_data, 
                               view_type=view_type,
                               user=current_user)


@views.route('/municipality_dashboard/<int:municipality_id>')
@login_required
def municipality_dashboard(municipality_id):
    if current_user.role != 'municipal' or current_user.municipality_id != municipality_id:
        return redirect(url_for('views.dashboard'))  # or 403 error

    municipality = Municipality.query.get_or_404(municipality_id)
    barangays = Barangay.query.filter_by(municipality_id=municipality.id).all()
    return render_template('dashboard.html', municipality=municipality, barangays=barangays)


@views.route('/municipality_analytics/<int:municipality_id>')
@login_required
def municipality_analytics(municipality_id):
    if current_user.role != 'municipal' or current_user.municipality_id != municipality_id:
        return redirect(url_for('views.dashboard'))  # or return 403

    municipality = Municipality.query.get_or_404(municipality_id)
    drying_records = DryingRecord.query.join(Barangay).filter(Barangay.municipality_id == municipality.id).all()
    return render_template('analytics.html', records=drying_records)


@views.route('/another_dashboard')
@login_required
def another_dashboard():
    # Logic for the other dashboard
    pass



