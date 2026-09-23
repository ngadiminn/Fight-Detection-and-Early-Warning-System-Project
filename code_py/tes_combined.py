import cv2
import mediapipe as mp
import requests
import time
import threading
import datetime

# ==========================================
# KONFIGURASI ALAMAT (Cek IP lagi ya biar nggak ketuker)
# ==========================================
# IP Camera RTSP
RTSP_URL = "rtsp://admin:Artyago_23@192.168.1.20:554/cam/realmonitor?channel=1&subtype=1" 
# IP ESP32
ESP32_IP = "http://192.168.1.23" 

# ==========================================
# KONFIGURASI TELEGRAM
# ==========================================
BOT_TOKEN = "8643840840:AAGjEYMFvXhGfmK0BUo2MRU8BUYsgSIH6Qo"
CHAT_ID = "2147060689"

# ==========================================
# SETUP MEDIAPIPE & VARIABEL LOGIKA
# ==========================================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

status_terakhir = -1 
waktu_mulai_bahaya = 0      # Mencatat kapan sinyal '1' pertama kali muncul
telegram_terkirim = False   # Mencegah Telegram spam berkali-kali

# ==========================================
# FUNGSI JALUR BELAKANG (THREADING)
# ==========================================
def tugas_ngirim_ke_esp(status_dikirim):
    """Mengirim perintah ke ESP32 tanpa bikin video patah-patah"""
    url = f"{ESP32_IP}/sinyal?status={status_dikirim}"
    try:
        response = requests.get(url, timeout=2)
        print(f"[ESP32] Sinyal '{status_dikirim}' terkirim! Balasan: {response.text}")
    except Exception as e:
        print(f"[ESP32 ERROR] Gagal konek: {e}")

def tugas_ngirim_telegram():
    """Mengirim Telegram pakai API resmi tanpa bikin video ngelag"""
    sekarang = datetime.datetime.now()
    waktu_str = sekarang.strftime("%H:%M:%S WIB")
    bulan_indo = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                  "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    tanggal_str = f"{sekarang.day:02d} {bulan_indo[sekarang.month]} {sekarang.year}"
    
    pesan = (
        "⚠️ *EMERGENCY ALERT*\n\n"
        "Telah terdeteksi indikasi perkelahian!\n"
        "📍 Lokasi: Ruang Kelas TULT 14.09\n"
        f"🕒 Waktu: {waktu_str}\n"
        f"📅 Tanggal: {tanggal_str}\n\n"
        "Tindakan output fisik alarm & lampu telah diaktifkan. Harap segera lakukan intervensi."
    )
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    
    try:
        print("\n[TELEGRAM] Memproses pengiriman pesan...")
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("[TELEGRAM] Pesan peringatan SUKSES terkirim! ⚡\n")
        else:
            print(f"[TELEGRAM ERROR] Gagal: {response.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] Koneksi bermasalah: {e}")

# ==========================================
# BUKA KAMERA RTSP
# ==========================================
print("Mencoba menyambung ke IP Cam...")
cap = cv2.VideoCapture(RTSP_URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 2) 

if not cap.isOpened():
    print("[ERROR] Gagal membuka stream RTSP.")
    exit()

print("Kamera terhubung! Tekan huruf 'q' di jendela video untuk keluar.")

while True:
    success, img = cap.read()
    if not success:
        time.sleep(0.1)
        continue

    img = cv2.resize(img, (640, 480))
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    jari_terbuka = 0 # Default

    if results.multi_hand_landmarks:
        for handLms in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)
            
            tipIds = [4, 8, 12, 16, 20]
            lmList = []
            
            for id, lm in enumerate(handLms.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lmList.append([id, cx, cy])

            if len(lmList) != 0:
                if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]:
                    jari_terbuka += 1
                for id in range(1, 5):
                    if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]:
                        jari_terbuka += 1

    # ==========================================
    # LOGIKA UTAMA (SINYAL ESP32 & DELAY 20 DETIK TELEGRAM)
    # ==========================================
    if jari_terbuka >= 4: # TANGAN TERBUKA -> BAHAYA (1)
        
        # Jika baru pertama kali mendeteksi bahaya
        if status_terakhir != 1:
            print(">>> Bahaya terdeteksi! Memulai alarm ESP32...")
            threading.Thread(target=tugas_ngirim_ke_esp, args=(1,)).start()
            
            status_terakhir = 1
            waktu_mulai_bahaya = time.time() # Mulai nyalakan stopwatch
            telegram_terkirim = False        # Reset status telegram
            
        # Hitung durasi bahaya yang sedang berlangsung
        durasi_bahaya = time.time() - waktu_mulai_bahaya
        
        # Tampilkan teks timer di layar
        cv2.putText(img, f"BAHAYA (1) - Durasi: {int(durasi_bahaya)}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        # Cek apakah durasi sudah tembus 20 detik dan telegram belum terkirim
        if durasi_bahaya >= 20.0 and not telegram_terkirim:
            threading.Thread(target=tugas_ngirim_telegram).start()
            telegram_terkirim = True # Kunci agar tidak spam berkali-kali
            
        # Tampilkan notif di layar kalau Telegram udah kekirim
        if telegram_terkirim:
            cv2.putText(img, "TELEGRAM TERKIRIM!", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
    elif jari_terbuka == 0: # TANGAN MENGEPAL -> AMAN (0)
        
        # Jika baru pertama kali mendeteksi aman
        if status_terakhir != 0:
            print(">>> Kondisi Aman. Mematikan alarm ESP32 & reset timer...")
            threading.Thread(target=tugas_ngirim_ke_esp, args=(0,)).start()
            
            status_terakhir = 0
            waktu_mulai_bahaya = 0    # Reset stopwatch
            telegram_terkirim = False # Reset status telegram
            
        cv2.putText(img, "AMAN (0) - Mengepal", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

    # Tampilkan video
    cv2.imshow("CCTV Deteksi Tangan (RTSP)", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()