import requests
import time
import datetime

# --- KONFIGURASI ESP32 ---
ESP32_IP = "http://192.168.1.20" 

# --- KONFIGURASI TELEGRAM ---
# Masukkan data dari Notepad kamu ke dalam tanda kutip di bawah ini
BOT_TOKEN = "8643840840:AAGjEYMFvXhGfmK0BUo2MRU8BUYsgSIH6Qo"
CHAT_ID = "2147060689"

def dapatkan_waktu_sekarang():
    """Mengambil waktu dan tanggal saat ini secara real-time"""
    sekarang = datetime.datetime.now()
    waktu_str = sekarang.strftime("%H:%M:%S WIB")
    
    bulan_indo = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                  "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    tanggal_str = f"{sekarang.day:02d} {bulan_indo[sekarang.month]} {sekarang.year}"
    
    return waktu_str, tanggal_str

def kirim_telegram():
    """Mengirim pesan ke Telegram menggunakan API resmi"""
    waktu, tanggal = dapatkan_waktu_sekarang()
    
    # Format pesan menggunakan Markdown (Bintang * untuk Bold)
    pesan = (
        "⚠️ *EMERGENCY ALERT*\n\n"
        "Telah terdeteksi indikasi perkelahian!\n"
        "📍 Lokasi: Ruang Kelas TULT 14.09\n"
        f"🕒 Waktu: {waktu}\n"
        f"📅 Tanggal: {tanggal}\n\n"
        "Tindakan output fisik alarm & lampu telah diaktifkan. Harap segera lakukan intervensi."
    )
    
    # URL resmi API Telegram
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Data yang dikirim ke server Telegram
    payload = {
        "chat_id": CHAT_ID,
        "text": pesan,
        "parse_mode": "Markdown" # Biar format bold-nya terbaca
    }
    
    try:
        print("\n[SISTEM] Memproses pengiriman notifikasi Telegram...")
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            print("[SISTEM] Notifikasi Telegram sukses terkirim secepat kilat! ⚡")
        else:
            print(f"[SISTEM] Gagal mengirim Telegram. Error: {response.text}")
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan koneksi ke Telegram. Error: {e}")

def kirim_sinyal(status):
    """Mengirimkan sinyal ke ESP32 dan memicu Telegram jika status = 1"""
    url = f"{ESP32_IP}/sinyal?status={status}"
    
    try:
        print(f"\nMengirim sinyal '{status}' ke ESP32...")
        response = requests.get(url, timeout=5)
        print(f"Balasan ESP32: {response.text}")
        
        # Pemicu Logika: Jika sinyal bahaya (1) sukses, langsung hajar kirim Telegram
        if status == 1 and response.status_code == 200:
            kirim_telegram()
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Gagal terhubung ke ESP32! Periksa koneksi WiFi. Error: {e}")

# ==========================================
# SKENARIO PENGETESAN
# ==========================================
if __name__ == "__main__":
    print("--- MEMULAI TES ALARM (ESP32 + TELEGRAM) ---")
    
    # 1. Kirim sinyal bahaya
    kirim_sinyal(1)
    
    # Biarkan alarm nyala selama 10 detik
    print("\nMenunggu 10 detik...\n")
    time.sleep(10)
    
    # 2. Kirim sinyal aman
    kirim_sinyal(0)
    print("\nTes selesai, mantap komandan!")