# Machine Learning and IOT-Based Paddy Rice Monitoring System

**Award:** **TOP 1 Best Paper** – Computing and Information Systems Category  
**Research In-House 2025** | Bohol Island State University - Main Campus

A machine learning and IoT-based paddy rice post-drying monitoring system that integrates real-time sensor data with predictive analytics to optimize rice yield tracking and moisture management across municipal, barangay, and farmer levels.

---

## Overview

Paddy Rice Tracker is an end-to-end IoT-enabled agricultural monitoring platform designed to:
-Capture real-time environmental data (temperature, humidity, moisture) from ESP32/Arduino sensors
-Predict post-drying yield using machine learning models
-Provide role-based dashboards for municipal officers, barangay staff, and farmers
-Provide automated shelf-life recommendations based on final moisture content to optimize storage and reduce spoilage
-Synchronize data across edge devices via RESTful APIs and Cloud Database storage
-Generate temporal analytics to drive data-informed agricultural decisions

---

### Hardware Component
The system relies on edge devices to collect real-time sensor data. The source code for the hardware logic is maintained in a separate repository to decouple the web logic from the embedded systems.

* **Repository:** [paddy-rice-iot-node](https://github.com/jenn-if-err/paddy-rice-iot-node)
* **Role:** Handles sensor data collection (Arduino), runs local ML predictions, and syncs data to this web platform via the `/api/sync` endpoint.

---

## Key Features

### Role-Based Access Control (RBAC)
The system supports three distinct user tiers with specific privileges:
1.  **Municipal Officer:**
    - View aggregated yield statistics across all Barangays.
    - Monitor high-level agricultural performance.
2.  **Barangay Staff:**
    - Manage local farmer registries.
    - Validate and oversee drying records for their jurisdiction.
    - View barangay-specific analytics.
3.  **Farmer:**
    - Personal dashboard to track their specific batch records.
    - View historical drying performance and output.


### Real-Time Analytics Dashboards
- Interactive Chart.js visualizations for yield trends (monthly/yearly)
- Chronologically sorted time-series data with proper year-month ordering
- Comparative analysis of initial vs. final weight per batch and barangay
- Tracking of temperature, humidity, and moisture levels for every drying batch

### IoT Data Pipeline
- RESTful endpoints for secure sensor data ingestion from ESP32/Arduino devices
- UUID-based record tagging for audit trails and duplicate prevention
- JSON-based data syncing between edge devices and the cloud database
- Server-side calculation of moisture reduction and final yield upon data receipt

### Data Management
- CRUD operations for drying records, farmers, and locations
- PostgreSQL database architecture managed via SQLAlchemy ORM
- Enforced foreign key constraints across Municipalities → Barangays → Farmers → Records

## The Team

* **Jennifer Tongco** – Team Leader, Lead Full-Stack Developer & System Architect
* **Claire Justin Pugio** – UI/UX Designer 
* **John Jabez Visarra** – Hardware Engineer & Frontend Support
* **John Kylo Cubelo** – Hardware Engineer
* **Engr. Jeralyn Alagon** – Thesis Adviser

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sync` | POST | Sync drying records from IoT devices |
| `/api/fetch?farmer_uuid=<uuid>` | GET | Retrieve farmer's historical records |
| `/api/farmers/<username>` | GET | Fetch farmer profile by username |
| `/api/users` | GET | List all users (municipal/barangay) |
| `/api/barangays` | GET | List all barangays |
| `/api/municipalities` | GET | List all municipalities |

---

## Tech Stack

### Backend
- **Framework:** Flask 2.3.2 (Python)
- **Database:** PostgreSQL (production) / SQLite (local dev)
- **ORM:** SQLAlchemy 3.1.1
- **Migrations:** Alembic (Flask-Migrate)
- **Authentication:** Flask-Login, Flask-Dance (OAuth), Werkzeug

### Frontend
- **Templating:** Jinja2
- **Visualization:** Chart.js (Yield trends & analytics)
- **Styling:** Bootstrap 5 (Responsive UI)

### IoT & ML Stack (Inferred from Data Schema)
- **Microcontroller**: Raspberry Pi 4 / Arduino (Sensor integration)
- **ML Libraries**: Scikit-learn 1.3.2, Joblib, NumPy, Pandas
- **Algorithm**: Regression Models (trained for moisture/yield prediction)
- **Data Synchronization**: RESTful API (Custom JSON sync via requests)

### Deployment
- **Platform:** Render.com
- **WSGI Server:** Gunicorn 21.2.0
- **Environment:** Python 3.11

---

## Project Structure

```
paddy_rice_tracker/
├── app.py                      # Flask application entry point
├── requirements.txt            # Python dependencies
├── Procfile                    # Render deployment config
├── render.yaml                 # Render service definition
├── website/
│   ├── __init__.py             # Flask app factory
│   ├── models.py               # SQLAlchemy models (User, Farmer, DryingRecord, etc.)
│   ├── views.py                # Main routes (dashboards, CRUD)
│   ├── api.py                  # RESTful API endpoints
│   ├── auth.py                 # Authentication & user management
│   ├── extensions.py           # Flask extensions (db, login_manager, migrate)
│   ├── static/
│   │   ├── logo.svg
│   │   ├── favicon.svg
│   │   └── index.js
│   └── templates/
│       ├── base.html           # Base template with navbar
│       ├── login.html
│       ├── dashboard.html      # Role-specific dashboards
│       ├── analytics.html      # Municipal analytics
│       ├── barangay_analytics.html
│       ├── farmer_analytics.html
│       ├── records.html
│       ├── farmers.html
│       └── ...
├── migrations/                 # Alembic database migrations
└── instance/
    └── database.db             # Local SQLite database (dev only)
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL (for production) or SQLite (auto-created for dev)
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jenn-if-err/paddy_rice_tracker.git
   cd paddy_rice_tracker
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your_secret_key_here
   DATABASE_URL=sqlite:///instance/database.db  # For local dev
   # DATABASE_URL=postgresql://user:password@host/dbname  # For production
   GOOGLE_CLIENT_ID=your_google_oauth_client_id
   GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
   ```

5. **Initialize the database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. **Run the development server**
   ```bash
   python app.py
   ```
   Navigate to `http://127.0.0.1:5000`

---

## 🔧 Database Schema

### Core Models

#### `User` (Municipal & Barangay Staff)
- `id`, `email`, `full_name`, `role` (municipal/barangay)
- `municipality_id`, `barangay_id`, `password`

#### `Farmer`
- `id`, `uuid`, `first_name`, `middle_name`, `last_name`
- `username`, `password`, `barangay_id`, `user_id`

#### `DryingRecord`
- `id`, `uuid`, `timestamp`, `batch_name`
- `initial_weight`, `final_weight`, `temperature`, `humidity`
- `sensor_value`, `initial_moisture`, `final_moisture`, `drying_time`
- `date_dried`, `date_planted`, `date_harvested`, `due_date`
- `farmer_id`, `barangay_id`, `municipality_id`, `user_id`

#### `Municipality` & `Barangay`
- Hierarchical location management

---

## 📡 API Usage Examples

### Sync IoT Data
```bash
POST /api/sync
Content-Type: application/json

{
  "records": [
    {
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
      "batch_name": "Batch A",
      "initial_weight": 100.5,
      "temperature": 28.5,
      "humidity": 65.2,
      "sensor_value": 320,
      "initial_moisture": 24.5,
      "final_moisture": 14.0,
      "drying_time": "48 hours",
      "final_weight": 85.3,
      "date_dried": "2025-12-01",
      "farmer_uuid": "farmer-uuid-here",
      "user_id": 1
    }
  ]
}
```

### Fetch Farmer Records
```bash
GET /api/fetch?farmer_uuid=farmer-uuid-here
```

Response:
```json
[
  {
    "uuid": "...",
    "batch_name": "Batch A",
    "initial_weight": 100.5,
    "final_weight": 85.3,
    "temperature": 28.5,
    "humidity": 65.2,
    "date_dried": "2025-12-01",
    "farmer_name": "Juan Dela Cruz",
    "barangay_name": "San Jose",
    "municipality_name": "Cabanatuan City"
  }
]
```

---

## Deployment

### Render.com (Current Deployment)

1. **Connect GitHub repository** to Render dashboard
2. **Environment variables** are auto-configured via `render.yaml`
3. **Database** is provisioned as a managed PostgreSQL instance
4. **Auto-deploy** on push to `main` branch

### Manual Deployment (Alternative)

```bash
# Install production dependencies
pip install -r requirements.txt

# Set production environment variables
export FLASK_ENV=production
export DATABASE_URL=postgresql://...

# Run database migrations
flask db upgrade

# Start Gunicorn server
gunicorn app:app --bind 0.0.0.0:8000
```

---

## Testing

### Run Local Development Server
```bash
python app.py
```
Debug mode is enabled by default in `app.py` for hot-reloading.

### Test API Endpoints
```bash
# Test sync endpoint
curl -X POST http://127.0.0.1:5000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"records": [...]}'

# Test fetch endpoint
curl http://127.0.0.1:5000/api/fetch?farmer_uuid=<uuid>
```

---

## License

This project is part of an academic thesis and is intended for educational purposes.

---
