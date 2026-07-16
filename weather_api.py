# weather_api.py
import json
import time
import redis
import requests

# Inisialisasi koneksi ke kontainer Redis Docker (DB 1 khusus layer caching)
redis_client = redis.Redis(host='localhost', port=6379, db=1)

def get_weather(city: str) -> dict:
    """
    Mengambil data cuaca berdasarkan nama kota dengan strategi Cache-Aside menggunakan Redis.
    """
    # Lakukan sanitasi teks di awal agar konsisten di seluruh fungsi
    clean_city = city.strip()
    cache_key = f"weather:{clean_city.lower()}"
    
    # --------------------------------------------------------------------------
    # 1. CEK CACHE DULU (Cache Look-up)
    # --------------------------------------------------------------------------
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            print(f"⚡ [CACHE HIT] Data cuaca kota '{clean_city}' ditemukan di Redis!")
            return json.loads(cached_data.decode('utf-8'))
    except redis.RedisError as err:
        # Graceful degradation: Jika Redis mati/error, sistem tidak crash & tetap lanjut ke API
        print(f"⚠️ [REDIS ERROR] Gagal membaca cache: {err}")

    # --------------------------------------------------------------------------
    # 2. CACHE MISS (Memanggil API Internal/Eksternal Lambat)
    # --------------------------------------------------------------------------
    print(f"🐢 [CACHE MISS] Data kota '{clean_city}' tidak ditemukan di cache.")
    print("⏳ Menjalankan simulasi API call lambat (2 detik)...")
    time.sleep(2)  # Aturan wajib dari skenario soal
    
    try:
        # Eksekusi pemanggilan HTTP Request asli sesuai contoh skenario soal
        response = requests.get(f"[https://api.example.com/weather/](https://api.example.com/weather/){clean_city.lower()}", timeout=5)
        api_data = response.json()
    except (requests.RequestException, ValueError):
        # Fallback Data: Karena api.example.com adalah domain tiruan, 
        # kita sediakan objek tiruan yang valid agar program tidak memuntahkan error 500.
        api_data = {
            "city": clean_city.capitalize(),
            "temperature": "29°C",
            "condition": "Cloudy",
            "source": "Fallback Simulated API Response",
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    # --------------------------------------------------------------------------
    # 3. SIMPAN KE CACHE (Set Expiry 5 Menit / 300 Detik)
    # --------------------------------------------------------------------------
    try:
        redis_client.setex(
            name=cache_key,
            time=300,  # Masa kedaluwarsa 5 menit sesuai instruksi tugas
            value=json.dumps(api_data)
        )
        print(f"💾 [SAVED TO CACHE] Data kota '{clean_city}' disimpan ke Redis untuk 5 menit ke depan.")
    except redis.RedisError as err:
        print(f"⚠️ [REDIS ERROR] Gagal menyimpan data ke cache: {err}")
        
    return api_data