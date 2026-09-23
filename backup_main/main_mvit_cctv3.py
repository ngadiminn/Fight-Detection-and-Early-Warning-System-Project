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
RTSP_URL = "rtsp://admin:Artyago_23@10.38.27.175:554/cam/realmonitor?channel=1&subtype=1" 
ESP32_IP = "http://10.38.27.95" 

# ==========================================
# KONFIGURASI TELEGRAM
# ==========================================
BOT_TOKEN = "8643840840:AAGjEYMFvXhGfmK0BUo2MRU8BUYsgSIH6Qo"
CHAT_ID = "2147060689"

# ==========================================
# KONFIGURASI MODEL
# ==========================================
MODEL_PATH = "mvit_fight_modelb4lr0001.pth"
SEQUENCE_LENGTH = 16
FRAME_SKIP = 2 # Mengekstrak 1 frame setiap 2 frame agar lebih efisien

# Variabel Global
status_terakhir = -1 
waktu_mulai_bahaya = 0      
telegram_terkirim = False   
predicted_class_name = "Loading..."
is_inferencing = False

# Menyimpan 50 data probabilitas terakhir untuk digambar jadi grafik
fight_prob_history = deque(maxlen=50) 

# ==========================================
# FUNGSI GAMBAR GRAFIK (HUD ala Game)
# ==========================================
def draw_probability_graph(img, history):
    """Fungsi untuk menggambar grafik garis dengan background PUTIH"""
    if len(history) < 2:
        return

    # Pengaturan ukuran dan posisi kotak grafik (Pojok kanan bawah)
    w, h = 300, 100
    x_offset = img.shape[1] - w - 40  # 30 px dari batas kanan
    y_offset = img.shape[0] - h - 20  # 20 px dari batas bawah

    # Gambar background PUTIH SOLID
    cv2.rectangle(img, (x_offset, y_offset), (x_offset + w, y_offset + h), (255, 255, 255), -1)
    
    # Border HITAM biar tegas
    cv2.rectangle(img, (x_offset, y_offset), (x_offset + w, y_offset + h), (0, 0, 0), 2)

    # Garis putus-putus untuk batas 50% (Threshold penentu perkelahian)
    y_50 = int(y_offset + h / 2)
    for x_dot in range(x_offset, x_offset + w, 10):
        cv2.line(img, (x_dot, y_50), (x_dot + 4, y_50), (150, 150, 150), 1)

    # Label Teks Keterangan Grafik (Warna Hitam)
    cv2.putText(img, "AI Fight Confidence", (x_offset + 10, y_offset + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    cv2.putText(img, "100%", (x_offset - 45, y_offset + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(img, " 50%", (x_offset - 45, y_50 + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(img, "  0%", (x_offset - 45, y_offset + h), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # KETERANGAN LEGENDA (Di pojok kanan atas grafik)
    cv2.putText(img, "Merah: Berkelahi", (x_offset + 190, y_offset + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 220), 1)
    cv2.putText(img, "Hijau: Aman", (x_offset + 190, y_offset + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 150, 0), 1)

    # Hitung jarak X antar titik di grafik
    step_x = w / (history.maxlen - 1)

    # Merangkai garis grafiknya dari masa lalu ke masa kini
    for i in range(1, len(history)):
        p1 = history[i-1]
        p2 = history[i]

        x1 = int(x_offset + (i-1) * step_x)
        y1 = int(y_offset + h - (p1 * h))

        x2 = int(x_offset + i * step_x)
        y2 = int(y_offset + h - (p2 * h))

        # Warna: Merah menyala jika yakin Fight (>50%), Hijau gelap jika aman (<50%)
        color = (0, 0, 255) if p2 >= 0.5 else (0, 180, 0) 
        thickness = 2 
        cv2.line(img, (x1, y1), (x2, y2), color, thickness)
        
        # Gambar titik indikator di ujung grafik paling terbaru
        if i == len(history) - 1:
            cv2.circle(img, (x2, y2), 4, color, -1)
            # Tulis angka persentase terakhir
            cv2.putText(img, f"{int(p2*100)}%", (x2 + 10, y2 + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

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
    """Mengirim Telegram dengan Programmatic Time Logging untuk mengukur latensi API"""
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
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=5)
        end_time = time.time()
        latensi_ms = (end_time - start_time) * 1000
        
        if response.status_code == 200:
            print(f"[{timestamp_str}] [TELEGRAM] Pesan peringatan SUKSES terkirim! ⚡")
            print(f" [LATENSI API] Waktu Tunda Transmisi Telegram: {latensi_ms:.2f} ms\n")
        else:
            print(f"[{timestamp_str}] [TELEGRAM ERROR] Gagal: {response.text}")
    except Exception as e:
        print(f"[{timestamp_str}] [TELEGRAM ERROR] Koneksi bermasalah: {e}")

# def run_inference_thread(frames, model):
#     """Menjalankan prediksi AI & merekam probabilitasnya di thread terpisah"""
#     global predicted_class_name, is_inferencing, fight_prob_history
#     try:
#         # Melakukan preprocessing manual agar bisa mengambil detail persentasenya
#         clips = []
#         transform = Fight_utils_mvit.transform_()
#         for frame in frames:
#             image = frame.copy()
#             frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
#             frame_transformed = transform(image=frame_rgb)['image']
#             clips.append(frame_transformed)
            
#         # Mengambil detail probabilitas
#         probs = Fight_utils_mvit.PredTopKProb(2, clips, model)
        
#         prob_fight = 0.0
#         for cls_name, p in probs:
#             if cls_name == "fight":
#                 prob_fight = p
#                 break
                
#         # Simpan persentase ke memori riwayat untuk digambar
#         fight_prob_history.append(prob_fight)
        
#         # Eksekusi penentuan nama kelas pemenang tunggal
#         predicted_class_name = Fight_utils_mvit.PredTopKClass(1, clips, model)
        
#     except Exception as e:
#         print(f"[INFERENCE ERROR] {e}")
#     finally:
#         is_inferencing = False

def run_inference_thread(frames, model):
    """Menjalankan prediksi AI & merekam probabilitasnya di thread terpisah"""
    global predicted_class_name, is_inferencing, fight_prob_history
    try:
        # Melakukan preprocessing manual agar bisa mengambil detail persentasenya
        clips = []
        transform = Fight_utils_mvit.transform_()
        for frame in frames:
            image = frame.copy()
            frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            frame_transformed = transform(image=frame_rgb)['image']
            clips.append(frame_transformed)
            
        # ---> 1. CATAT WAKTU PERSIS SEBELUM AI MIKIR DI SINI SAYANG <---
        waktu_mulai = time.time()
        
        # ---> 2. MODEL AI MULAI MENGEKSEKUSI DAN MENEBAK <---
        # Mengambil detail probabilitas
        probs = Fight_utils_mvit.PredTopKProb(2, clips, model)
        
        prob_fight = 0.0
        for cls_name, p in probs:
            if cls_name == "fight":
                prob_fight = p
                break
                
        # Simpan persentase ke memori riwayat untuk digambar
        fight_prob_history.append(prob_fight)
        
        # Eksekusi penentuan nama kelas pemenang tunggal
        predicted_class_name = Fight_utils_mvit.PredTopKClass(1, clips, model)
        
        # ---> 3. CATAT WAKTU PERSIS SETELAH AI SELESAI MIKIR <---
        waktu_selesai = time.time()
        
        # ---> 4. HITUNG DAN PRINT DURASI INFERENSI <---
        waktu_inferensi = waktu_selesai - waktu_mulai
        print(f"Waktu Inferensi: {waktu_inferensi:.4f} detik")
        
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

    # Resize untuk tampilan layar
    display_img = cv2.resize(img, (1024, 768))
    
    # Ambil frame untuk inferensi sesuai FRAME_SKIP
    if frame_counter % FRAME_SKIP == 0:
        frames_queue.append(img)
        
    frame_counter += 1

    # Mulai proses deteksi di background
    if len(frames_queue) == SEQUENCE_LENGTH and not is_inferencing:
        is_inferencing = True
        frames_list = list(frames_queue)
        threading.Thread(target=run_inference_thread, args=(frames_list, model)).start()

    # ==========================================
    # LOGIKA UTAMA (SINYAL ESP32 & DELAY 14 DETIK TELEGRAM)
    # ==========================================
    if predicted_class_name == "fight": 
        if status_terakhir != 1:
            timestamp_awal_bahaya = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            print(f"\n [TIMESTAMP TA] Bahaya Pertama Kali Terdeteksi & Dikirim ke ESP32: {timestamp_awal_bahaya}")
            print(">>> Memulai alarm ESP32 via background thread...")
            threading.Thread(target=tugas_ngirim_ke_esp, args=(1,)).start()
            
            status_terakhir = 1
            waktu_mulai_bahaya = time.time()
            telegram_terkirim = False        
            
        durasi_bahaya = time.time() - waktu_mulai_bahaya
        cv2.putText(display_img, f"PERKELAHIAN!! - Durasi: {int(durasi_bahaya)}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        if durasi_bahaya >= 14.0 and not telegram_terkirim:
            timestamp_awal_telegram = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            print(f" [TIMESTAMP TA] Telegram Pemicu Awal (Detik ke-14) pada: {timestamp_awal_telegram}")
            threading.Thread(target=tugas_ngirim_telegram).start()
            telegram_terkirim = True 
            
        if telegram_terkirim:
            cv2.putText(display_img, "TELEGRAM TERKIRIM!", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
    elif predicted_class_name == "noFight": 
        if status_terakhir != 0:
            print(">>> Kondisi Aman. Mematikan alarm ESP32 & reset timer...")
            threading.Thread(target=tugas_ngirim_ke_esp, args=(0,)).start()
            
            status_terakhir = 0
            waktu_mulai_bahaya = 0    
            telegram_terkirim = False 
            
        cv2.putText(display_img, "AMAN - No Fight", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    else:
        cv2.putText(display_img, predicted_class_name, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

    # Tampilkan status Menganalisa
    if is_inferencing:
        cv2.putText(display_img, "Analyzing...", (460, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
        cv2.putText(display_img, "Analyzing...", (460, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # ---> PANGGIL FUNGSI GAMBAR GRAFIK DI SINI <---
    draw_probability_graph(display_img, fight_prob_history)

    # Tampilkan video utuh
    cv2.imshow("CCTV Deteksi Perkelahian (MViT)", display_img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()