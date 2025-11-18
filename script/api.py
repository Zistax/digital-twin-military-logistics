import requests

url = "http://127.0.0.1:8000/predict_risk"

payload = {
    "total_minutes": 120,
    "timestep_minutes": 10,
    "n_convoys": 3,
}

response = requests.post(url, json=payload)
print("Status code:", response.status_code)
print("JSON:", response.json())