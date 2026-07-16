# test_weather.py
from weather_api import get_weather
import time

print("--- PANGGILAN PERTAMA (Harusnya Lambat - Cache Miss) ---")
start_time = time.time()
data1 = get_weather("Semarang")
print(f"Hasil Data: {data1}")
print(f"⏱️ Waktu Eksekusi: {time.time() - start_time:.2f} detik\n")

print("--- PANGGILAN KEDUA (Harusnya Instan - Cache Hit!) ---")
start_time = time.time()
data2 = get_weather("Semarang")
print(f"Hasil Data: {data2}")
print(f"⚡ Waktu Eksekusi: {time.time() - start_time:.4f} detik\n")