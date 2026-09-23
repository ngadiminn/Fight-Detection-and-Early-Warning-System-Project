#include <WiFi.h>
#include <WebServer.h>
#include <DFRobotDFPlayerMini.h>

DFRobotDFPlayerMini myDFPlayer;
WebServer server(80);

// --- PENGATURAN WIFI ---
const char* ssid = "lord hytam";
const char* password = "satusampai8";

// --- PIN DEFINITIONS ---
const int led1 = 13;     // Indikator Siaga (Armed)
const int led2 = 14;     // Indikator Senyap (Muted)
const int led3 = 27;     // Indikator Bahaya (Aktif)
const int btnAtas = 25;  // Saklar Siaga
const int btnBawah = 26; // Saklar Senyap
const int relayPin = 5;  // Relay Strobo

// --- VARIABEL STATUS SISTEM ---
int statusSistem = 0; // 0: Aman, 1: Strobo, 2: Strobo+Sirine, 3: Strobo+Voice
int statusAudio = 0;  // Mencatat track apa yang sedang diputar

// --- VARIABEL TIMER KEDIP ---
unsigned long waktuKedip = 0;
bool statusKedip = false;

// --- FUNGSI MENERIMA SINYAL DARI PYTHON ---
void handleSinyal() {
  if (server.hasArg("status")) {
    int nilai = server.arg("status").toInt();
    
    if (nilai >= 0 && nilai <= 3) {
      statusSistem = nilai;
      
      // KITA NGGAK PAKAI SERIAL.PRINT DI SINI BIAR DFPLAYER NGGAK MABUK!
      server.send(200, "text/plain", "Perintah Skenario Dieksekusi.");
    } else {
      server.send(400, "text/plain", "Skenario tidak dikenal!");
    }
  } else {
    server.send(400, "text/plain", "Format salah!");
  }
}

void setup() {
  pinMode(led1, OUTPUT); pinMode(led2, OUTPUT); pinMode(led3, OUTPUT);
  digitalWrite(led1, HIGH); digitalWrite(led2, HIGH); digitalWrite(led3, HIGH); 
  
  pinMode(btnAtas, INPUT); pinMode(btnBawah, INPUT);
  
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, LOW); 

  // 1. BUKA JALUR KE LAPTOP DULU BUAT NGECEK IP (BAUD 115200)
  Serial.begin(115200); 
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }
  
  Serial.println("\nKoneksi Berhasil!");
  Serial.print("IP ESP32: "); 
  Serial.println(WiFi.localIP());
  Serial.println("Sistem Siaga. Beralih ke DFPlayer dalam 2 detik...");
  
  // Kasih waktu sebentar biar tulisan di atas kebaca di Serial Monitor
  delay(2000); 

  // 2. TUTUP JALUR LAPTOP, GANTI KECEPATAN KHUSUS BUAT DFPLAYER (BAUD 9600)
  Serial.begin(9600); 
  delay(1000);
  
  // Sekarang Serial TX0/RX0 murni cuma buat ngobrol sama modul MP3
  if (myDFPlayer.begin(Serial)) {
    myDFPlayer.volume(20); 
  }

  server.on("/sinyal", handleSinyal); 
  server.begin();
}

void loop() {
  server.handleClient(); 

  bool isArmed = (digitalRead(btnAtas) == HIGH); 
  bool isMuted = (digitalRead(btnBawah) == HIGH);

  digitalWrite(led1, isArmed ? LOW : HIGH); 
  digitalWrite(led2, isMuted ? LOW : HIGH);

  // --- EKSEKUSI SKENARIO DARI PYTHON ---
  if (isArmed && statusSistem > 0) {
    
    // 1. Logika Kedip Strobo Tiap 200ms (Biar ESP32 Nggak Pingsan)
    unsigned long waktuSekarang = millis();
    if (waktuSekarang - waktuKedip >= 200) {
      waktuKedip = waktuSekarang;
      statusKedip = !statusKedip;
      
      digitalWrite(led3, statusKedip ? LOW : HIGH); 
      digitalWrite(relayPin, statusKedip ? HIGH : LOW); 
    }

    // 2. Logika Pemutaran Audio Skenario 2 & 3
    if (!isMuted) {
      if (statusSistem == 2 && statusAudio != 1) {
        myDFPlayer.play(1); // Putar Sirine
        statusAudio = 1;
      } 
      else if (statusSistem == 3 && statusAudio != 2) {
        myDFPlayer.play(2); // Putar Voice
        statusAudio = 2;
      }
    }

  } else {
    // --- KONDISI AMAN (Status 0) ---
    digitalWrite(led3, HIGH); 
    digitalWrite(relayPin, LOW); 
    
    if (statusAudio > 0) {
      myDFPlayer.pause();
      statusAudio = 0;
    }
  }
}