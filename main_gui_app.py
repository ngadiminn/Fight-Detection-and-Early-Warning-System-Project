import cv2
import requests
import time
import threading
import datetime
import os
import numpy as np
from collections import deque
import Fight_utils_mvit
import customtkinter as ctk
from PIL import Image, ImageTk

# ==========================================
# KONFIGURASI ALAMAT & TELEGRAM
# ==========================================
RTSP_URL = "rtsp://admin:Artyago_23@10.168.9.175:554/cam/realmonitor?channel=1&subtype=1" 
ESP32_IP = "http://10.168.9.95" 
BOT_TOKEN = "8643840840:AAGjEYMFvXhGfmK0BUo2MRU8BUYsgSIH6Qo"
CHAT_ID = "-5326497556"
MODEL_PATH = "models/mvit_fight_modelb4lr0001.pth"
SEQUENCE_LENGTH = 16
FRAME_SKIP = 2 

# Bikin folder lokal buat nyimpen Auto-Capture
if not os.path.exists("History_Capture"):
    os.makedirs("History_Capture")

# ==========================================
# INISIALISASI TEMA APLIKASI
# ==========================================
ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue") 

# ==========================================
# KELAS UTAMA APLIKASI
# ==========================================
class MandorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Fight Detection App")
        self.geometry("1300x850")
        
        # Variabel Status Sistem (Otak AI)
        self.status_terakhir = 0
        self.status_esp_sekarang = 0
        self.waktu_mulai_bahaya = 0
        self.waktu_terakhir_bahaya = 0
        self.telegram_terkirim = False
        self.capture_tersimpan = False
        self.predicted_class_name = "Loading..."
        self.is_inferencing = False
        self.fight_prob_history = deque(maxlen=50)
        self.is_running = False
        self.last_capture_path = "" # Mengingat foto terakhir yang disimpan
        
        # Membangun Tampilan (UI)
        self.build_ui()

    def build_ui(self):
        # Frame Kiri untuk Video CCTV
        self.video_frame = ctk.CTkFrame(self, corner_radius=10)
        self.video_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        self.video_label = ctk.CTkLabel(self.video_frame, text="Kamera Mati. Tekan 'Start System'.")
        self.video_label.pack(fill="both", expand=True)

        # Frame Kanan untuk Panel Kontrol & Log
        self.panel_frame = ctk.CTkFrame(self, width=350, corner_radius=10)
        self.panel_frame.pack(side="right", fill="y", padx=10, pady=10)
        self.panel_frame.pack_propagate(False) # Kunci ukuran lebarnya

        # Judul Panel
        ctk.CTkLabel(self.panel_frame, text="⚙️ Panel Pengaturan", font=("Arial", 16, "bold")).pack(pady=10)

        # --- KONFIGURASI WAKTU (BISA DIATUR USER) ---
        self.atur_frame = ctk.CTkFrame(self.panel_frame, fg_color="transparent")
        self.atur_frame.pack(fill="x", padx=10, pady=5)

        self.input_jeda = self.buat_kolom_input("Batas Jeda Deteksi (detik):", "4.0")
        self.input_s2 = self.buat_kolom_input("Mulai Sirine (detik ke-):", "5.0")
        self.input_s3 = self.buat_kolom_input("Mulai Voice (detik ke-):", "12.0")
        self.input_capture = self.buat_kolom_input("Auto Capture (detik ke-):", "2.0") 
        self.input_tele = self.buat_kolom_input("Kirim Telegram (detik ke-):", "14.0")

        # --- GRAFIK CONFIDENCE (DIPINDAH KE PANEL KANAN) ---
        ctk.CTkLabel(self.panel_frame, text="Grafik AI Confidence", font=("Arial", 14, "bold")).pack(pady=(15, 0))
        self.graph_label = ctk.CTkLabel(self.panel_frame, text="Menunggu data AI...")
        self.graph_label.pack(pady=5)

        # --- LOG HISTORY ---
        ctk.CTkLabel(self.panel_frame, text="📃 Log History", font=("Arial", 14, "bold")).pack(pady=(15, 5))
        self.log_box = ctk.CTkTextbox(self.panel_frame, height=200, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TOMBOL KONTROL ---
        self.btn_start = ctk.CTkButton(self.panel_frame, text="▶ Start System", fg_color="green", hover_color="darkgreen", command=self.start_system)
        self.btn_start.pack(fill="x", padx=10, pady=(15, 5))

        self.btn_stop = ctk.CTkButton(self.panel_frame, text="⏹ Stop System", fg_color="red", hover_color="darkred", state="disabled", command=self.stop_system)
        self.btn_stop.pack(fill="x", padx=10, pady=5)
        
        self.tambah_log("Sistem Siap. Menunggu instruksi Start.")

    def buat_kolom_input(self, label_text, default_val):
        frame = ctk.CTkFrame(self.atur_frame, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        ctk.CTkLabel(frame, text=label_text, font=("Arial", 12)).pack(side="left")
        entry = ctk.CTkEntry(frame, width=50)
        entry.pack(side="right")
        entry.insert(0, default_val)
        return entry

    def tambah_log(self, pesan):
        waktu_sekarang = datetime.datetime.now().strftime("%H:%M:%S")
        pesan_format = f"[{waktu_sekarang}] {pesan}\n"
        
        self.log_box.configure(state="normal")
        self.log_box.insert("end", pesan_format)
        self.log_box.see("end") 
        self.log_box.configure(state="disabled")

    # ==========================================
    # FUNGSI PEMBUAT TEKS OUTLINE HITAM DENGAN WARNA CUSTOM
    # ==========================================
    def gambar_teks_outline(self, img, teks, posisi, font_scale=1.0, tebal_outline=4, tebal_teks=2, warna_teks=(255, 255, 255)):
        # Bikin outline hitam dulu
        cv2.putText(img, teks, posisi, cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), tebal_outline)
        # Tumpuk dengan teks berwarna (format warna OpenCV adalah BGR, bukan RGB)
        cv2.putText(img, teks, posisi, cv2.FONT_HERSHEY_SIMPLEX, font_scale, warna_teks, tebal_teks)

    # ==========================================
    # FUNGSI PEMBUAT GAMBAR GRAFIK TERPISAH
    # ==========================================
    def get_graph_image(self, history):
        w, h = 300, 100
        img = np.ones((h + 30, w + 20, 3), dtype=np.uint8) * 255 
        
        cv2.rectangle(img, (5, 5), (w + 15, h + 25), (0, 0, 0), 2)

        if len(history) < 2:
            cv2.putText(img, "Menunggu data AI...", (80, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            return img

        x_offset = 10
        y_offset = 15
        y_50 = int(y_offset + h / 2)
        
        for x_dot in range(x_offset, x_offset + w, 10):
            cv2.line(img, (x_dot, y_50), (x_dot + 4, y_50), (150, 150, 150), 1)

        cv2.putText(img, "100%", (x_offset + 5, y_offset + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
        cv2.putText(img, "50%", (x_offset + 5, y_50 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
        cv2.putText(img, "0%", (x_offset + 5, y_offset + h - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)

        cv2.putText(img, "Merah: Berkelahi", (x_offset + 190, y_offset + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 220), 1)
        cv2.putText(img, "Hijau: Aman", (x_offset + 190, y_offset + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 150, 0), 1)

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
                cv2.putText(img, f"{int(p2*100)}%", (x2 - 15, y2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 2)
                
        return img

    # ==========================================
    # LOGIKA THREADING & KONEKSI
    # ==========================================
    def tugas_ngirim_ke_esp(self, status_dikirim):
        url = f"{ESP32_IP}/sinyal"
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        params = {"status": status_dikirim, "timestamp": timestamp_str}
        try:
            requests.get(url, params=params, timeout=2)
            teks_log = f"ESP32 Aktif: Skenario {status_dikirim}" if status_dikirim > 0 else "ESP32: Kondisi Aman (0)"
            self.after(0, lambda: self.tambah_log("📡 " + teks_log))
        except Exception as e:
            self.after(0, lambda: self.tambah_log(f"❌ Error ESP32: Gagal konek!"))

    def tugas_ngirim_telegram(self, photo_path=""):
        self.after(0, lambda: self.tambah_log("🚀 Mengirim peringatan & FOTO ke Telegram..."))
        
        # --- FORMAT TANGGAL & WAKTU ALAMATNYA DIKEMBALIKAN! ---
        sekarang = datetime.datetime.now()
        waktu_str = sekarang.strftime("%H:%M:%S WIB")
        bulan_indo = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                      "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        tanggal_str = f"{sekarang.day:02d} {bulan_indo[sekarang.month]} {sekarang.year}"
        
        pesan = (
            "⚠️ *EMERGENCY ALERT*\n\n"
            "Telah terdeteksi indikasi perkelahian!\n"
            "📍 Lokasi: Ruang Laboratorium P304\n"
            f"🕒 Waktu: {waktu_str}\n"
            f"📅 Tanggal: {tanggal_str}\n\n"
            "Tindakan output fisik alarm & lampu telah diaktifkan. Harap segera lakukan intervensi."
        )
        
        try:
            start_time = time.time()
            
            # Kalau file fotonya ada, kirim fotonya sekalian
            if photo_path and os.path.exists(photo_path):
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                data = {"chat_id": CHAT_ID, "caption": pesan, "parse_mode": "Markdown"}
                with open(photo_path, "rb") as image_file:
                    files = {"photo": image_file}
                    response = requests.post(url, data=data, files=files, timeout=15)
            else:
                # Kalau gagal dapet foto, fallback kirim teks biasa
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
                response = requests.post(url, json=payload, timeout=10)
                
            end_time = time.time()
            latensi_ms = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                self.after(0, lambda: self.tambah_log("✅ Peringatan Telegram sukses terkirim!"))
            else:
                self.after(0, lambda: self.tambah_log(f"❌ Error Telegram: {response.text}"))
        except Exception as e:
            self.after(0, lambda: self.tambah_log("❌ Error Telegram: Koneksi bermasalah!"))

    def run_inference_thread(self, frames, model):
        try:
            clips = []
            transform = Fight_utils_mvit.transform_()
            for frame in frames:
                image = frame.copy()
                frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                clips.append(transform(image=frame_rgb)['image'])
                
            probs = Fight_utils_mvit.PredTopKProb(2, clips, model)
            prob_fight = 0.0
            for cls_name, p in probs:
                if cls_name == "fight":
                    prob_fight = p
                    break
                    
            self.fight_prob_history.append(prob_fight)
            self.predicted_class_name = Fight_utils_mvit.PredTopKClass(1, clips, model)
        except Exception as e:
            print(f"[ERROR AI] {e}")
        finally:
            self.is_inferencing = False

    # ==========================================
    # LOGIKA UTAMA (KAMERA & DETEKSI)
    # ==========================================
    def start_system(self):
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.is_running = True
        self.tambah_log("Mempersiapkan Model AI & Kamera...")
        threading.Thread(target=self.kamera_loop, daemon=True).start()

    def stop_system(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.tambah_log("Sistem dihentikan pengguna.")
        if self.status_esp_sekarang != 0:
            threading.Thread(target=self.tugas_ngirim_ke_esp, args=(0,)).start()

    def kamera_loop(self):
        model = Fight_utils_mvit.loadModel(MODEL_PATH)
        self.after(0, lambda: self.tambah_log("Model MViT berhasil dimuat!"))

        cap = cv2.VideoCapture(RTSP_URL)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2) 
        
        if not cap.isOpened():
            self.after(0, lambda: self.tambah_log("❌ Gagal membuka CCTV RTSP!"))
            return

        self.after(0, lambda: self.tambah_log("✅ CCTV Terhubung. Memulai pantauan..."))
        frames_queue = deque(maxlen=SEQUENCE_LENGTH)
        frame_counter = 0

        while self.is_running:
            success, img = cap.read()
            if not success:
                time.sleep(0.1)
                continue

            display_img = cv2.resize(img, (800, 600))
            gambar_murni_buat_capture = img.copy() 
            
            if frame_counter % FRAME_SKIP == 0:
                frames_queue.append(img)
            frame_counter += 1

            if len(frames_queue) == SEQUENCE_LENGTH and not self.is_inferencing:
                self.is_inferencing = True
                threading.Thread(target=self.run_inference_thread, args=(list(frames_queue), model)).start()

            try:
                batas_jeda = float(self.input_jeda.get())
                batas_s2 = float(self.input_s2.get())
                batas_s3 = float(self.input_s3.get())
                batas_cap = float(self.input_capture.get())
                batas_tele = float(self.input_tele.get())
            except:
                batas_jeda, batas_s2, batas_s3, batas_cap, batas_tele = 4.0, 5.0, 12.0, 2.0, 14.0 

            waktu_sekarang = time.time()

            if self.predicted_class_name == "fight": 
                self.waktu_terakhir_bahaya = waktu_sekarang
                if self.status_terakhir == 0:
                    self.status_terakhir = 1
                    self.waktu_mulai_bahaya = waktu_sekarang
                    self.telegram_terkirim = False
                    self.capture_tersimpan = False
                    self.after(0, lambda: self.tambah_log("⚠️ ALERT: Indikasi Perkelahian Dimulai!"))
                    
            if self.status_terakhir == 1:
                jeda_waktu = waktu_sekarang - self.waktu_terakhir_bahaya
                
                if self.predicted_class_name == "fight":
                    durasi_bahaya = waktu_sekarang - self.waktu_mulai_bahaya
                    # Warna BGR: (0, 0, 255) = Merah
                    self.gambar_teks_outline(display_img, f"PERKELAHIAN!! - Durasi: {int(durasi_bahaya)}s", (20, 50), warna_teks=(0, 0, 255))
                    
                    if durasi_bahaya >= batas_cap and not self.capture_tersimpan:
                        nama_file = f"History_Capture/Fight_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        cv2.imwrite(nama_file, gambar_murni_buat_capture)
                        self.last_capture_path = nama_file  
                        self.capture_tersimpan = True
                        self.after(0, lambda: self.tambah_log(f"📸 Auto-Capture tersimpan di folder lokal."))

                    target_skenario = 1 
                    if durasi_bahaya >= batas_s3: target_skenario = 3 
                    elif durasi_bahaya >= batas_s2: target_skenario = 2 
                        
                    if self.status_esp_sekarang != target_skenario:
                        threading.Thread(target=self.tugas_ngirim_ke_esp, args=(target_skenario,)).start()
                        self.status_esp_sekarang = target_skenario
                    
                    if durasi_bahaya >= batas_tele and not self.telegram_terkirim:
                        threading.Thread(target=self.tugas_ngirim_telegram, args=(self.last_capture_path,)).start()
                        self.telegram_terkirim = True 
                        
                elif jeda_waktu <= batas_jeda:
                    durasi_bahaya = waktu_sekarang - self.waktu_mulai_bahaya
                    # Warna BGR: (0, 165, 255) = Oranye untuk peringatan jeda
                    self.gambar_teks_outline(display_img, f"JEDA DETEKSI - Tahan: {int(durasi_bahaya)}s", (20, 50), warna_teks=(0, 165, 255))
                    
                    target_skenario = 0
                    if self.status_esp_sekarang != target_skenario:
                        threading.Thread(target=self.tugas_ngirim_ke_esp, args=(target_skenario,)).start()
                        self.status_esp_sekarang = target_skenario
                        
                else:
                    self.after(0, lambda: self.tambah_log("🟢 Situasi kembali kondusif (Aman)."))
                    target_skenario = 0
                    if self.status_esp_sekarang != target_skenario:
                        threading.Thread(target=self.tugas_ngirim_ke_esp, args=(target_skenario,)).start()
                        self.status_esp_sekarang = target_skenario
                        
                    self.status_terakhir = 0
                    self.waktu_mulai_bahaya = 0    
                    self.telegram_terkirim = False 
                    self.capture_tersimpan = False
                    
            elif self.status_terakhir == 0:
                # Warna BGR: (0, 255, 0) = Hijau
                self.gambar_teks_outline(display_img, "AMAN - No Fight", (20, 50), warna_teks=(0, 255, 0))

            if self.telegram_terkirim and self.status_terakhir == 1:
                # Warna BGR: (0, 255, 255) = Kuning untuk indikator telegram
                self.gambar_teks_outline(display_img, "TELEGRAM TERKIRIM!", (20, 90), font_scale=0.8, tebal_outline=3, warna_teks=(0, 255, 255))

            # ----------------------------------------------------
            # PROSES UPDATE GAMBAR KE GUI (VIDEO & GRAFIK TERPISAH)
            # ----------------------------------------------------
            # 1. Update Video Utama
            rgb_img = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(rgb_img)
            img_tk = ctk.CTkImage(light_image=img_pil, size=(800, 600))
            self.after(0, self.update_video_label, img_tk)

            # 2. Update Panel Grafik di sebelah kanan
            graph_img = self.get_graph_image(self.fight_prob_history)
            rgb_graph = cv2.cvtColor(graph_img, cv2.COLOR_BGR2RGB)
            graph_pil = Image.fromarray(rgb_graph)
            graph_tk = ctk.CTkImage(light_image=graph_pil, size=(320, 130))
            self.after(0, self.update_graph_label, graph_tk)

        cap.release()
        self.after(0, lambda: self.video_label.configure(image="", text="Kamera Dimatikan."))
        self.after(0, lambda: self.graph_label.configure(image="", text="Menunggu data AI..."))

    def update_video_label(self, img_tk):
        self.video_label.configure(image=img_tk, text="")

    def update_graph_label(self, graph_tk):
        self.graph_label.configure(image=graph_tk, text="")

if __name__ == "__main__":
    app = MandorApp()
    app.mainloop()