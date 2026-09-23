// // --- KODE TES 1: LED ---
// const int led1 = 13;
// const int led2 = 14;
// const int led3 = 27;

// void setup() {
//   pinMode(led1, OUTPUT);
//   pinMode(led2, OUTPUT);
//   pinMode(led3, OUTPUT);
  
//   // Pastikan semua LED mati saat awal mulai (Active LOW = HIGH untuk mati)
//   digitalWrite(led1, HIGH);
//   digitalWrite(led2, HIGH);
//   digitalWrite(led3, HIGH);
// }

// void loop() {
//   // Nyalakan berurutan (LOW untuk menyala)
//   digitalWrite(led1, LOW);
//   delay(500);
//   digitalWrite(led2, LOW);
//   delay(500);
//   digitalWrite(led3, LOW);
//   delay(500);

//   // Matikan semua bersamaan
//   digitalWrite(led1, HIGH);
//   digitalWrite(led2, HIGH);
//   digitalWrite(led3, HIGH);
//   delay(1000); // Jeda 1 detik sebelum mengulang
// }

// // --- KODE TES 2: TOMBOL ---
// const int btnAtas = 25;
// const int btnBawah = 26;

// void setup() {
//   Serial.begin(115200); // Buka Serial Monitor di baud rate 115200
  
//   // Gunakan INPUT biasa karena pull-up resistor (R1, R2) sudah ada di hardware
//   pinMode(btnAtas, INPUT); 
//   pinMode(btnBawah, INPUT);
// }

// void loop() {
//   int statusAtas = digitalRead(btnAtas);
//   int statusBawah = digitalRead(btnBawah);

//   // Cetak status ke Serial Monitor
//   Serial.print("Status Tombol D27: ");
//   if(statusAtas == LOW) {
//     Serial.print("DITEKAN  |  ");
//   } else {
//     Serial.print("Lepas    |  ");
//   }

//   Serial.print("Status Tombol D26: ");
//   if(statusBawah == LOW) {
//     Serial.println("DITEKAN");
//   } else {
//     Serial.println("Lepas");
//   }

//   delay(200); // Jeda agar tulisan tidak berjalan terlalu cepat
// }

// // --- KODE TES 3: RELAY ---
// const int relayPin = 5;

// void setup() {
//   pinMode(relayPin, OUTPUT);
//   // Pastikan relay mati saat awal
//   digitalWrite(relayPin, LOW); 
// }

// void loop() {
//   // Nyalakan Relay
//   digitalWrite(relayPin, HIGH);
//   delay(5000); // Biarkan menyala selama 5 detik
  
//   // Matikan Relay
//   digitalWrite(relayPin, LOW);
//   delay(5000); // Biarkan mati selama 5 detik
// }


#include <DFRobotDFPlayerMini.h>

DFRobotDFPlayerMini myDFPlayer;

void setup() {
  // Kita pakai 'Serial' bawaan ESP32 (yang memang nempel di RX0/TX0).
  // Wajib pakai angka 9600 karena itu bahasa standarnya DFPlayer.
  Serial.begin(9600);
  
  // Kasih waktu 1 detik buat ESP32 dan DFPlayer "salaman"
  delay(1000);

  // Mulai panggil DFPlayer
  if (!myDFPlayer.begin(Serial)) { 
    // Karena kita nggak bisa liat Serial Monitor, kalau DFPlayer-nya error,
    // kita suruh lampu biru kecil bawaan ESP32 (Pin 2) kedip-kedip cepat sbg tanda bahaya.
    pinMode(2, OUTPUT);
    while(true){
      digitalWrite(2, HIGH); delay(100);
      digitalWrite(2, LOW); delay(100);
    }
  }

  // Kalau lolos, atur volume dan sikat lagunya!
  myDFPlayer.volume(15);  
  myDFPlayer.play(1); // Putar lagu 001.mp3
}

void loop() {
  // Biarkan lagunya mengalun santai
}