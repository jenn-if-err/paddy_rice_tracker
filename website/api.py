from flask import Blueprint, request, jsonify
from .models import DryingRecord
from .extensions import db
from flask_login import login_required, current_user

api = Blueprint('api', __name__)

@api.route('/sync', methods=['POST'])
@login_required
def sync():
    try:
        data = request.get_json()

        # Process and sync data
        for record in data.get('records', []):
            new_record = DryingRecord(
                initial_weight=record['initial_weight'],
                temperature=record['temperature'],
                humidity=record['humidity'],
                sensor_value=record['sensor_value'],
                initial_moisture=record['initial_moisture'],
                final_moisture=record['final_moisture'],
                drying_time=record['drying_time'],
                final_weight=record['final_weight'],
                user_id=current_user.id
            )
            db.session.add(new_record)

        db.session.commit()
        return jsonify({"status": "success", "message": "Records synced."}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
