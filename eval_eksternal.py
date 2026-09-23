import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report, ConfusionMatrixDisplay
import Fight_utils_mvit

# =====================================================================
# 1. KONFIGURASI DIREKTORI DAN PARAMETER
# =====================================================================
DATASET_EKSTERNAL_DIR = r"D:\Project_CCTV_3\dataset_eksternal"
MODEL_PATH = "models/mvit_fight_modelb4lr0001.pth"
CLASSES_LIST = ['fight', 'noFight']
SEQUENCE_LENGTH = 16

def extract_16_frames(video_path):
    """
    Fungsi untuk mengekstrak 16 frame secara merata dari sebuah video
    untuk mensimulasikan jendela waktu observasi (Space-Time Cubes).
    """
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    
    if frame_count == 0:
        return frames
        
    # Menghitung interval lompatan (skip) agar merata dari awal hingga akhir video
    skip_interval = max(int(frame_count / SEQUENCE_LENGTH), 1)
    
    for i in range(SEQUENCE_LENGTH):
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(i * skip_interval, frame_count - 1))
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)
        else:
            break
            
    cap.release()
    
    # Padding: Jika durasi video sangat pendek, duplikasi frame terakhir
    while len(frames) > 0 and len(frames) < SEQUENCE_LENGTH:
        frames.append(frames[-1])
        
    return frames

def evaluate_external_dataset():
    """
    Fungsi utama untuk melakukan pengujian model terhadap dataset eksternal
    dan menghasilkan metrik Confusion Matrix serta Classification Report.
    """
    print("[INFO] Memuat arsitektur dan bobot MViTv2...")
    model = Fight_utils_mvit.loadModel(MODEL_PATH)
    transform = Fight_utils_mvit.transform_()
    
    y_true = []
    y_pred = []
    
    # 2. PROSES ITERASI DAN INFERENSI KESELURUHAN DATASET
    for class_name in CLASSES_LIST:
        folder_path = os.path.join(DATASET_EKSTERNAL_DIR, class_name)
        if not os.path.exists(folder_path):
            print(f"Peringatan: Direktori {folder_path} tidak ditemukan!")
            continue
            
        video_files = [f for f in os.listdir(folder_path) if f.endswith(('.mp4', '.avi'))]
        print(f"\n[INFO] Memproses kelas pengujian: '{class_name}' ({len(video_files)} sampel)...")
        
        for i, video_file in enumerate(video_files, 1):
            video_path = os.path.join(folder_path, video_file)
            frames = extract_16_frames(video_path)
            
            if len(frames) == SEQUENCE_LENGTH:
                # Menerapkan standardisasi citra Albumentations
                clips = []
                for frame in frames:
                    clips.append(transform(image=frame)['image'])
                    
                # Eksekusi prediksi kelas menggunakan model MViTv2
                predicted_class = Fight_utils_mvit.PredTopKClass(1, clips, model)
                
                y_true.append(class_name)
                y_pred.append(predicted_class)
                
            if i % 10 == 0 or i == len(video_files):
                print(f"       -> {i}/{len(video_files)} video berhasil dianalisis...")

    # 3. PENYUSUNAN METRIK EVALUASI
    print("\n[INFO] Menyusun Confusion Matrix dan Classification Report...")
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES_LIST)
    
    # Merender dan menyimpan Confusion Matrix sebagai gambar
    fig, ax = plt.subplots(figsize=(8, 6), dpi=120)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=CLASSES_LIST)
    disp.plot(cmap=plt.cm.Blues, ax=ax)
    ax.set_title('Confusion Matrix - Validasi Dataset Eksternal (Unseen Data)', fontweight='bold', pad=15)
    plt.tight_layout()
    plt.savefig('confusion_matrix_eksternal.png', dpi=300, bbox_inches='tight')
    
    print("\n" + "="*60)
    print("LAPORAN EVALUASI DATASET EKSTERNAL (BAB 4)")
    print("="*60)
    report = classification_report(y_true, y_pred, target_names=CLASSES_LIST, digits=4)
    print(report)
    print("="*60)
    print("[INFO] Sukses! Gambar confusion matrix tersimpan sebagai 'confusion_matrix_eksternal.png'")

if __name__ == "__main__":
    evaluate_external_dataset()