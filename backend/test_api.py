import requests
import json

BASE_URL = "http://localhost:8000"

def test_prediction():
    print("=== Testing POST /predict ===")
    
    # This matches the schema we built for PredictionRequest
    payload = {
        "period": 3,
        "external_features": {
            "harga_gkg": 7800.0,
            "curah_hujan": 150.5,
            "produksi_padi": 52000.0,
            "inflasi_pangan": 0.4,
            "lebaran": 0
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/predict", json=payload)
        response.raise_for_status()
        data = response.json()
        print("✅ Prediction Successful!")
        print(f"Next Prediction: {data['prediction']}")
        print(f"Features Used (First Step): {json.dumps(data['details']['steps'][0]['features_used'], indent=2)}")
        print(f"Time Series Points returned: {len(data['series'])}")

        print("\n=== Testing POST /predict (Fallback without external_features) ===")
        fallback_payload = {"period": 2}
        resp_fallback = requests.post(f"{BASE_URL}/predict", json=fallback_payload)
        resp_fallback.raise_for_status()
        print("✅ Fallback Prediction Successful!")
        print(f"Fallback Next Prediction: {resp_fallback.json()['prediction']}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Prediction Failed: {e}")
        if e.response is not None:
            print(f"Details: {e.response.text}")

def test_get_historical():
    print("\n=== Testing GET /data/historical ===")
    try:
        response = requests.get(f"{BASE_URL}/data/historical?limit=30")
        response.raise_for_status()
        data = response.json()
        print("✅ Fetch Historical Data Successful!")
        print(f"Retrieved {len(data)} records.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Fetch Historical Data Failed: {e}")

def test_get_metrics():
    print("\n=== Testing GET /metrics ===")
    try:
        response = requests.get(f"{BASE_URL}/metrics")
        response.raise_for_status()
        data = response.json()
        print("✅ Fetch Metrics Successful!")
        print(f"Retrieved {len(data)} metrics records.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Fetch Metrics Failed: {e}")

if __name__ == "__main__":
    print("Make sure your FastAPI server is running (uvicorn app.main:app --reload)")
    print("and that the database connection is fixed!\n")
    
    test_get_historical()
    test_prediction()
    test_get_metrics()
