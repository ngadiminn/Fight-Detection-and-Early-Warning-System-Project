import cv2
import requests
import time
import threading
import datetime
from collections import deque
import Fight_utils_mvit

# ==========================================
# KONFIGURASI ALAMAT
# ==========================================
RTSP_URL = "rtsp://admin:Artyago_23@10.203.104.175:554/cam/realmonitor?channel=1&subtype=1" 
ESP32_IP = "http://10.203.104.95" 

# ==========================================
# KONFIGURASI TELEGRAM
# ==========================================
BOT_TOKEN = "8643840840:AAGjEYMFvXhGfmK0BUo2MRU8BUYsgSIH6Qo"
CHAT_ID = "2147060689"

# ==========================================
# KONFIGURASI MODEL
# ==========================================
MODEL_PATH = "mvit_fight_model.pth"
SEQUENCE_LENGTH = 16
FRAME_SKIP = 2 # Mengekstrak 1 frame setiap 2 frame agar lebih efisien

# Variabel Global
status_terakhir = -1 
waktu_mulai_bahaya = 0      
telegram_terkirim = False   
predicted_class_name = "Loading..."
is_inferencing = False

# ==========================================
# FUNGSI JALUR BELAKANG (THREADING)
# ==========================================
def tugas_ngirim_ke_esp(status_dikirim):
    """Mengirim perintah ke ESP32 tanpa bikin video patah-patah"""
    sekarang = datetime.datetime.now()
    timestamp_str = sekarang.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    url = f"{ESP32_IP}/sinyal"
    params = {
        "status": status_dikirim,
        "timestamp": timestamp_str
    }
    try:
        response = requests.get(url, params=params, timeout=2)
        print(f"[{timestamp_str}] [ESP32] Sinyal '{status_dikirim}' terkirim! Balasan: {response.text}")
    except Exception as e:
        print(f"[{timestamp_str}] [ESP32 ERROR] Gagal konek: {e}")

def tugas_ngirim_telegram():
    """Mengirim Telegram pakai API resmi tanpa bikin video ngelag"""
    sekarang = datetime.datetime.now()
    waktu_str = sekarang.strftime("%H:%M:%S WIB")
    bulan_indo = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                  "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    tanggal_str = f"{sekarang.day:02d} {bulan_indo[sekarang.month]} {sekarang.year}"
    timestamp_str = sekarang.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    pesan = (
        "⚠️ *EMERGENCY ALERT*\n\n"
        "Telah terdeteksi indikasi perkelahian!\n"
        "📍 Lokasi: Ruang Laboratorium P304\n"
        f"🕒 Waktu: {waktu_str}\n"
        f"📅 Tanggal: {tanggal_str}\n\n"
        "Tindakan output fisik alarm & lampu telah diaktifkan. Harap segera lakukan intervensi."
    )
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    
    try:
        print(f"\n[{timestamp_str}] [TELEGRAM] Memproses pengiriman pesan...")
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"[{timestamp_str}] [TELEGRAM] Pesan peringatan SUKSES terkirim! ⚡\n")
        else:
            print(f"[{timestamp_str}] [TELEGRAM ERROR] Gagal: {response.text}")
    except Exception as e:
        print(f"[{timestamp_str}] [TELEGRAM ERROR] Koneksi bermasalah: {e}")

def run_inference_thread(frames, model):
    """Menjalankan prediksi AI di thread terpisah agar video tidak lag"""
    global predicted_class_name, is_inferencing
    try:
        # Fungsi ini mereturn class dengan probabilitas tertinggi ('fight' atau 'noFight')
        prediction = Fight_utils_mvit.streaming_framesInference(frames, model)
        predicted_class_name = prediction
    except Exception as e:
        print(f"[INFERENCE ERROR] {e}")
    finally:
        is_inferencing = False

# ==========================================
# BUKA KAMERA RTSP & INISIALISASI MODEL
# ==========================================
print("Memuat Model MViT... (Ini butuh beberapa detik)")
model = Fight_utils_mvit.loadModel(MODEL_PATH)
print("Model berhasil dimuat!")

print("Mencoba menyambung ke IP Cam...")
cap = cv2.VideoCapture(RTSP_URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 2) 

if not cap.isOpened():
    print("[ERROR] Gagal membuka stream RTSP.")
    exit()

print("Kamera terhubung! Tekan huruf 'q' di jendela video untuk keluar.")

frames_queue = deque(maxlen=SEQUENCE_LENGTH)
frame_counter = 0

while True:
    success, img = cap.read()
    if not success:
        time.sleep(0.1)
        continue

    # Resize untuk tampilan (tidak mempengaruhi input model karena di-resize di utils)
    display_img = cv2.resize(img, (1024, 768))
    
    # Ambil frame untuk inferensi sesuai FRAME_SKIP
    if frame_counter % FRAME_SKIP == 0:
        frames_queue.append(img)
        
    frame_counter += 1

    # Jika queue penuh dan tidak sedang inferensi, mulai proses deteksi di background
    if len(frames_queue) == SEQUENCE_LENGTH and not is_inferencing:
        is_inferencing = True
        # Copy queue ke list agar aman dari perubahan antrian saat inferensi berjalan
        frames_list = list(frames_queue)
        threading.Thread(target=run_inference_thread, args=(frames_list, model)).start()

    # ==========================================
    # LOGIKA UTAMA (SINYAL ESP32 & DELAY 20 DETIK TELEGRAM)
    # ==========================================
    if predicted_class_name == "fight": # BAHAYA (1)
        
        # Jika baru pertama kali mendeteksi bahaya
        if status_terakhir != 1:
            print(">>> Perkelahian terdeteksi! Memulai alarm ESP32...")
            threading.Thread(target=tugas_ngirim_ke_esp, args=(1,)).start()
            
            status_terakhir = 1
            waktu_mulai_bahaya = time.time() # Mulai nyalakan stopwatch
            telegram_terkirim = False        # Reset status telegram
            
        # Hitung durasi bahaya yang sedang berlangsung
        durasi_bahaya = time.time() - waktu_mulai_bahaya
        
        # Tampilkan teks timer di layar
        cv2.putText(display_img, f"PERKELAHIAN!! - Durasi: {int(durasi_bahaya)}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        # Cek apakah durasi sudah tembus 20 detik dan telegram belum terkirim
        if durasi_bahaya >= 20.0 and not telegram_terkirim:
            threading.Thread(target=tugas_ngirim_telegram).start()
            telegram_terkirim = True # Kunci agar tidak spam berkali-kali
            
        # Tampilkan notif di layar kalau Telegram udah kekirim
        if telegram_terkirim:
            cv2.putText(display_img, "TELEGRAM TERKIRIM!", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
    elif predicted_class_name == "noFight": # AMAN (0)
        
        # Jika baru pertama kali mendeteksi aman
        if status_terakhir != 0:
            print(">>> Kondisi Aman. Mematikan alarm ESP32 & reset timer...")
            threading.Thread(target=tugas_ngirim_ke_esp, args=(0,)).start()
            
            status_terakhir = 0
            waktu_mulai_bahaya = 0    # Reset stopwatch
            telegram_terkirim = False # Reset status telegram
            
        cv2.putText(display_img, "AMAN - No Fight", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    else:
        # Sedang loading model awal
        cv2.putText(display_img, predicted_class_name, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)


    # Tampilkan status inferensi di layar
    if is_inferencing:
        cv2.putText(display_img, "Analyzing...", (460, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
        cv2.putText(display_img, "Analyzing...", (460, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Tampilkan video
    cv2.imshow("CCTV Deteksi Perkelahian (MViT)", display_img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
