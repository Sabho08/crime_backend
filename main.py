from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import joblib
import os
from analysis import get_hotspots_data, get_bns_stats_data, train_model, get_predictive_zones_data

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
DATA_FILE = os.path.join(BASE_DIR, "crime_data_updated.csv")
if not os.path.exists(DATA_FILE):
    DATA_FILE = os.path.join(BASE_DIR, "crime_data.csv")
MODEL_FILE = os.path.join(BASE_DIR, "risk_model.joblib")
ENCODER_FILE = os.path.join(BASE_DIR, "tod_encoder.joblib")

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

def load_data():
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError("Crime data not found. Please run data_gen.py first.")
    return pd.read_csv(DATA_FILE)

@app.on_event("startup")
def startup_event():
    # Generate data and train model if not present
    if not os.path.exists(DATA_FILE):
        print("Generating synthetic data...")
        import data_gen
        data_gen.generate_crime_data()
    
    df = load_data()
    if not os.path.exists(MODEL_FILE):
        print("Training risk prediction model...")
        train_model(df)

@app.get("/hotspots")
def get_hotspots():
    df = load_data()
    return pd.DataFrame(get_hotspots_data(df)).fillna(0).to_dict(orient='records')

@app.get("/bns-stats")
def get_bns_stats():
    df = load_data()
    stats = get_bns_stats_data(df)
    # Convert keys to string for JSON compatibility if they are integers
    return {str(k): v for k, v in stats.items()}

@app.get("/predictive-zones")
def get_predictive_zones():
    df = load_data()
    return pd.DataFrame(get_predictive_zones_data(df)).fillna(0).to_dict(orient='records')

@app.get("/firs")
def get_firs():
    df = load_data()
    # Add a synthetic status and risk for the table
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
        df = load_data()
        
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

        # Map crime_type to BNS (Simplified)
        bns_map = {'Theft': 303, 'Robbery': 309, 'Assault': 115, 'Harassment': 74, 'Nuisance': 126}
        bns = bns_map.get(req.crime_type, 303)

        # Create row exactly matching the CSV header order
        # FIR_UID,BNS_Section,Crime_Type,Timestamp,Time_of_Day,Latitude,Longitude,Dist_to_PS,
        # Area_Type,Area_Zone,Crime_Frequency,Target,Place,Event,Relation,Lighting,CCTV,
        # Modus_Operandi,Weather,Response_Time_Mins,Patrol_Frequency
        new_row_list = [
            f'CIT-2026-{len(df) + 1}', # FIR_UID
            bns,                       # BNS_Section
            req.crime_type,            # Crime_Type
            req.time,                  # Timestamp
            tod,                       # Time_of_Day
            req.latitude,              # Latitude
            req.longitude,             # Longitude
            1.0,                       # Dist_to_PS
            "Urban",                   # Area_Type
            "Residential",             # Area_Zone
            "Low",                     # Crime_Frequency
            "Adult",                   # Target
            "Street",                  # Place
            "None",                    # Event
            "Stranger",                # Relation
            "Well Lit",                # Lighting
            "No",                      # CCTV
            "Unknown",                 # Modus_Operandi
            "Clear",                   # Weather
            0,                         # Response_Time_Mins
            "None",                    # Patrol_Frequency
            req.description            # Description
        ]
        
        # Append to the CSV as a single line
        import csv
        with open(DATA_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(new_row_list)
            
        return {"status": "success", "message": "Incident reported successfully."}
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable if available (e.g., for Render/Heroku)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
