import requests
import json

# URL Firebase kamu
FIREBASE_URL = "https://toko-4960c-default-rtdb.asia-southeast1.firebasedatabase.app"

def save_data(path, data):
    """Menyimpan data ke path tertentu di Firebase"""
    url = f"{FIREBASE_URL}/{path}.json"
    res = requests.put(url, json=data)
    if res.status_code == 200:
        return True
    else:
        print("Error saving:", res.text)
        return False

def load_data(path):
    """Mengambil data dari path tertentu di Firebase"""
    url = f"{FIREBASE_URL}/{path}.json"
    res = requests.get(url)
    if res.status_code == 200:
        return res.json() or {}
    else:
        print("Error loading:", res.text)
        return {}

def push_data(path, data):
    """Menambahkan data baru (auto-ID) ke path tertentu"""
    url = f"{FIREBASE_URL}/{path}.json"
    res = requests.post(url, json=data)
    if res.status_code == 200:
        return res.json()["name"]
    else:
        print("Error pushing:", res.text)
        return None
