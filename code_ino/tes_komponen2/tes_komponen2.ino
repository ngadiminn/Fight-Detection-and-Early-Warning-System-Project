#include <DFRobotDFPlayerMini.h>

DFRobotDFPlayerMini myDFPlayer;

// --- PIN DEFINITIONS ---
// LED (Active LOW)
const int led1 = 13;
const int led2 = 14;
const int led3 = 27;

// Tombol (Latching / Push Button)
const int btnAtas = 25;
const int btnBawah = 26;

// Relay (Khusus untuk Lampu Strobo)
const int relayPin = 5;

// Variabel untuk Bypass Delay (Biar sistem nggak macet)
unsigned long waktuSebelumnyaLed = 0;
bool statusLed3 = HIGH; // HIGH = Mati karena active LOW

unsigned long waktuSebelumnyaRelay = 0;
bool statusRelay = LOW; 

void setup() {
  // 1. SETUP LED
  pinMode(led1, OUTPUT);
  pinMode(led2, OUTPUT);
  pinMode(led3, OUTPUT);
  // Matikan semua LED di awal 
  digitalWrite(led1, HIGH);
  digitalWrite(led2, HIGH);
  digitalWrite(led3, HIGH);

  // 2. SETUP TOMBOL
  pinMode(btnAtas, INPUT);
  pinMode(btnBawah, INPUT);

  // 3. SETUP RELAY STROBO (Ampli otomatis nyala dari hardware)
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, LOW); // Pastikan strobo mati di awal

  // 4. SETUP DFPLAYER
  Serial.begin(9600);
  delay(1000); // Kasih waktu ESP32 dan DFPlayer "salaman"

  // Panggil DFPlayer (Versi Normal)
  if (!myDFPlayer.begin(Serial)) { 
    // Kalau DFPlayer error, LED 3 kedip-kedip super cepat
    pinMode(2, OUTPUT);
    while(true){
      digitalWrite(2, HIGH); delay(100);
      digitalWrite(2, LOW); delay(100);
    }
  }

  // Atur volume dan putar lagu
  myDFPlayer.volume(15);  
  myDFPlayer.play(1); // Putar lagu 0001.mp3
}

void loop() {
  unsigned long waktuSekarang = millis();

  // ---------------------------------------------------------
  // 1. LOGIKA TOMBOL -> LED 1 & 2
  // ---------------------------------------------------------
  int statusAtas = digitalRead(btnAtas);
  int statusBawah = digitalRead(btnBawah);

  // Jika btnAtas LOW (Ditekan), nyalakan LED1
  if(statusAtas == LOW) {
    digitalWrite(led1, LOW);
  } else {
    digitalWrite(led1, HIGH);
  }

  // Jika btnBawah LOW (Ditekan), nyalakan LED2
  if(statusBawah == LOW) {
    digitalWrite(led2, LOW);
  } else {
    digitalWrite(led2, HIGH);
  }

  // ---------------------------------------------------------
  // 2. LOGIKA LED 3 (Heartbeat Sistem - Kedip tiap 1 Detik)
  // ---------------------------------------------------------
  if (waktuSekarang - waktuSebelumnyaLed >= 1000) {
    waktuSebelumnyaLed = waktuSekarang;
    statusLed3 = !statusLed3; // Balik statusnya
    digitalWrite(led3, statusLed3);
  }

  // ---------------------------------------------------------
  // 3. LOGIKA RELAY STROBO (Nyala 5 detik, Mati 5 detik)
  // ---------------------------------------------------------
  if (waktuSekarang - waktuSebelumnyaRelay >= 5000) {
    waktuSebelumnyaRelay = waktuSekarang;
    statusRelay = !statusRelay; // Balik status Relay
    digitalWrite(relayPin, statusRelay);
  }
}