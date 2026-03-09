import pandas as pd
from pymongo import MongoClient
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB Configuration
# For MongoDB Atlas, use the SRV connection string: mongodb+srv://<username>:<password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "crime_db"
COLLECTION_NAME = "crime_incidents"

def import_csv_to_mongo():
    # Detect the latest CSV
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(base_dir, "crime_data_updated.csv")
    if not os.path.exists(data_file):
        data_file = os.path.join(base_dir, "crime_data.csv")
    
    if not os.path.exists(data_file):
        print(f"Error: No CSV file found at {data_file}")
        return

    print(f"Reading data from {data_file}...")
    try:
        df = pd.read_csv(data_file)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    print(f"Connecting to MongoDB at {MONGO_URI.split('@')[-1] if '@' in MONGO_URI else MONGO_URI}...")
    try:
        # Use a longer timeout for connecting to remote clusters
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        # Check connection
        client.admin.command('ping')
        
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Clear existing data (optional, but good for a fresh start with the boilerplate data)
        print(f"Clearing existing data in collection '{COLLECTION_NAME}'...")
        collection.delete_many({})
        
        # Convert DataFrame to list of dictionaries
        records = df.to_dict(orient='records')
        
        # Insert into MongoDB
        print(f"Importing {len(records)} records into MongoDB...")
        collection.insert_many(records)
        
        print("Import completed successfully!")
        client.close()
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        print("\nTip: If you're using MongoDB Atlas, ensure your IP address is whitelisted in the Atlas Network Access settings.")
        sys.exit(1)

if __name__ == "__main__":
    import_csv_to_mongo()
