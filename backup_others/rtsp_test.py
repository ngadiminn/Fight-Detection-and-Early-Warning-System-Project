"""
RTSP Streaming Test
===================
Script untuk menguji koneksi dan streaming RTSP dari kamera/server.

Dependensi:
    pip install opencv-python
    pip install numpy

Cara pakai:
    python rtsp_test.py
    python rtsp_test.py --url rtsp://username:password@192.168.1.100:554/stream
"""

import cv2
import time
import argparse
import sys
import numpy as np
from datetime import datetime


# ─── Konfigurasi Default ──────────────────────────────────────────────────────

DEFAULT_RTSP_URL = "rtsp://username:password@192.168.1.23:554/cam/realmonitor?channel=1&subtype=1"

# Contoh URL lain:
# ONVIF standard   : rtsp://admin:admin@192.168.1.100:554/onvif1
# Hikvision        : rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101
# Dahua            : rtsp://admin:password@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0
# Axis             : rtsp://root:password@192.168.1.100/axis-media/media.amp
# Generic          : rtsp://192.168.1.100:554/live
# Local test (VLC) : rtsp://localhost:8554/test

# ─── Fungsi Utama ─────────────────────────────────────────────────────────────

def test_rtsp_connection(rtsp_url: str, timeout: int = 10) -> bool:
    """
    Menguji apakah RTSP URL dapat terhubung.

    Args:
        rtsp_url: URL RTSP yang akan diuji
        timeout: Batas waktu koneksi dalam detik

    Returns:
        True jika berhasil terhubung, False jika gagal
    """
    print(f"\n{'='*60}")
    print(f"  RTSP CONNECTION TEST")
    print(f"{'='*60}")
    print(f"  URL    : {rtsp_url}")
    print(f"  Timeout: {timeout} detik")
    print(f"{'='*60}\n")

    # Paksa OpenCV pakai FFmpeg backend (lebih stabil untuk RTSP)
    os_env = {
        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC: timeout * 1000,
        cv2.CAP_PROP_READ_TIMEOUT_MSEC: timeout * 1000,
    }

    print("[INFO] Mencoba membuka stream...")
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

    # Set timeout dan buffer
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)

    start_time = time.time()

    if not cap.isOpened():
        elapsed = time.time() - start_time
        print(f"[GAGAL] Tidak dapat membuka stream setelah {elapsed:.1f}s")
        cap.release()
        return False

    elapsed = time.time() - start_time
    print(f"[OK] Stream berhasil dibuka dalam {elapsed:.1f}s")

    # Baca satu frame untuk verifikasi
    ret, frame = cap.read()
    if not ret or frame is None:
        print("[GAGAL] Tidak dapat membaca frame dari stream")
        cap.release()
        return False

    # Tampilkan info stream
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    codec  = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec_str = "".join([chr((codec >> 8 * i) & 0xFF) for i in range(4)])

    print(f"\n[INFO] Informasi Stream:")
    print(f"       Resolusi : {width} x {height}")
    print(f"       FPS      : {fps:.2f}")
    print(f"       Codec    : {codec_str}")
    print(f"       Frame    : {frame.shape}")

    cap.release()
    return True


def stream_rtsp(rtsp_url: str, show_window: bool = True,
                save_video: bool = False, output_file: str = "output.avi",
                max_frames: int = -1):
    """
    Streaming RTSP dengan tampilan real-time dan statistik.

    Args:
        rtsp_url    : URL RTSP
        show_window : Tampilkan jendela preview
        save_video  : Simpan video ke file
        output_file : Nama file output jika save_video=True
        max_frames  : Batas jumlah frame (-1 = tidak terbatas)
    """
    print(f"\n[INFO] Memulai RTSP Stream...")
    print(f"       URL: {rtsp_url}")
    print(f"       Tekan 'q' untuk berhenti | 's' untuk screenshot\n")

    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

    if not cap.isOpened():
        print("[ERROR] Gagal membuka stream RTSP!")
        return

    # Setup video writer jika perlu simpan
    writer = None
    if save_video:
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps    = cap.get(cv2.CAP_PROP_FPS) or 25.0
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
        print(f"[INFO] Menyimpan video ke: {output_file}")

    frame_count  = 0
    error_count  = 0
    start_time   = time.time()
    prev_time    = start_time
    fps_list     = []
    screenshot_n = 0

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                error_count += 1
                print(f"[WARN] Gagal baca frame (total error: {error_count})")
                if error_count > 30:
                    print("[ERROR] Terlalu banyak error, menghentikan stream.")
                    break
                time.sleep(0.1)
                continue

            error_count = 0
            frame_count += 1

            # Hitung FPS
            now          = time.time()
            elapsed_fps  = now - prev_time
            prev_time    = now
            current_fps  = 1.0 / elapsed_fps if elapsed_fps > 0 else 0
            fps_list.append(current_fps)
            if len(fps_list) > 30:
                fps_list.pop(0)
            avg_fps = np.mean(fps_list)

            # Overlay info pada frame
            elapsed_total = now - start_time
            timestamp     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cv2.rectangle(frame, (0, 0), (360, 80), (0, 0, 0), -1)
            cv2.putText(frame, f"FPS: {avg_fps:.1f}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Frames: {frame_count}",
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Uptime: {elapsed_total:.0f}s",
                        (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, timestamp,
                        (frame.shape[1] - 230, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

            # Simpan frame
            if writer:
                writer.write(frame)

            # Tampilkan window
            if show_window:
                cv2.imshow("RTSP Stream Test", frame)
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):
                    print("\n[INFO] Dihentikan oleh pengguna.")
                    break
                elif key == ord('s'):
                    screenshot_n += 1
                    fname = f"screenshot_{screenshot_n:03d}.jpg"
                    cv2.imwrite(fname, frame)
                    print(f"[INFO] Screenshot disimpan: {fname}")

            # Batasi frame jika ditentukan
            if max_frames > 0 and frame_count >= max_frames:
                print(f"\n[INFO] Mencapai batas {max_frames} frame.")
                break

            # Log statistik setiap 100 frame
            if frame_count % 100 == 0:
                print(f"[STAT] Frame: {frame_count:6d} | "
                      f"FPS: {avg_fps:.1f} | "
                      f"Uptime: {elapsed_total:.0f}s")

    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan dengan Ctrl+C")

    finally:
        cap.release()
        if writer:
            writer.release()
        if show_window:
            cv2.destroyAllWindows()

        # Ringkasan akhir
        total_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"  RINGKASAN")
        print(f"{'='*60}")
        print(f"  Total frame  : {frame_count}")
        print(f"  Avg FPS      : {np.mean(fps_list):.2f}" if fps_list else "  Avg FPS      : N/A")
        print(f"  Total durasi : {total_time:.1f} detik")
        if save_video:
            print(f"  Video simpan : {output_file}")
        print(f"{'='*60}\n")


def benchmark_rtsp(rtsp_url: str, duration: int = 30):
    """
    Benchmark performa stream RTSP selama sejumlah detik.

    Args:
        rtsp_url : URL RTSP
        duration : Durasi benchmark dalam detik
    """
    print(f"\n[INFO] Menjalankan benchmark selama {duration} detik...")

    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

    if not cap.isOpened():
        print("[ERROR] Gagal membuka stream!")
        return

    frame_count = 0
    error_count = 0
    fps_samples = []
    start_time  = time.time()
    prev_time   = start_time

    while time.time() - start_time < duration:
        ret, frame = cap.read()
        if ret:
            frame_count += 1
            now = time.time()
            d   = now - prev_time
            if d > 0:
                fps_samples.append(1.0 / d)
            prev_time = now
        else:
            error_count += 1

    cap.release()
    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"  HASIL BENCHMARK")
    print(f"{'='*60}")
    print(f"  Durasi          : {elapsed:.1f}s")
    print(f"  Total frame     : {frame_count}")
    print(f"  Total error     : {error_count}")
    print(f"  Avg FPS         : {np.mean(fps_samples):.2f}" if fps_samples else "  Avg FPS: N/A")
    print(f"  Min FPS         : {np.min(fps_samples):.2f}" if fps_samples else "")
    print(f"  Max FPS         : {np.max(fps_samples):.2f}" if fps_samples else "")
    print(f"  Stabilitas      : {(frame_count / max(frame_count + error_count, 1)) * 100:.1f}%")
    print(f"{'='*60}\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RTSP Streaming Test Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python rtsp_test.py
  python rtsp_test.py --url rtsp://admin:admin@192.168.1.100:554/stream1
  python rtsp_test.py --url rtsp://... --mode benchmark --duration 60
  python rtsp_test.py --url rtsp://... --mode stream --save
  python rtsp_test.py --url rtsp://... --mode connect
        """
    )
    parser.add_argument("--url",      type=str, default=DEFAULT_RTSP_URL,
                        help="URL RTSP (default: %(default)s)")
    parser.add_argument("--mode",     type=str, default="stream",
                        choices=["connect", "stream", "benchmark"],
                        help="Mode: connect | stream | benchmark (default: stream)")
    parser.add_argument("--timeout",  type=int, default=10,
                        help="Timeout koneksi dalam detik (default: 10)")
    parser.add_argument("--duration", type=int, default=30,
                        help="Durasi benchmark dalam detik (default: 30)")
    parser.add_argument("--save",     action="store_true",
                        help="Simpan video ke file (mode stream)")
    parser.add_argument("--output",   type=str, default="output.avi",
                        help="Nama file output video (default: output.avi)")
    parser.add_argument("--no-window", action="store_true",
                        help="Jangan tampilkan jendela (headless mode)")
    parser.add_argument("--max-frames", type=int, default=-1,
                        help="Batas jumlah frame (-1 = tidak terbatas)")

    args = parser.parse_args()

    print(f"\nOpenCV version : {cv2.__version__}")
    print(f"Mode           : {args.mode}")

    if args.mode == "connect":
        ok = test_rtsp_connection(args.url, timeout=args.timeout)
        sys.exit(0 if ok else 1)

    elif args.mode == "stream":
        # Tes koneksi dulu
        ok = test_rtsp_connection(args.url, timeout=args.timeout)
        if not ok:
            print("[ERROR] Koneksi gagal, stream dibatalkan.")
            sys.exit(1)
        stream_rtsp(
            rtsp_url    = args.url,
            show_window = not args.no_window,
            save_video  = args.save,
            output_file = args.output,
            max_frames  = args.max_frames,
        )

    elif args.mode == "benchmark":
        ok = test_rtsp_connection(args.url, timeout=args.timeout)
        if not ok:
            print("[ERROR] Koneksi gagal, benchmark dibatalkan.")
            sys.exit(1)
        benchmark_rtsp(args.url, duration=args.duration)


if __name__ == "__main__":
    main()
