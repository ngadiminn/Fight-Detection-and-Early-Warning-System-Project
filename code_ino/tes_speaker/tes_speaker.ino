#include <HardwareSerial.h>
#include <DFRobotDFPlayerMini.h>

DFRobotDFPlayerMini myDFPlayer;

void setup() {
  // Buka jalur komunikasi Serial ke DFPlayer
  Serial.begin(9600); 
  
  // Kasih jeda waktu sebentar biar modul MP3 nyala dengan sempurna
  delay(2000); 
  
  // Mulai inisialisasi DFPlayer
  if (myDFPlayer.begin(Serial)) {
    // Set volume (0 sampai 30). 
    // Aku set 30 biar kamu bisa ukur daya puncak (Peak Power) dari amplifiernya!
    myDFPlayer.volume(20); 
    delay(500);
    
    // Perintah ajaib: Putar Track 001 secara berulang-ulang (Looping)
    myDFPlayer.loop(1); 
  }
}

void loop() {
  // Kosongin aja sayang, soalnya DFPlayer punya chip sendiri 
  // buat ngurusin audio yang di-loop. ESP32 bisa rebahan!
}