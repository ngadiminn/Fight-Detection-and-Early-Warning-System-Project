import os
import random
import shutil

# =====================================================================
# 1. KONFIGURASI DIREKTORI
# =====================================================================
# Lokasi folder sumber dataset mentah
SOURCE_NORMAL = r"D:\Project_CCTV_3\cobs\Normal"
SOURCE_VIOLENCE = r"D:\Project_CCTV_3\cobs\Violence"

# Lokasi folder tujuan untuk dataset eksternal yang akan diuji
TARGET_BASE = r"D:\Project_CCTV_3\dataset_eksternal"
TARGET_NORMAL = os.path.join(TARGET_BASE, "noFight")
TARGET_VIOLENCE = os.path.join(TARGET_BASE, "fight")

# =====================================================================
# 2. KONFIGURASI JUMLAH SAMPEL
# =====================================================================
NUM_NORMAL = 50
NUM_VIOLENCE = 40

def prepare_validation_dataset():
    """
    Fungsi untuk mengambil subset dataset secara acak, menyalin, dan 
    melakukan pelabelan ulang (re-labelling) sesuai struktur kelas model.
    """
    print("[INFO] Memulai penyiapan dataset eksternal...")
    
    # Membuat folder tujuan jika belum tersedia
    os.makedirs(TARGET_NORMAL, exist_ok=True)
    os.makedirs(TARGET_VIOLENCE, exist_ok=True)

    # Mengambil seluruh daftar file berekstensi video dari folder sumber
    normal_files = [f for f in os.listdir(SOURCE_NORMAL) if f.endswith(('.avi', '.mp4'))]
    violence_files = [f for f in os.listdir(SOURCE_VIOLENCE) if f.endswith(('.avi', '.mp4'))]

    print(f" -> Total video Normal asli ditemukan  : {len(normal_files)}")
    print(f" -> Total video Violence asli ditemukan: {len(violence_files)}")

    # Memvalidasi ketersediaan jumlah file sebelum diproses
    if len(normal_files) < NUM_NORMAL:
        print("ERROR: Jumlah video Normal tidak mencukupi untuk subset!")
        return
    if len(violence_files) < NUM_VIOLENCE:
        print("ERROR: Jumlah video Violence tidak mencukupi untuk subset!")
        return

    # Mengacak urutan elemen di dalam daftar untuk memastikan pemilihan sampel acak (Randomize)
    random.shuffle(normal_files)
    random.shuffle(violence_files)

    # Memotong (slicing) daftar sesuai dengan jumlah sampel yang dibutuhkan
    selected_normal = normal_files[:NUM_NORMAL]
    selected_violence = violence_files[:NUM_VIOLENCE]

    print(f"\n[PROSES] Menyalin dan me-relabel {NUM_NORMAL} sampel Normal...")
    for i, filename in enumerate(selected_normal, 1):
        src_path = os.path.join(SOURCE_NORMAL, filename)
        # Re-labelling menjadi format: noFight_001.avi, noFight_002.avi, dst.
        ext = os.path.splitext(filename)[1]
        new_name = f"noFight_{i:03d}{ext}"
        dst_path = os.path.join(TARGET_NORMAL, new_name)
        shutil.copy2(src_path, dst_path)

    print(f"[PROSES] Menyalin dan me-relabel {NUM_VIOLENCE} sampel Violence...")
    for i, filename in enumerate(selected_violence, 1):
        src_path = os.path.join(SOURCE_VIOLENCE, filename)
        # Re-labelling menjadi format: fight_001.avi, fight_002.avi, dst.
        ext = os.path.splitext(filename)[1]
        new_name = f"fight_{i:03d}{ext}"
        dst_path = os.path.join(TARGET_VIOLENCE, new_name)
        shutil.copy2(src_path, dst_path)

    print("\n[SELESAI] Penyiapan dataset eksternal berhasil dieksekusi!")
    print(f"[INFO] Direktori dataset baru: {TARGET_BASE}")

if __name__ == "__main__":
    prepare_validation_dataset()