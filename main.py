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
DATA_FILE = os.path.join(BASE_DIR, "crime_data.csv")
MODEL_FILE = os.path.join(BASE_DIR, "risk_model.joblib")
ENCODER_FILE = os.path.join(BASE_DIR, "tod_encoder.joblib")

class PredictionRequest(BaseModel):
    latitude: float
    longitude: float
    time_of_day: str  # 'Morning', 'Afternoon', 'Evening', 'Night'
    dist_to_ps: float

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

if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable if available (e.g., for Render/Heroku)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
