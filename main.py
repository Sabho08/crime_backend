from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import joblib
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from analysis import get_hotspots_data, get_bns_stats_data, train_model, get_predictive_zones_data

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Urban Crime Pattern Recognition System")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(BASE_DIR, "risk_model.joblib")
ENCODER_FILE = os.path.join(BASE_DIR, "tod_encoder.joblib")

# MongoDB Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "crime_db"
COLLECTION_NAME = "crime_incidents"

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

class PredictionRequest(BaseModel):
    latitude: float
    longitude: float
    time_of_day: str  # 'Morning', 'Afternoon', 'Evening', 'Night'
    dist_to_ps: float

class ReportRequest(BaseModel):
    latitude: float
    longitude: float
    crime_type: str
    description: str
    time: str # ISO format or string
    # Multi-Vector Ingestion Fields (Matches PDF Slide 5)
    lighting: str = "Unknown"  # 'Well Lit', 'Dim', 'Dark', 'CCTV Shadow'
    cctv: str = "Unknown"      # 'Yes', 'No', 'Blind Spot'
    weapon: str = "None"       # 'None', 'Firearm', 'Blunt Object', 'Sharp Object'
    victim_count: int = 1

def load_data():
    try:
        cursor = collection.find({}, {'_id': False})
        df = pd.DataFrame(list(cursor))
        if df.empty:
             raise HTTPException(status_code=500, detail="No crime data found in database.")
        return df
    except Exception as e:
        print(f"Error loading data from MongoDB: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
def startup_event():
    # If DB is empty, try to import from CSV first
    try:
        # Check if connected
        client.admin.command('ping')
        if collection.count_documents({}) == 0:
            print("Database empty. Attempting to import from CSV...")
            try:
                import import_to_mongodb
                import_to_mongodb.import_csv_to_mongo()
            except Exception as e:
                print(f"Failed to auto-import CSV: {e}")
        
        try:
            df = load_data()
            if not os.path.exists(MODEL_FILE):
                print("Training risk prediction model...")
                train_model(df)
        except Exception as e:
            print(f"Startup error: {e}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        print("\nTip: If you're using MongoDB Atlas, ensure your IP address is whitelisted in the Atlas Network Access settings.")

@app.get("/hotspots")
def get_hotspots():
    df = load_data()
    return pd.DataFrame(get_hotspots_data(df)).fillna(0).to_dict(orient='records')

@app.get("/bns-stats")
def get_bns_stats():
    df = load_data()
    stats = get_bns_stats_data(df)
    return {str(k): v for k, v in stats.items()}

@app.get("/predictive-zones")
def get_predictive_zones():
    df = load_data()
    return pd.DataFrame(get_predictive_zones_data(df)).fillna(0).to_dict(orient='records')

@app.get("/firs")
def get_firs():
    df = load_data()
    df['Status'] = df['BNS_Section'].apply(lambda x: 'Inquiry' if x % 2 == 0 else 'Arrested')
    df['Risk'] = df['Dist_to_PS'].apply(lambda x: 'High' if x > 3 else 'Medium' if x > 1.5 else 'Low')
    return df.fillna("Unknown").to_dict(orient='records')

@app.post("/predict")
def predict_risk(req: PredictionRequest):
    if not os.path.exists(MODEL_FILE) or not os.path.exists(ENCODER_FILE):
        raise HTTPException(status_code=500, detail="Prediction model not trained.")
    
    model = joblib.load(MODEL_FILE)
    le = joblib.load(ENCODER_FILE)
    
    try:
        tod_encoded = le.transform([req.time_of_day])[0]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time_of_day value.")
    
    features = [[req.latitude, req.longitude, tod_encoded, req.dist_to_ps]]
    risk_score = model.predict(features)[0]
    
    return {
        "latitude": req.latitude,
        "longitude": req.longitude,
        "risk_score": round(float(risk_score), 2)
    }

@app.post("/report")
def report_crime(req: ReportRequest):
    try:
        # Simple Time_of_Day logic
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(req.time.replace('Z', '+00:00'))
            hour = dt.hour
            if 5 <= hour < 12: tod = 'Morning'
            elif 12 <= hour < 17: tod = 'Afternoon'
            elif 17 <= hour < 21: tod = 'Evening'
            else: tod = 'Night'
        except:
            tod = 'Night'

        bns_map = {'Theft': 303, 'Robbery': 309, 'Assault': 115, 'Harassment': 74, 'Nuisance': 126}
        bns = bns_map.get(req.crime_type, 303)

        count = collection.count_documents({})
        
        new_doc = {
            'FIR_UID': f'CIT-2026-{count + 1}',
            'BNS_Section': bns,
            'Crime_Type': req.crime_type,
            'Timestamp': req.time,
            'Time_of_Day': tod,
            'Latitude': req.latitude,
            'Longitude': req.longitude,
            'Dist_to_PS': 1.0,
            'Area_Type': "Urban",
            'Area_Zone': "Residential",
            'Crime_Frequency': "Low",
            'Target': "Adult",
            'Place': "Street",
            'Event': "None",
            'Relation': "Stranger",
            'Lighting': "Well Lit",
            'CCTV': "No",
            'Modus_Operandi': "Unknown",
            'Weather': "Clear",
            'Response_Time_Mins': 0,
            'Patrol_Frequency': "None",
            'Description': req.description
        }
        
        collection.insert_one(new_doc)
        
        is_organized_crime = (bns == 111)
            
        return {
            "status": "success", 
            "message": "Incident reported successfully.",
            "flag_nia": is_organized_crime,
            "bns_details": f"Section {bns} - {req.crime_type}"
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deterrence-advisories")
def get_deterrence_advisories():
    df = load_data()
    hotspots = get_hotspots_data(df)
    
    advisories = []
    for h in hotspots[:5]:
        risk = h.get('Risk_Score', 0)
        patrol_freq = "High (Hourly)" if risk > 15 else "Medium (2-4 hours)"
        advisories.append({
            "location": [h['Latitude'], h['Longitude']],
            "risk_score": round(risk, 2),
            "patrol_frequency": patrol_freq,
            "checkpoint_recommended": risk > 18,
            "advisory": f"Concentrate police presence in {patrol_freq} intervals due to high {h['Crime_Type'] if 'Crime_Type' in h else 'crime'} patterns."
        })
    return advisories

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
