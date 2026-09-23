import cv2
import mediapipe as mp
import requests
import time

# ==========================================
# KONFIGURASI JARINGAN
# ==========================================
# Masukkan IP Camera RTSP kamu. 
# Catatan: Kadang RTSP butuh tambahan port/path, contoh: "rtsp://192.168.1.23:554/stream1"
RTSP_URL = "rtsp://admin:Artyago_23@10.47.187.175:554/cam/realmonitor?channel=1&subtype=1" 

# IP ESP32 kamu (sesuaikan kalau berubah)
ESP32_IP = "http://192.168.1.20" 

# ==========================================
# SETUP MEDIAPIPE (Pendeteksi Tangan)
# ==========================================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Variabel Anti-Spam (Biar ESP32 nggak meledak nerima sinyal beruntun)
status_terakhir = -1 

def kirim_sinyal(status):
    """Kirim perintah HTTP ke ESP32 hanya jika statusnya berubah"""
    global status_terakhir
    
    if status != status_terakhir:
        url = f"{ESP32_IP}/sinyal?status={status}"
        try:
            print(f">>> Mengirim sinyal '{status}' ke ESP32...")
            response = requests.get(url, timeout=2) # Timeout cepat 2 detik
            print(f"    Balasan: {response.text}\n")
            status_terakhir = status
        except Exception as e:
            print(f"[ERROR] Gagal konek ke ESP32: {e}")

# ==========================================
# BUKA KAMERA RTSP
# ==========================================
print(f"Mencoba menyambung ke IP Cam: {RTSP_URL}...")
cap = cv2.VideoCapture(RTSP_URL)

if not cap.isOpened():
    print("[ERROR] Gagal membuka stream RTSP. Cek koneksi jaringan atau URL IP Cam kamu!")
    exit()

print("Kamera terhubung! Tekan huruf 'q' di jendela video untuk keluar.")

while True:
    success, img = cap.read()
    if not success:
        print("Menunggu frame dari IP Cam...")
        time.sleep(0.5)
        continue

    # Resize gambar biar komputernya nggak ngos-ngosan baca IP Cam resolusi tinggi
    img = cv2.resize(img, (640, 480))
    
    # MediaPipe mintanya warna RGB, sedangkan OpenCV pakai BGR
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    if results.multi_hand_landmarks:
        for handLms in results.multi_hand_landmarks:
            # Gambar kerangka tangan di layar biar keren
            mp_draw.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)
            
            # --- LOGIKA MENGHITUNG JARI TERBUKA ---
            jari_terbuka = 0
            tipIds = [4, 8, 12, 16, 20] # Index ujung jari: Jempol, Telunjuk, Tengah, Manis, Kelingking
            lmList = []
            
            for id, lm in enumerate(handLms.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lmList.append([id, cx, cy])

            if len(lmList) != 0:
                # Cek Jempol (Bandingkan posisi X)
                if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]:
                    jari_terbuka += 1
                
                # Cek 4 Jari lainnya (Bandingkan posisi Y ujung jari dengan buku jari bawahnya)
                for id in range(1, 5):
                    if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]:
                        jari_terbuka += 1

            # --- EKSEKUSI SINYAL ---
            # Jika minimal 4 jari terbuka -> TANGAN TERBUKA -> KIRIM 1
            if jari_terbuka >= 4:
                cv2.putText(img, "BAHAYA (1) - Tangan Terbuka", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                kirim_sinyal(1)
            
            # Jika 0 jari terbuka -> MENGEPAL -> KIRIM 0
            elif jari_terbuka == 0:
                cv2.putText(img, "AMAN (0) - Mengepal", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                kirim_sinyal(0)

    # Tampilkan video
    cv2.imshow("CCTV Deteksi Tangan (RTSP)", img)

    # Tekan 'q' untuk berhenti
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()