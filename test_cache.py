# test_cache.py
import time
from weather_api import get_weather

print("==================================================")
print("       RUNNING REDIS CACHING TEST SCRIPT          ")
print("==================================================\n")

# Panggilan Pertama - Harus Lambat (2 detik)
print("[TEST] Menjalankan Panggilan Pertama...")
start = time.time()
result1 = get_weather("Jakarta")
time1 = time.time() - start
print(f"👉 First call result: {time1:.2f}s\n")

print("--------------------------------------------------\n")

# Panggilan Kedua - Harus Cepat (< 0.1 detik)
print("[TEST] Menjalankan Panggilan Kedua (Data Ter-cache)...")
start = time.time()
result2 = get_weather("Jakarta")
time2 = time.time() - start
print(f"👉 Second call (cached) result: {time2:.4f}s\n")

print("==================================================")
print("               TEST SELESAI                       ")
print("==================================================")
