#include <WiFi.h>
#include <WebServer.h>
#include <DFRobotDFPlayerMini.h>

DFRobotDFPlayerMini myDFPlayer;
WebServer server(80); // Server jalan di port 80

// --- PENGATURAN WIFI ---
const char* ssid = "lord hytam";
const char* password = "satusampai8";

// --- PIN DEFINITIONS ---
const int led1 = 27;   // Indikator Siaga (Armed)
const int led2 = 14;   // Indikator Senyap (Muted)
const int led3 = 13;   // Indikator Bahaya (Kedip)
const int btnAtas = 25;  // Saklar Siaga
const int btnBawah = 26; // Saklar Senyap
const int relayPin = 5;  // Relay Strobo

// --- VARIABEL STATUS ---
bool isAlarm = false;        // Sinyal dari Python (0 atau 1)
bool audioSedangMain = false;// Mencegah DFPlayer di-trigger berulang-ulang
unsigned long waktuKedip = 0;
bool statusKedip = false;

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
  // Nyalakan Serial di 115200 SEMENTARA untuk cek IP (Nanti kita ubah ke 9600 buat DFPlayer)
  Serial.begin(115200); 
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  
  // !!! CATAT ALAMAT IP INI DI BUKUMU/NOTEPAD !!!
  Serial.println("Koneksi Berhasil!");
  Serial.print("IP ESP32: ");
  Serial.println(WiFi.localIP());

  Serial.flush(); // Perintah mutlak: "Jangan ngapa-ngapain sampai tulisan IP selesai dicetak!"
  delay(1000);    // Kasih jeda 1 detik biar aman sentosa
  
  // 3. SETUP WEB SERVER
  server.on("/sinyal", handleSinyal); // Path URL untuk menerima data
  server.begin();

  // 4. UBAH SERIAL KE 9600 UNTUK DFPLAYER
  Serial.begin(9600); // Timpa kecepatan Serial jadi 9600 khusus buat DFPlayer
  delay(1000);
  myDFPlayer.begin(Serial); // Mulai DFPlayer secara diam-diam
  myDFPlayer.volume(20); 
}

void loop() {
  server.handleClient(); // Wajib agar ESP32 terus merespon WiFi

  // BACA TOMBOL FISIK
  bool isArmed = (digitalRead(btnAtas) == HIGH); // Jika tombol ditekan (ON)
  bool isMuted = (digitalRead(btnBawah) == HIGH);

  // LOGIKA LED 1 (SIAGA) & LED 2 (SENYAP)
  digitalWrite(led1, isArmed ? LOW : HIGH); // LOW = Nyala
  digitalWrite(led2, isMuted ? LOW : HIGH);

  // --- LOGIKA UTAMA ALARM ---
  if (isArmed && isAlarm) {
    // 1. Audio Trigger (Hanya panggil play 1x saat awal alarm)
    if (!audioSedangMain) {
      if (!isMuted) { // Bunyikan HANYA jika TIDAK mode senyap
        myDFPlayer.play(1); 
      }
      audioSedangMain = true;
    }

    // 2. Strobo & LED 3 Kedip Cepat Panik (Tiap 200 milidetik)
    unsigned long waktuSekarang = millis();
    if (waktuSekarang - waktuKedip >= 200) {
      waktuKedip = waktuSekarang;
      statusKedip = !statusKedip;
      
      digitalWrite(led3, statusKedip ? LOW : HIGH); // LED 3 kedip
      digitalWrite(relayPin, statusKedip ? HIGH : LOW); // Strobo cetak-cetek
    }
  } else {
    // --- KONDISI AMAN ATAU SISTEM DISARMED ---
    digitalWrite(led3, HIGH); // Matikan LED 3
    digitalWrite(relayPin, LOW); // Matikan Strobo
    
    // Matikan suara jika sebelumnya menyala
    if (audioSedangMain) {
      // Untuk modul clone MP3-TF-16P, perintah stop kadang rewel, 
      // jadi kita akalin dengan me-reset atau mem-pause.
      myDFPlayer.pause(); 
      audioSedangMain = false;
    }
  }
}