import pandas as pd
import random
from datetime import datetime, timedelta
import os

# Mumbai locations coordinate pool from data_gen.py
COORDINATE_POOL = [
    [18.9221, 72.8337], [18.9256, 72.8242], [18.9400, 72.8353], [18.9432, 72.8231], [18.9543, 72.8115],
    [18.9548, 72.7985], [18.9633, 72.8155], [18.9690, 72.8205], [18.9750, 72.8333], [18.9700, 72.8400],
    [19.0020, 72.8180], [19.0166, 72.8295], [19.0222, 72.8400], [19.0270, 72.8500], [19.0210, 72.8540],
    [19.0370, 72.8633], [19.0400, 72.8400], [19.0430, 72.8250], [19.0630, 72.8280], [19.0650, 72.8630],
    [19.0686, 72.8766], [19.0620, 72.8980], [19.0860, 72.9080], [19.1100, 72.9200], [19.1450, 72.9300],
    [19.1720, 72.9400], [19.1170, 72.8750], [19.1300, 72.8150], [19.1060, 72.8250], [19.0800, 72.8550],
    [19.1000, 72.8400], [19.0880, 72.8680], [19.1330, 72.9150], [19.1100, 72.8950], [19.1500, 72.8800],
    [19.1850, 72.8350], [19.2100, 72.8700], [19.2450, 72.8500], [19.2550, 72.8650], [19.0500, 72.9300],
    [19.0200, 72.9200], [19.0400, 72.9250], [19.0550, 72.9150], [19.1000, 72.8800], [19.1150, 72.8850],
    [19.0580, 72.8450], [18.9680, 72.8130], [18.9650, 72.8050], [18.9950, 72.8400], [19.0000, 72.8550],
    [18.9300, 72.8300], [18.9350, 72.8280], [18.9450, 72.8380], [18.9500, 72.8200], [18.9580, 72.8050],
    [18.9620, 72.8300], [18.9720, 72.8250], [18.9780, 72.8150], [18.9850, 72.8300], [18.9900, 72.8200],
    [19.0100, 72.8250], [19.0150, 72.8400], [19.0250, 72.8300], [19.0300, 72.8450], [19.0350, 72.8550],
    [19.0450, 72.8350], [19.0520, 72.8500], [19.0600, 72.8400], [19.0700, 72.8300], [19.0750, 72.8650],
    [19.0850, 72.8450], [19.0920, 72.8300], [19.1020, 72.8500], [19.1120, 72.8600], [19.1220, 72.8700],
    [19.1320, 72.8800], [19.1420, 72.8900], [19.1520, 72.9000], [19.1620, 72.9100], [19.1720, 72.9200],
    [19.1820, 72.9300], [19.1920, 72.9400], [19.2020, 72.8600], [19.2120, 72.8500], [19.2220, 72.8450],
    [19.2320, 72.8550], [19.2420, 72.8650], [19.2520, 72.8750], [19.2620, 72.8850], [19.2720, 72.8950],
    [19.1000, 72.9100], [19.0900, 72.9000], [19.0800, 72.8900], [19.0700, 72.8800], [19.1250, 72.8350],
    [19.1350, 72.8450], [19.1450, 72.8550], [19.1550, 72.8650], [19.1650, 72.8750], [19.1750, 72.8850]
]

def get_time_of_day(timestamp):
    hour = timestamp.hour
    if 5 <= hour < 12:
        return 'Morning'
    elif 12 <= hour < 17:
        return 'Afternoon'
    elif 17 <= hour < 21:
        return 'Evening'
    else:
        return 'Night'

def generate_ultimate_crime_data(num_rows=5000):
    data = []
    
    # BNS sections from ggs.py
    bns_sections = {
        '303': 'Theft', '308': 'Robbery', '311': 'Robbery/Death', 
        '115': 'Hurt', '305': 'Burglary', '63/64': 'Rape',
        '111': 'Organized Crime', '126': 'Public Nuisance', '70': 'Sexual Offenses', 
        '103': 'Murder', '310': 'Robbery', '320': 'Mischief'
    }
    
    mo_tags = ['Lock Breaking', 'Snatching', 'Deception', 'Tailgating', 'Forced Entry', 'Bypassing Alarm']
    lighting = ['Daylight', 'Well Lit', 'Dim Light', 'Pitch Dark']
    weather = ['Clear', 'Rainy', 'Foggy', 'Humid']
    patrol_options = ['Hourly', 'Twice-Daily', 'Only on Call', 'No Active Patrol']
    relations = ['Stranger', 'Neighbor', 'Friend', 'Family Member', 'Acquaintance']
    zones = ['Residential', 'Industrial', 'Commercial']
    area_types = ['Urban', 'Slum', 'Rural']
    
    for i in range(num_rows):
        fir_no = f"MH-MUM-2026-{60000 + i}"
        section_code = random.choice(list(bns_sections.keys()))
        crime = bns_sections[section_code]
        area_type = random.choice(area_types)
        
        # --- Area Zone Logic ---
        if crime == 'Burglary':
            area_zone = random.choices(zones, weights=[70, 10, 20])[0]
        elif crime == 'Theft':
            area_zone = random.choices(zones, weights=[20, 20, 60])[0]
        else:
            area_zone = random.choice(zones)

        # --- Environmental Factors Logic ---
        if crime == 'Burglary':
            light = random.choices(lighting, weights=[5, 10, 25, 60])[0]
            mo = 'Lock Breaking'
            weather_cond = random.choices(weather, weights=[40, 40, 10, 10])[0]
            patrol_freq = random.choices(patrol_options, weights=[5, 15, 30, 50])[0] 
        elif crime == 'Theft':
            light = random.choice(lighting)
            mo = 'Snatching'
            weather_cond = 'Clear'
            patrol_freq = random.choice(patrol_options)
        else:
            light = random.choice(lighting)
            mo = random.choice(mo_tags)
            weather_cond = random.choice(weather)
            patrol_freq = random.choice(patrol_options)

        # --- Crime Frequency Logic ---
        if area_type == 'Slum' or patrol_freq == 'No Active Patrol':
            crime_freq = random.choices(['High', 'Medium'], weights=[70, 30])[0]
        elif patrol_freq == 'Hourly':
            crime_freq = random.choices(['Low', 'Medium'], weights=[80, 20])[0]
        else:
            crime_freq = random.choice(['Low', 'Medium', 'High'])

        # Spatio-Temporal
        timestamp = datetime(2026, 1, 1) + timedelta(days=random.randint(0, 365), hours=random.randint(0, 23))
        
        # Use COORDINATE_POOL from data_gen.py
        loc = random.choice(COORDINATE_POOL)
        lat, lon = loc[0], loc[1]
        
        # --- Relation Logic ---
        if crime == 'Hurt':
            relation = random.choices(['Neighbor', 'Friend', 'Family Member'], weights=[50, 25, 25])[0]
        elif crime in ['Theft', 'Robbery', 'Burglary']:
            relation = 'Stranger'
        else:
            relation = random.choice(relations)
            
        dist_to_ps = round(random.uniform(0.1, 8.0), 2)
        time_of_day = get_time_of_day(timestamp)
        
        # Numeric BNS code for backend logic if possible
        try:
            bns_code = int(section_code.split('/')[0])
        except:
            bns_code = 303 # Fallback
            
        data.append({
            'FIR_UID': fir_no,
            'BNS_Section': bns_code,
            'Crime_Type': crime,
            'Timestamp': timestamp,
            'Time_of_Day': time_of_day,
            'Latitude': lat,
            'Longitude': lon,
            'Dist_to_PS': dist_to_ps,
            'Area_Type': area_type,
            'Area_Zone': area_zone,
            'Crime_Frequency': crime_freq,
            'Target': random.choice(['Old', 'Kid', 'Mid-age']),
            'Place': random.choice(['House', 'Shop', 'Street', 'Bank']),
            'Event': random.choice(['Holi', 'Navratri', 'None']),
            'Relation': relation,
            'Lighting': light,
            'CCTV': random.choice(['Yes', 'No']),
            'Modus_Operandi': mo,
            'Weather': weather_cond,
            'Response_Time_Mins': random.randint(5, 45),
            'Patrol_Frequency': patrol_freq
        })
    
    return pd.DataFrame(data)

if __name__ == "__main__":
    df = generate_ultimate_crime_data(5000)
    
    # Save to crime_data_updated.csv
    output_path = os.path.join(os.path.dirname(__file__), 'crime_data_updated.csv')
    df.to_csv(output_path, index=False)
    print(f"Dataset generated successfully with {len(df)} rows at {output_path}")
    print("Columns included:", list(df.columns))
