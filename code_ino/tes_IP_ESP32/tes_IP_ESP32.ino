#include <WiFi.h> // Pakai library ini kalau kamu pakai ESP32

// Ganti sama nama hotspot & password kamu ya!
const char* ssid = "lord hytam";
const char* password = "satusampai8";

void setup() {
  Serial.begin(115200);
  
  // Mulai konek ke WiFi
  WiFi.begin(ssid, password);
  Serial.print("Lagi nyambung ke hotspot...");

  // Tunggu sampai konek
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  // Kalau udah berhasil, kasih tau IP-nya
  Serial.println("");
  Serial.println("Yeay! Berhasil nyambung.");
  Serial.print("Alamat IP ESP kamu adalah: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // Kosongin aja karena kita cuma mau tes IP di awal
}