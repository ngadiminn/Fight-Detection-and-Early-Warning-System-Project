#include <WiFi.h>
#include <WebServer.h>
#include <DFRobotDFPlayerMini.h>

DFRobotDFPlayerMini myDFPlayer;
WebServer server(80); // Server jalan di port 80

// --- PENGATURAN WIFI ---
const char* ssid = "lord hytam";
const char* password = "satusampai8";

// --- PIN DEFINITIONS ---
const int led1 = 13;   // Indikator Siaga (Armed)
const int led2 = 14;   // Indikator Senyap (Muted)
const int led3 = 27;   // Indikator Bahaya (Kedip)
const int btnAtas = 25;  // Saklar Siaga
const int btnBawah = 26; // Saklar Senyap
const int relayPin = 5;  // Relay Strobo

// --- VARIABEL STATUS ALARM & WIFI ---
bool isAlarm = false;        // Sinyal dari Python (0 atau 1)

// --- VARIABEL TIMER (MILLIS) ---
unsigned long waktuKedip = 0;
bool statusKedip = false;

unsigned long waktuMulaiAlarm = 0; // Mencatat kapan alarm pertama kali menyala
int statusAudio = 0;               // 0: Diam, 1: Track 1 main, 2: Track 2 main
bool alarmAktifSebelumnya = false; // Mendeteksi momen transisi dari aman ke bahaya

// Tambahan untuk fitur delay mati 3 detik
unsigned long waktuMulaiAman = 0;  // Stopwatch untuk ngitung 3 detik
bool prosesBerhentiAudio = false;  // Menandai kalau sistem lagi nunggu 3 detik buat matiin audio

// --- FUNGSI MENERIMA SINYAL DARI PYTHON ---
void handleSinyal() {
  if (server.hasArg("status")) {
    String nilai = server.arg("status");
    if (nilai == "1") {
      isAlarm = true;
      server.send(200, "text/plain", "Bahaya Diterima! Alarm Aktif.");
    } else if (nilai == "0") {
      isAlarm = false;
      server.send(200, "text/plain", "Aman Diterima! Alarm Dimatikan.");
    }
  } else {
    server.send(400, "text/plain", "Format salah! Gunakan ?status=1 atau 0");
  }
}

void setup() {
  // 1. SETUP PIN & MATIKAN SEMUA AKTUALISASI AWAL
  pinMode(led1, OUTPUT); pinMode(led2, OUTPUT); pinMode(led3, OUTPUT);
  digitalWrite(led1, HIGH); digitalWrite(led2, HIGH); digitalWrite(led3, HIGH); // Mati (Active LOW)
  
  pinMode(btnAtas, INPUT); pinMode(btnBawah, INPUT);
  
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, LOW); // Relay mati

  // 2. KONEKSI WIFI
  Serial.begin(115200); 
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  
  Serial.println("Koneksi Berhasil!");
  Serial.print("IP ESP32: ");
  Serial.println(WiFi.localIP());

  Serial.flush(); 
  delay(1000);    
  
  // 3. SETUP WEB SERVER
  server.on("/sinyal", handleSinyal); 
  server.begin();

  // 4. UBAH SERIAL KE 9600 UNTUK DFPLAYER
  Serial.begin(9600); 
  delay(1000);
  myDFPlayer.begin(Serial); 
  myDFPlayer.volume(20); 
}

void loop() {
  server.handleClient(); // Wajib agar ESP32 terus merespon WiFi

  // BACA TOMBOL FISIK
  bool isArmed = (digitalRead(btnAtas) == HIGH); 
  bool isMuted = (digitalRead(btnBawah) == HIGH);

  // LOGIKA LED 1 (SIAGA) & LED 2 (SENYAP)
  digitalWrite(led1, isArmed ? LOW : HIGH); 
  digitalWrite(led2, isMuted ? LOW : HIGH);

  // --- LOGIKA UTAMA ALARM ---
  if (isArmed && isAlarm) {
    
    // Deteksi awal mula alarm menyala (Mulai nyalakan stopwatch alarm)
    if (!alarmAktifSebelumnya) {
      waktuMulaiAlarm = millis();
      statusAudio = 0;
      alarmAktifSebelumnya = true;
      prosesBerhentiAudio = false; // Batalin proses matiin audio kalau tiba-tiba bahaya lagi
    }

    // Hitung sudah berapa lama alarm menyala
    unsigned long waktuBerjalan = millis() - waktuMulaiAlarm;

    // 1. Audio Trigger dengan Sistem Timer (Tidak Membekukan Program)
    if (!isMuted) { 
      // Putar Track 001 jika sudah masuk detik ke-5
      if (waktuBerjalan >= 5000 && statusAudio == 0) {
        myDFPlayer.play(1); 
        statusAudio = 1; // Kunci agar tidak diputar berulang-ulang
      }
      // Putar Track 002 jika sudah masuk detik ke-12 (5 detik awal + 7 detik kemudian)
      else if (waktuBerjalan >= 12000 && statusAudio == 1) {
        myDFPlayer.play(2); 
        statusAudio = 2; // Kunci permanen sampai kondisi aman
      }
    }

    // 2. Strobo & LED 3 Kedip Cepat Panik (Tiap 200 milidetik)
    unsigned long waktuSekarang = millis();
    if (waktuSekarang - waktuKedip >= 200) {
      waktuKedip = waktuSekarang;
      statusKedip = !statusKedip;
      
      digitalWrite(led3, statusKedip ? LOW : HIGH); 
      digitalWrite(relayPin, statusKedip ? HIGH : LOW); 
    }
    
  } else {
    // --- KONDISI AMAN ATAU SISTEM DISARMED ---
    
    // Matikan indikator bahaya visual SEKETIKA
    digitalWrite(led3, HIGH); 
    digitalWrite(relayPin, LOW); 
    
    alarmAktifSebelumnya = false; // Reset stopwatch alarm utama
    
    // Matikan suara dengan efek tertahan (delay 3 detik pakai millis)
    if (statusAudio > 0) {
      // Nyalakan stopwatch 3 detik kalau belum mulai
      if (!prosesBerhentiAudio) {
        waktuMulaiAman = millis();
        prosesBerhentiAudio = true;
      }

      // Cek apakah udah berlalu 3000 milidetik (3 detik) sejak aman
      if (millis() - waktuMulaiAman >= 3000) {
        myDFPlayer.pause(); 
        statusAudio = 0; // Reset status audio
        prosesBerhentiAudio = false; // Selesai
      }
    } else {
      // Pastikan indikator aman ter-reset kalau emang audionya udah mati
      prosesBerhentiAudio = false;
    }
  }
}