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
RTSP_URL = "rtsp://admin:Artyago_23@10.196.207.175:554/cam/realmonitor?channel=1&subtype=1" 
ESP32_IP = "http://10.196.207.95" 

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
FRAME_SKIP = 2 

# ==========================================
# VARIABEL GLOBAL & LOGIKA BUFFER WAKTU
# ==========================================
status_terakhir = 0         # 0 = Aman, 1 = Event Bahaya Sedang Berlangsung
status_esp_sekarang = 0     # Mencatat sinyal terakhir yang dikirim ke ESP (0,1,2,3)
waktu_mulai_bahaya = 0      # Kapan perkelahian pertama kali pecah
waktu_terakhir_bahaya = 0   # Kapan AI terakhir kali melihat gerakan perkelahian
telegram_terkirim = False   
predicted_class_name = "Loading..."
is_inferencing = False

# FITUR JEDA: Berapa lama sistem "menunggu" sebelum mereset total perkelahian
BATAS_JEDA_AMAN = 7.0  # 7 Detik 

fight_prob_history = deque(maxlen=50) 

# ==========================================
# FUNGSI GAMBAR GRAFIK (HUD ala Game)
# ==========================================
def draw_probability_graph(img, history):
    if len(history) < 2:
        return

    w, h = 300, 100
    x_offset = img.shape[1] - w - 40  
    y_offset = img.shape[0] - h - 20  

    cv2.rectangle(img, (x_offset, y_offset), (x_offset + w, y_offset + h), (255, 255, 255), -1)
    cv2.rectangle(img, (x_offset, y_offset), (x_offset + w, y_offset + h), (0, 0, 0), 2)

    y_50 = int(y_offset + h / 2)
    for x_dot in range(x_offset, x_offset + w, 10):
        cv2.line(img, (x_dot, y_50), (x_dot + 4, y_50), (150, 150, 150), 1)

    cv2.putText(img, "AI Fight Confidence", (x_offset + 10, y_offset + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    cv2.putText(img, "100%", (x_offset - 45, y_offset + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(img, " 50%", (x_offset - 45, y_50 + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(img, "  0%", (x_offset - 45, y_offset + h), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    cv2.putText(img, "Merah: Berkelahi", (x_offset + 190, y_offset + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 220), 1)
    cv2.putText(img, "Hijau: Aman", (x_offset + 190, y_offset + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 150, 0), 1)

    step_x = w / (history.maxlen - 1)

    for i in range(1, len(history)):
        p1 = history[i-1]
        p2 = history[i]

        x1 = int(x_offset + (i-1) * step_x)
        y1 = int(y_offset + h - (p1 * h))

        x2 = int(x_offset + i * step_x)
        y2 = int(y_offset + h - (p2 * h))

        color = (0, 0, 255) if p2 >= 0.5 else (0, 180, 0) 
        thickness = 2 
        cv2.line(img, (x1, y1), (x2, y2), color, thickness)
        
        if i == len(history) - 1:
            cv2.circle(img, (x2, y2), 4, color, -1)
            cv2.putText(img, f"{int(p2*100)}%", (x2 + 10, y2 + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

# ==========================================
# FUNGSI JALUR BELAKANG (THREADING)
# ==========================================
def tugas_ngirim_ke_esp(status_dikirim):
    sekarang = datetime.datetime.now()
    timestamp_str = sekarang.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    url = f"{ESP32_IP}/sinyal"
    params = {
        "status": status_dikirim,
        "timestamp": timestamp_str
    }
    try:
        response = requests.get(url, params=params, timeout=2)
        print(f"[{timestamp_str}] [ESP32] Skenario '{status_dikirim}' terkirim! Balasan: {response.text}")
    except Exception as e:
        print(f"[{timestamp_str}] [ESP32 ERROR] Gagal konek: {e}")

def tugas_ngirim_telegram():
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
            print(f"⏱️ [LATENSI API] Waktu Tunda Transmisi Telegram: {latensi_ms:.2f} ms\n")
        else:
            print(f"[{timestamp_str}] [TELEGRAM ERROR] Gagal: {response.text}")
    except Exception as e:
        print(f"[{timestamp_str}] [TELEGRAM ERROR] Koneksi bermasalah: {e}")

def run_inference_thread(frames, model):
    global predicted_class_name, is_inferencing, fight_prob_history
    try:
        clips = []
        transform = Fight_utils_mvit.transform_()
        for frame in frames:
            image = frame.copy()
            frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            frame_transformed = transform(image=frame_rgb)['image']
            clips.append(frame_transformed)
            
        waktu_mulai = time.time()
        
        probs = Fight_utils_mvit.PredTopKProb(2, clips, model)
        
        prob_fight = 0.0
        for cls_name, p in probs:
            if cls_name == "fight":
                prob_fight = p
                break
                
        fight_prob_history.append(prob_fight)
        predicted_class_name = Fight_utils_mvit.PredTopKClass(1, clips, model)
        
        waktu_selesai = time.time()
        waktu_inferensi = waktu_selesai - waktu_mulai
        print(f"Waktu Inferensi AI: {waktu_inferensi:.4f} detik")
        
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

    display_img = cv2.resize(img, (1024, 768))
    
    if frame_counter % FRAME_SKIP == 0:
        frames_queue.append(img)
        
    frame_counter += 1

    if len(frames_queue) == SEQUENCE_LENGTH and not is_inferencing:
        is_inferencing = True
        frames_list = list(frames_queue)
        threading.Thread(target=run_inference_thread, args=(frames_list, model)).start()

    # ==========================================
    # LOGIKA UTAMA (SISTEM SKENARIO & BUFFER WAKTU AMAN)
    # ==========================================
    waktu_sekarang = time.time()

    # 1. Kalau AI ngelihat berantem, perbarui terus catatannya
    if predicted_class_name == "fight": 
        waktu_terakhir_bahaya = waktu_sekarang
        
        # Kalau sebelumnya lagi bener-bener aman (status 0), mulai event perkelahian baru
        if status_terakhir == 0:
            status_terakhir = 1
            waktu_mulai_bahaya = waktu_sekarang
            telegram_terkirim = False        
            
    # 2. Logika Eskalasi Skenario & Jeda
    if status_terakhir == 1:
        jeda_waktu = waktu_sekarang - waktu_terakhir_bahaya
        
        # --- KONDISI A: AI MENDETEKSI PERKELAHIAN SAAT INI ---
        if predicted_class_name == "fight":
            durasi_bahaya = waktu_sekarang - waktu_mulai_bahaya
            cv2.putText(display_img, f"PERKELAHIAN!! - Durasi: {int(durasi_bahaya)}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            
            # Penentuan Level Alarm
            target_skenario = 1 # Default saat baru mulai berantem
            if durasi_bahaya >= 12.0:
                target_skenario = 3 # > 12s (Strobo + Voice)
            elif durasi_bahaya >= 5.0:
                target_skenario = 2 # > 5s (Strobo + Sirine)
                
            # Nyalakan ESP32 sesuai target skenario
            if status_esp_sekarang != target_skenario:
                print(f">>> Eskalasi! Mengirim perintah Skenario {target_skenario} ke ESP32...")
                threading.Thread(target=tugas_ngirim_ke_esp, args=(target_skenario,)).start()
                status_esp_sekarang = target_skenario
            
            # Kirim Telegram
            if durasi_bahaya >= 14.0 and not telegram_terkirim:
                timestamp_awal_telegram = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                print(f"\n🚨 [TIMESTAMP TA] Telegram Pemicu Awal (Detik ke-14) pada: {timestamp_awal_telegram}")
                threading.Thread(target=tugas_ngirim_telegram).start()
                telegram_terkirim = True 
                
            if telegram_terkirim:
                cv2.putText(display_img, "TELEGRAM TERKIRIM!", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                
        # --- KONDISI B: JEDA AMAN (BELUM LEWAT BATAS) ---
        elif jeda_waktu <= BATAS_JEDA_AMAN:
            durasi_bahaya = waktu_sekarang - waktu_mulai_bahaya
            cv2.putText(display_img, f"MENCURIGAKAN! (Jeda) - Durasi: {int(durasi_bahaya)}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 3)
            
            # MATIKAN ALARM ESP32 SEMENTARA (Skenario 0) TAPI TIMER TETAP JALAN
            target_skenario = 0
            if status_esp_sekarang != target_skenario:
                print(">>> Jeda Sementara. Mematikan alarm ESP32...")
                threading.Thread(target=tugas_ngirim_ke_esp, args=(target_skenario,)).start()
                status_esp_sekarang = target_skenario
                
        # --- KONDISI C: BENAR-BENAR AMAN (LEWAT BATAS) ---
        else:
            print(">>> Jeda terlewati. Kondisi Benar-benar Aman. Reset sistem...")
            
            # Pastikan ESP32 sudah dimatikan
            target_skenario = 0
            if status_esp_sekarang != target_skenario:
                threading.Thread(target=tugas_ngirim_ke_esp, args=(target_skenario,)).start()
                status_esp_sekarang = target_skenario
                
            status_terakhir = 0
            waktu_mulai_bahaya = 0    
            telegram_terkirim = False 
            
    # 3. Kalo status_terakhir udah bener-bener aman (0)
    elif status_terakhir == 0:
        cv2.putText(display_img, "AMAN - No Fight", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

    if is_inferencing:
        cv2.putText(display_img, "Analyzing...", (460, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
        cv2.putText(display_img, "Analyzing...", (460, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    draw_probability_graph(display_img, fight_prob_history)

    cv2.imshow("CCTV Deteksi Perkelahian (MViT)", display_img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()