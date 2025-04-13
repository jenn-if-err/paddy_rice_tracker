from flask import Blueprint, request, jsonify
from .models import DryingRecord, Farmer, User, Barangay, Municipality
from .extensions import db
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash
from flask_login import login_user
from datetime import datetime

api = Blueprint('api', __name__)
auth = Blueprint('auth', __name__)

from datetime import datetime

@api.route('/sync', methods=['POST'])
def sync():
    try:
        data = request.get_json()

        if not data or 'records' not in data:
            return jsonify({"status": "error", "message": "Invalid data format."}), 400

        for record in data['records']:
            # Validate required fields
            required_fields = [
                'uuid', 'batch_name', 'initial_weight', 'temperature', 'humidity',
                'sensor_value', 'initial_moisture', 'final_moisture',
                'drying_time', 'final_weight', 'farmer_uuid', 'user_id','date_dried'
            ]
            if not all(field in record for field in required_fields):
                return jsonify({"status": "error", "message": "Missing fields in record."}), 400

            # Check if the record already exists (by UUID)
            existing = DryingRecord.query.filter_by(uuid=record['uuid']).first()
            if existing:
                continue  # Skip duplicate

            # ✅ Look up farmer by farmer_uuid (not farmer_id)
            farmer = Farmer.query.filter_by(uuid=record.get('farmer_uuid')).first()
            if not farmer:
                print(f"⚠️ Skipping record {record['uuid']}: farmer_uuid {record.get('farmer_uuid')} not found.")
                continue

            # Parse optional dates
            def parse_date(d):
                return datetime.strptime(d, '%Y-%m-%d').date() if d else None

            # Parse updated_at if provided
            updated_at = None
            if 'updated_at' in record and record['updated_at']:
                try:
                    updated_at = datetime.fromisoformat(record['updated_at'])
                except ValueError:
                    print(f"⚠️ Invalid updated_at for record {record['uuid']} — skipping timestamp")

            # Create the new drying record
            new_record = DryingRecord(
                uuid=record['uuid'],
                batch_name=record['batch_name'],
                initial_weight=record['initial_weight'],
                temperature=record['temperature'],
                humidity=record['humidity'],
                sensor_value=record['sensor_value'],
                initial_moisture=record['initial_moisture'],
                final_moisture=record['final_moisture'],
                drying_time=record['drying_time'],
                final_weight=record['final_weight'],
                date_planted=parse_date(record['date_planted']),
                date_harvested=parse_date(record['date_harvested']),
                due_date=parse_date(record['due_date']),
                date_dried=parse_date(record['date_dried']),
                user_id=record['user_id'],
                updated_at=updated_at,

                farmer_id=farmer.id,
                farmer_name=record.get('farmer_name'),
                barangay_id=record.get('barangay_id'),
                municipality_id=record.get('municipality_id'),
            )
            db.session.add(new_record)

        db.session.commit()
        return jsonify({"status": "success", "message": "Records synced."}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/fetch', methods=['GET'])
def fetch():
    farmer_uuid = request.args.get('farmer_uuid')

    if not farmer_uuid:
        return jsonify({"status": "error", "message": "Missing farmer_uuid"}), 400

    farmer = Farmer.query.filter_by(uuid=farmer_uuid).first()
    if not farmer:
        return jsonify({"status": "error", "message": "Farmer not found"}), 404

    records = DryingRecord.query.filter_by(farmer_id=farmer.id).all()

    data = []
    for record in records:
        data.append({
            "uuid": record.uuid,
            "batch_name": record.batch_name,
            "initial_weight": record.initial_weight,
            "temperature": record.temperature,
            "humidity": record.humidity,
            "sensor_value": record.sensor_value,
            "initial_moisture": record.initial_moisture,
            "final_moisture": record.final_moisture,
            "drying_time": record.drying_time,
            "final_weight": record.final_weight,
            "date_planted": record.date_planted.isoformat() if record.date_planted else None,
            "date_harvested": record.date_harvested.isoformat() if record.date_harvested else None,
            "due_date": record.due_date.isoformat() if record.due_date else None,
            "date_dried": record.date_dried.isoformat() if record.date_dried else None,
            "farmer_id": record.farmer_id,
            "farmer_uuid": record.farmer.uuid if record.farmer else None,
            "user_id": record.user_id,
            "barangay_id": record.barangay_id,
            "municipality_id": record.municipality_id,
            "farmer_name": record.farmer.full_name if record.farmer else None,
            "barangay_name": record.barangay.name if record.barangay else None,
            "municipality_name": record.municipality.name if record.municipality else None
        })

    return jsonify(data), 200



@api.route('/farmers/<username>', methods=['GET'])
def get_farmer(username):
    print(f"Attempting to fetch farmer with username: {username}")
    farmer = Farmer.query.filter_by(username=username).first()

    if farmer:
        farmer_data = {
            "uuid": farmer.uuid,
            "username": farmer.username,
            "first_name": farmer.first_name,
            "middle_name": farmer.middle_name,
            "last_name": farmer.last_name,
            "barangay_id": farmer.barangay_id
        }
        return jsonify(farmer_data), 200
    else:
        print("Farmer not found")
        return jsonify({"message": "Farmer not found"}), 404
    

@api.route('/users', methods=['GET'])
def get_all_users():
    users = User.query.all()
    user_list = []
    for user in users:
        user_list.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "barangay_id": user.barangay_id,
            "municipality_id": user.municipality_id
        })
    return jsonify(user_list), 200

@api.route('/barangays', methods=['GET'])
def get_all_barangays():
    barangays = Barangay.query.all()
    barangay_list = []
    for b in barangays:
        barangay_list.append({
            "id": b.id,
            "name": b.name,
            "municipality_id": b.municipality_id
        })
    return jsonify(barangay_list), 200

@api.route('/municipalities', methods=['GET'])
def get_all_municipalities():
    municipalities = Municipality.query.all()
    municipality_list = []
    for m in municipalities:
        municipality_list.append({
            "id": m.id,
            "name": m.name
        })
    return jsonify(municipality_list), 200
