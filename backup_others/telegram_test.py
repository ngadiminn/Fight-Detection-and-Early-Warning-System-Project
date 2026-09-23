import requests
import time
from datetime import datetime

# ==========================================
# KONFIGURASI TELEGRAM
# ==========================================
# Aku langsung masukin token dan chat ID kamu yang sebelumnya ya
BOT_TOKEN = "8643840840:AAGjEYMFvXhGfmK0BUo2MRU8BUYsgSIH6Qo"
CHAT_ID = "2147060689"

def test_latensi_telegram(jumlah_test=20):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    print(f"🚀 Memulai uji latensi API Telegram sebanyak {jumlah_test} kali...\n")
    
    data_latensi = []
    
    for i in range(1, jumlah_test + 1):
        waktu_sekarang = datetime.now().strftime("%H:%M:%S")
        pesan = f"🧪 *TESTING LATENSI {i}/{jumlah_test}*\nMengukur waktu respon API pada {waktu_sekarang}"
        payload = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        
        try:
            # 1. Catat waktu AWAL (Mulai Stopwatch)
            start_time = time.time()
            
            # 2. Tembak data ke server Telegram
            response = requests.post(url, json=payload, timeout=5)
            
            # 3. Catat waktu AKHIR (Stopwatch Berhenti)
            end_time = time.time()
            
            # 4. Hitung selisih latensi dalam milidetik (ms)
            latensi_ms = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                print(f"[{i:02d}] ✅ Sukses | Latensi: {latensi_ms:.2f} ms")
                data_latensi.append(latensi_ms)
            else:
                print(f"[{i:02d}] ❌ Gagal | Kode Status: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"[{i:02d}] ⚠️ Error jaringan: {e}")
        
        # Jeda 1 detik agar tidak terkena blokir (Limit API Telegram)
        time.sleep(1)
        
    # ==========================================
    # REKAPITULASI HASIL (Untuk Data Laporan Bab 4)
    # ==========================================
    if data_latensi:
        rata_rata = sum(data_latensi) / len(data_latensi)
        tercepat = min(data_latensi)
        terlama = max(data_latensi)
        
        print("\n" + "="*45)
        print("HASIL REKAPITULASI LATENSI TELEGRAM")
        print("="*45)
        print(f"Total Pesan Terkirim : {len(data_latensi)}/{jumlah_test} Sukses")
        print(f"Rata-rata Latensi    : {rata_rata:.2f} ms")
        print(f"Latensi Tercepat     : {tercepat:.2f} ms")
        print(f"Latensi Terlama      : {terlama:.2f} ms")
        print("="*45)
        print("Data siap disalin ke tabel pengujian Laporan TA! 🥳")

if __name__ == "__main__":
    # Menjalankan fungsi dengan 20 kali percobaan
    test_latensi_telegram(20)