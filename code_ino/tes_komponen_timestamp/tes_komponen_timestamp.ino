#include <WiFi.h>
#include <WebServer.h>
#include <DFRobotDFPlayerMini.h>
#include <time.h>
#include <sys/time.h>

DFRobotDFPlayerMini myDFPlayer;
WebServer server(80); // Server jalan di port 80

// --- PENGATURAN WIFI ---
const char* ssid = "lord hytam";
const char* password = "satusampai8";

// --- PENGATURAN WAKTU SERVER (NTP) ---
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 25200; // GMT+7 untuk Waktu Indonesia Barat (WIB)
const int   daylightOffset_sec = 0;

// --- PIN DEFINITIONS ---
const int led1 = 27;   // Indikator Siaga (Armed)
const int led2 = 14;   // Indikator Senyap (Muted)
const int led3 = 13;   // Indikator Bahaya (Kedip)
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

// Fitur penundaan mati audio selama 3 detik
unsigned long waktuMulaiAman = 0;  // Stopwatch untuk menghitung 3 detik
bool prosesBerhentiAudio = false;  // Menandai status penundaan audio sebelum dimatikan

// --- FUNGSI MENDAPATKAN TIMESTAMP NYATA ---
String getRealTimestamp() {
  struct timeval tv;
  // Menarik waktu dari sistem ESP32 secara mentah (termasuk microsecond)
  gettimeofday(&tv, NULL);

  // Mengubah waktu mentah menjadi format kalender lokal
  struct tm* timeinfo = localtime(&tv.tv_sec);
  if (timeinfo == NULL) {
    return "Gagal sinkron waktu";
  }

  char timeStringBuff[50];
  // Format Output awal: YYYY-MM-DD HH:MM:SS
  strftime(timeStringBuff, sizeof(timeStringBuff), "%Y-%m-%d %H:%M:%S", timeinfo);

  // Mengubah microsecond (us) menjadi millisecond (ms)
  int millisec = tv.tv_usec / 1000;

  // Menggabungkan string jam dengan angka milidetiknya (format: .xyz)
  char finalBuff[60];
  sprintf(finalBuff, "%s.%03d", timeStringBuff, millisec);

  return String(finalBuff);
}

// --- FUNGSI MENERIMA SINYAL DARI PYTHON ---
void handleSinyal() {
  if (server.hasArg("status")) {
    String nilai = server.arg("status");
    if (nilai == "1") {
      isAlarm = true;
      // Mencetak tanggal dan jam nyata saat status bahaya diterima
      Serial.print("🚨 [LATENSI] Sinyal BAHAYA masuk pada: ");
      Serial.println(getRealTimestamp());
      
      server.send(200, "text/plain", "Bahaya Diterima! Alarm Aktif.");
    } else if (nilai == "0") {
      isAlarm = false;
      // Mencetak tanggal dan jam nyata saat status aman diterima
      Serial.print("✅ [LATENSI] Sinyal AMAN masuk pada: ");
      Serial.println(getRealTimestamp());
      
      server.send(200, "text/plain", "Aman Diterima! Alarm Dimatikan.");
    }
  } else {
    server.send(400, "text/plain", "Format salah! Gunakan ?status=1 atau 0");
  }
}

void setup() {
  // 1. SETUP PIN & MATIKAN SEMUA AKTUALISASI AWAL
  pinMode(led1, OUTPUT); pinMode(led2, OUTPUT); pinMode(led3, OUTPUT);
  digitalWrite(led1, HIGH); digitalWrite(led2, HIGH); digitalWrite(led3, HIGH); // Kondisi Mati (Active LOW)
  
  pinMode(btnAtas, INPUT); pinMode(btnBawah, INPUT);
  
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, LOW); // Relay kondisi mati

  // 2. KONEKSI WIFI & SERIAL MONITOR PC
  Serial.begin(115200); // Kecepatan tinggi khusus Serial Monitor PC
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  
  Serial.println("\nKoneksi Berhasil!");
  Serial.print("IP ESP32: ");
  Serial.println(WiFi.localIP());

  // Inisialisasi sinkronisasi waktu ke internet via server NTP
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  Serial.println("Sinkronisasi waktu dengan server NTP berhasil!");
  Serial.println("Sistem Siaga. Menunggu sinyal dari Python...");

  Serial.flush(); 
  delay(1000);    
  
  // 3. SETUP WEB SERVER
  server.on("/sinyal", handleSinyal); 
  server.begin();

  // 4. SETUP DFPLAYER DI PIN D16 & D17 (Serial2)
  // Format komunikasi: Baudrate 9600, Mode 8N1, Pin RX=16, Pin TX=17
  Serial2.begin(9600, SERIAL_8N1, 16, 17); 
  delay(1000);
  
  // Menginisialisasi modul DFPlayer menggunakan jalur komunikasi Serial2
  if (myDFPlayer.begin(Serial2)) {
    Serial.println("DFPlayer Siap!");
    myDFPlayer.volume(20); 
  } else {
    Serial.println("Error: DFPlayer tidak terdeteksi di pin 16/17!");
  }
}

void loop() {
  server.handleClient(); // Memproses permintaan data masuk dari protokol WiFi

  // BACA TOMBOL FISIK
  bool isArmed = (digitalRead(btnAtas) == HIGH); 
  bool isMuted = (digitalRead(btnBawah) == HIGH);

  // LOGIKA LED 1 (SIAGA) & LED 2 (SENYAP)
  digitalWrite(led1, isArmed ? LOW : HIGH); 
  digitalWrite(led2, isMuted ? LOW : HIGH);

  // --- LOGIKA UTAMA ALARM ---
  if (isArmed && isAlarm) {
    
    // Deteksi transisi perubahan kondisi dari aman ke kondisi bahaya
    if (!alarmAktifSebelumnya) {
      waktuMulaiAlarm = millis();
      statusAudio = 0;
      alarmAktifSebelumnya = true;
      prosesBerhentiAudio = false; 
    }

    // Menghitung akumulasi durasi waktu alarm aktif
    unsigned long waktuBerjalan = millis() - waktuMulaiAlarm;

    // 1. Logika Aktivasi Audio Berdasarkan Jeda Waktu (Non-blocking)
    if (!isMuted) { 
      // Mengaktifkan Track 001 setelah masuk detik ke-5
      if (waktuBerjalan >= 5000 && statusAudio == 0) {
        myDFPlayer.play(1); 
        statusAudio = 1; 
      }
      // Mengaktifkan Track 002 setelah masuk detik ke-12 (Jeda 7 detik setelah Track 1)
      else if (waktuBerjalan >= 12000 && statusAudio == 1) {
        myDFPlayer.play(2); 
        statusAudio = 2; 
      }
    }

    // 2. Logika Kedipan Indikator Visual Bahaya (Strobo & LED 3) Tiap 200 milidetik
    unsigned long waktuSekarang = millis();
    if (waktuSekarang - waktuKedip >= 200) {
      waktuKedip = waktuSekarang;
      statusKedip = !statusKedip;
      
      digitalWrite(led3, statusKedip ? LOW : HIGH); 
      digitalWrite(relayPin, statusKedip ? HIGH : LOW); 
    }
    
  } else {
    // --- KONDISI AMAN ATAU SISTEM DISARMED ---
    
    // Menonaktifkan seluruh indikator visual secara instan
    digitalWrite(led3, HIGH); 
    digitalWrite(relayPin, LOW); 
    
    alarmAktifSebelumnya = false; 
    
    // Penundaan pemutusan sinyal suara audio selama 3 detik menggunakan metode millis
    if (statusAudio > 0) {
      if (!prosesBerhentiAudio) {
        waktuMulaiAman = millis();
        prosesBerhentiAudio = true;
      }

      if (millis() - waktuMulaiAman >= 3000) {
        myDFPlayer.pause(); 
        statusAudio = 0; 
        prosesBerhentiAudio = false; 
      }
    } else {
      prosesBerhentiAudio = false;
    }
  }
}