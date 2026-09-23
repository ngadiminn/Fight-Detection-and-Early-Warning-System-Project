import cv2
import mediapipe as mp
import requests
import time
import threading # <-- Ini pahlawan kita hari ini

# ==========================================
# KONFIGURASI
# ==========================================
RTSP_URL = "rtsp://admin:Artyago_23@192.168.1.20:554/cam/realmonitor?channel=1&subtype=1" # Sesuaikan lagi ya
ESP32_IP = "http://192.168.1.23" 

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

status_terakhir = -1 

# --- FUNGSI BARU UNTUK JALUR BELAKANG (THREAD) ---
def tugas_ngirim_ke_esp(status_dikirim):
    url = f"{ESP32_IP}/sinyal?status={status_dikirim}"
    try:
        response = requests.get(url, timeout=2)
        print(f"[THREAD] Sinyal '{status_dikirim}' terkirim! Balasan: {response.text}")
    except Exception as e:
        print(f"[THREAD ERROR] Gagal konek ke ESP32: {e}")

def kirim_sinyal_tanpa_lag(status):
    """Fungsi ini cuma ngasih perintah ke jalur belakang, jadi video nggak nungguin"""
    global status_terakhir
    
    if status != status_terakhir:
        print(f">>> Memicu pengiriman sinyal '{status}' di background...")
        # Bikin "pekerja" baru untuk ngirim data tanpa menghentikan video
        pekerja = threading.Thread(target=tugas_ngirim_ke_esp, args=(status,))
        pekerja.start() # Suruh pekerjanya jalan sekarang
        
        status_terakhir = status

# ==========================================
# BUKA KAMERA RTSP
# ==========================================
print(f"Mencoba menyambung ke IP Cam...")
cap = cv2.VideoCapture(RTSP_URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 2) # Trik OpenCV: Kecilin buffer biar video selalu live

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

    if results.multi_hand_landmarks:
        for handLms in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)
            
            jari_terbuka = 0
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

            # Panggil fungsi yang baru (Tanpa Lag)
            if jari_terbuka >= 4:
                cv2.putText(img, "BAHAYA (1) - Tangan Terbuka", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                kirim_sinyal_tanpa_lag(1)
            
            elif jari_terbuka == 0:
                cv2.putText(img, "AMAN (0) - Mengepal", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                kirim_sinyal_tanpa_lag(0)

    cv2.imshow("CCTV Deteksi Tangan (RTSP)", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()