import sys
sys.path.append('.')
from utils.cwa_api import CWAApiClient
import json

client = CWAApiClient()
data = client.fetch_dataset("W-C0034-005")
if data:
    records = data.get('records', {})
    tropical_cyclones = records.get('TropicalCyclones', {}).get('TropicalCyclone', [])
    for tc in tropical_cyclones:
        name = tc.get('TyphoonName', 'Unknown')
        print(f"Typhoon Name: {name}")
        analysis = tc.get('AnalysisData', {}).get('Fix', [])
        if analysis:
            latest = analysis[-1]
            print(f"Speed: {latest.get('MaxWindSpeed')}")
            print(f"Dir: {latest.get('MovingDirection')}")
