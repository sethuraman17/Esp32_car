#include <WiFi.h>
#include <WebServer.h>

// ---------------- MOTOR PINS ----------------

const int MR1 = 14; // Right motor forward
const int MR2 = 12; // Right motor backward

const int ML1 = 27; // Left motor backward
const int ML2 = 26; // Left motor forward


// ---------------- WIFI ----------------

// ESP32 creates its own Wi-Fi network
const char* ssid = "ESP32_CAR";
const char* password = "12345678";

WebServer server(80);


// ---------------- MOTOR FUNCTIONS ----------------

void Forward() {

  digitalWrite(MR1, HIGH);
  digitalWrite(MR2, LOW);

  digitalWrite(ML1, LOW);
  digitalWrite(ML2, HIGH);
}

void Backward() {

  digitalWrite(MR1, LOW);
  digitalWrite(MR2, HIGH);

  digitalWrite(ML1, HIGH);
  digitalWrite(ML2, LOW);
}

void Left() {

  digitalWrite(MR1, HIGH);
  digitalWrite(MR2, LOW);

  digitalWrite(ML1, HIGH);
  digitalWrite(ML2, LOW);
}

void Right() {

  digitalWrite(MR1, LOW);
  digitalWrite(MR2, HIGH);

  digitalWrite(ML1, LOW);
  digitalWrite(ML2, HIGH);
}

void Stop() {

  digitalWrite(MR1, LOW);
  digitalWrite(MR2, LOW);

  digitalWrite(ML1, LOW);
  digitalWrite(ML2, LOW);
}


// ---------------- MOBILE UI ----------------

const char HTML_PAGE[] PROGMEM = R"rawliteral(

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
content="width=device-width,
initial-scale=1.0,
user-scalable=no">

<title>ESP32 Car</title>

<style>

body {

  margin: 0;

  background: #111;

  color: white;

  font-family: Arial;

  text-align: center;

  touch-action: none;

}

h1 {

  margin-top: 30px;

}

.control {

  margin-top: 40px;

}

button {

  width: 100px;

  height: 100px;

  margin: 10px;

  border: none;

  border-radius: 20px;

  background: #333;

  color: white;

  font-size: 40px;

}

button:active {

  background: #008cff;

  transform: scale(0.95);

}

.stop {

  background: #d22;

}

</style>

</head>


<body>

<h1>🤖 ESP32 CAR</h1>

<div class="control">

  <div>

    <button
      ontouchstart="send('F')"
      ontouchend="send('S')"
      onmousedown="send('F')"
      onmouseup="send('S')">
      ▲
    </button>
  </div>


  <div>

    <button
      ontouchstart="send('L')"
      ontouchend="send('S')"
      onmousedown="send('L')"
      onmouseup="send('S')">
      ◀️
    </button>


    <button
      class="stop"
      onclick="send('S')">
      ■
    </button>


    <button
      ontouchstart="send('R')"
      ontouchend="send('S')"
      onmousedown="send('R')"
      onmouseup="send('S')">
      ▶️
    </button>

  </div>


  <div>

    <button
      ontouchstart="send('B')"
      ontouchend="send('S')"
      onmousedown="send('B')"
      onmouseup="send('S')">
      ▼
    </button>

  </div>

</div>


<script>

function send(command) {

  fetch('/control?cmd=' + command);

}

</script>


</body>

</html>

)rawliteral";


// ---------------- WEB SERVER ----------------

void handleRoot() {

  server.send(
    200,
    "text/html",
    HTML_PAGE
  );

}


void handleControl() {

  String command =
    server.arg("cmd");


  if (command == "F") {

    Forward();

  }

  else if (command == "B") {

    Backward();

  }

  else if (command == "L") {

    Left();

  }

  else if (command == "R") {

    Right();

  }

  else {

    Stop();

  }


  server.send(
    200,
    "text/plain",
    "OK"
  );

}


// ---------------- SETUP ----------------

void setup() {

  Serial.begin(115200);


  pinMode(MR1, OUTPUT);
  pinMode(MR2, OUTPUT);

  pinMode(ML1, OUTPUT);
  pinMode(ML2, OUTPUT);


  Stop();


  // Create ESP32 Wi-Fi hotspot

  WiFi.mode(WIFI_AP);

  WiFi.softAP(
    ssid,
    password
  );


  Serial.println();

  Serial.println(
    "ESP32 CAR WiFi started"
  );

  Serial.print(
    "IP address: "
  );

  Serial.println(
    WiFi.softAPIP()
  );


  server.on(
    "/",
    handleRoot
  );

  server.on(
    "/control",
    handleControl
  );


  server.begin();

  Serial.println(
    "Web server started"
  );

}


// ---------------- LOOP ----------------

void loop() {

  server.handleClient();

}