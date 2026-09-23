import requests
import time

# --- PENTING: GANTI IP INI DENGAN IP ESP32 KAMU! ---
# Contoh: "http://192.168.1.15"
ESP32_IP = "http://192.168.1.20" 

def kirim_sinyal(status):
    """
    Kirim sinyal ke ESP32.
    status = 1 (Perkelahian Terdeteksi)
    status = 0 (Kondisi Aman/Normal)
    """
    url = f"{ESP32_IP}/sinyal?status={status}"
    
    try:
        print(f"Mengirim sinyal '{status}' ke ESP32...")
        response = requests.get(url, timeout=5)
        print(f"Balasan ESP32: {response.text}\n")
    except requests.exceptions.RequestException as e:
        print(f"Gagal terhubung ke ESP32! Cek koneksi WiFi. Error: {e}\n")

# ==========================================
# SKENARIO PENGETESAN
# ==========================================
if __name__ == "__main__":
    print("--- MEMULAI TES ALARM ---")
    
    # 1. Kirim sinyal bahaya (1)
    kirim_sinyal(1)
    
    # Biarkan alarm nyala selama 10 detik
    print("Menunggu 10 detik...\n")
    time.sleep(10)
    
    # 2. Kirim sinyal aman (0)
    kirim_sinyal(0)
    print("Tes selesai!")