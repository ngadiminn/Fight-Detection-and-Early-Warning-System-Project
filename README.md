# 🚨 Fight Detection & Early Warning System (CCTV Surveillance)

Sistem deteksi perkelahian / tindak kekerasan secara *real-time* berbasis CCTV dan kecerdasan buatan (*Computer Vision*) menggunakan arsitektur **Multiscale Vision Transformers (MViT-v2-S)**, terintegrasi dengan **Early Warning System (ESP32 Actuator/Alarm)** serta notifikasi otomatis ke **Telegram Bot**.

---

## 📌 Fitur Utama

- **🧠 Deep Learning Video Classification**: Menggunakan model `MViT_v2_s` (*Multiscale Vision Transformer*) yang di-fine-tune untuk mendeteksi aksi perkelahian (*fight vs no-fight*) dari urutan frame video (sequence clips).
- **📹 Real-Time RTSP CCTV Streaming**: Mendukung pemrosesan langsung dari feed IP Camera (RTSP stream) maupun file video lokal/webcam.
- **🖥️ Modern GUI Dashboard**: Dibangun menggunakan `CustomTkinter` dengan visualisasi status stream, grafik probabilitas, log aktivitas, dan auto-capture bukti kejadian.
- **🔔 Telegram Bot Alerting**: Pengiriman notifikasi darurat secara instan beserta foto snapshot kejadian saat terdeteksi perkelahian.
- **⚡ IoT Early Warning Trigger**: Integrasi komunikasi HTTP/WiFi ke modul **ESP32** untuk menyalakan aktuator fisik (sirine / buzzer / lampu peringatan / relay).
- **📊 Riwayat & Evaluasi Lengkap**: Disertai notebook visualisasi metrik evaluasi, confusion matrix eksternal, dan grafik pelatihan.

---

## 📂 Struktur Direktori

```text
├── models/                     # Bobot model terlatih (.pth) via Git LFS
│   ├── mvit_fight_model.pth
│   ├── mvit_fight_modelb4lr0001.pth
│   └── ...
├── dataset_maintraining/       # Dataset video training & validasi
├── dataset_eksternal/          # Dataset uji eksternal untuk validasi generalisasi
├── History_TrainingGraphs/     # Grafik loss, akurasi, dan performa training
├── History_Keypose/            # Ekstraksi frame/keypose untuk analisis
├── History_Capture/            # Folder penyimpanan tangkapan layar otomatis
├── code_ino/                   # Source code Arduino / ESP32 untuk aktuator peringatan
├── code_py/                    # Skrip pengujian RTSP & konektivitas WiFi
├── notebooks/                  # Jupyter Notebook untuk training & eksperimen
├── Fight_utils_mvit.py         # Modul preprocessing, transform, & inferensi MViT
├── main_gui_app.py             # Aplikasi GUI utama (Dashboard Deteksi CCTV)
├── datasetprep.py              # Utilitas pembagian dataset (train/val split)
├── eval_eksternal.py           # Skrip evaluasi performa pada dataset eksternal
├── requirements.txt            # Daftar pustaka Python yang dibutuhkan
└── README.md                   # Dokumentasi proyek
```

---

## 🛠️ Instalasi & Persiapan

### 1. Clone Repository & Git LFS
Pastikan Git dan Git LFS sudah terpasang di komputer Anda:
```bash
git clone https://github.com/ngadiminn/Fight-Detection-and-Early-Warning-System-Project.git
cd Fight-Detection-and-Early-Warning-System-Project

# Pastikan file model .pth tertarik dengan sempurna
git lfs pull
```

### 2. Buat & Aktifkan Virtual Environment (Direkomendasikan)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instal Dependensi
```bash
pip install -r requirements.txt
```

---

## 🚀 Cara Menjalankan Sistem

### Menjalankan Dashboard GUI Utama
Pastikan konfigurasi RTSP stream CCTV, IP ESP32, serta token Telegram pada `main_gui_app.py` sudah sesuai dengan jaringan Anda, lalu jalankan:

```bash
python main_gui_app.py
```

### Evaluasi Dataset Eksternal
Untuk menguji performa model terhadap dataset uji eksternal:
```bash
python eval_eksternal.py
```

---

## ⚙️ Konfigurasi Sistem

Di dalam `main_gui_app.py`, Anda dapat menyesuaikan konfigurasi berikut:
- **`RTSP_URL`**: URL stream RTSP IP Camera CCTV Anda.
- **`ESP32_IP`**: Alamat IP modul ESP32 untuk aktuator peringatan dini.
- **`BOT_TOKEN` & `CHAT_ID`**: Token bot dan ID chat Telegram tujuan pengiriman alert.
- **`MODEL_PATH`**: Lokasi file bobot model (contoh: `models/mvit_fight_modelb4lr0001.pth`).
- **`SEQUENCE_LENGTH`**: Jumlah frame yang diproses dalam 1 window inferensi (default: `16`).

---

## 📊 Hasil Evaluasi Model

Evaluasi model MViT menghasilkan akurasi dan ketahanan deteksi yang tinggi pada berbagai skenario pencahayaan dan pergerakan objek. Metrik evaluasi lengkap, kurva pelatihan, dan confusion matrix dapat dilihat pada file `confusion_matrix_eksternal.png` dan folder `History_TrainingGraphs/`.

---

## 👥 Kontributor & Lisensi
Dikembangkan oleh **ngadiminn**. Proyek ini ditujukan untuk kebutuhan riset pengawasan keamanan cerdas dan deteksi aksi kekerasan publik.
