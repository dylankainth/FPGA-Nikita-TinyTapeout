/*
 * Face Detection Chip Integration Example (Arduino/RP2040 Pico)
 *
 * This example shows how to stream camera pixels to the face detection chip
 * and read back detection results.
 *
 * Hardware: RP2040 Pico + OV7670 camera + TinyTapeout face detector
 *
 * Pin Configuration (RP2040):
 *   Data pins (RGB pixel):  GPIO 0-7
 *   Channel select:         GPIO 8-9 (ch_sel[1:0])
 *   Pixel valid:            GPIO 10
 *   Frame done:             GPIO 11
 *   Row zone:               GPIO 12-13
 *   Col zone:               GPIO 14-15
 *   Results:                GPIO 16-20 (face_det, skin, eyes, nose, mouth)
 */

// ============ CONFIGURATION ============

#define FRAME_WIDTH   320
#define FRAME_HEIGHT  240

// Output pins (to face detector)
#define PIN_DATA_BASE    0    // GPIO 0-7 for 8-bit data
#define PIN_CH_SEL_0     8    // Channel select bit 0
#define PIN_CH_SEL_1     9    // Channel select bit 1
#define PIN_PIXEL_VALID  10   // Pixel valid flag
#define PIN_FRAME_DONE   11   // Frame done flag
#define PIN_ROW_ZONE_0   12   // Row zone bit 0
#define PIN_ROW_ZONE_1   13   // Row zone bit 1
#define PIN_COL_ZONE_0   14   // Col zone bit 0
#define PIN_COL_ZONE_1   15   // Col zone bit 1

// Input pins (from face detector results)
#define PIN_FACE_DET     16   // face_detected
#define PIN_SKIN_DET     17   // skin_found
#define PIN_EYES_DET     18   // eyes_found
#define PIN_NOSE_DET     19   // nose_found
#define PIN_MOUTH_DET    20   // mouth_found

// Camera control pins
#define PIN_CAM_PCLK     22   // Pixel clock (input from camera)
#define PIN_CAM_VSYNC    26   // Vertical sync (frame start)
#define PIN_CAM_PWDN     21   // Power down
#define PIN_CAM_RST      2    // Reset

// ============ ZONE MAPPING ============

// Map image coordinates to face regions
uint8_t get_row_zone(uint16_t y) {
  if (y < 80)      return 0b00;  // Eyes (top third)
  else if (y < 160) return 0b01;  // Nose (middle third)
  else              return 0b10;  // Mouth (bottom third)
}

uint8_t get_col_zone(uint16_t x) {
  if (x < 107)     return 0b00;  // Left
  else if (x < 214) return 0b10;  // Center
  else              return 0b01;  // Right
}

// ============ FACE DETECTOR INTERFACE ============

// Send one pixel (R, G, B channels) to the face detector
void send_pixel(uint8_t r, uint8_t g, uint8_t b, uint8_t row_zone, uint8_t col_zone) {
  uint8_t control;

  // Build control byte: [col_zone(2b) | row_zone(2b) | pixel_valid | ch_sel(2b)]

  // Send R channel (ch_sel = 0b00)
  digitalWrite_range(PIN_DATA_BASE, r);
  control = (col_zone << 6) | (row_zone << 4) | (1 << 2) | 0b00;
  digitalWrite(PIN_CH_SEL_1, (control >> 1) & 1);
  digitalWrite(PIN_CH_SEL_0, control & 1);
  digitalWrite(PIN_PIXEL_VALID, 1);
  digitalWrite(PIN_ROW_ZONE_0, (row_zone >> 0) & 1);
  digitalWrite(PIN_ROW_ZONE_1, (row_zone >> 1) & 1);
  digitalWrite(PIN_COL_ZONE_0, (col_zone >> 0) & 1);
  digitalWrite(PIN_COL_ZONE_1, (col_zone >> 1) & 1);
  delayNanoseconds(20);  // 50 MHz clock = 20ns

  // Send G channel (ch_sel = 0b01)
  digitalWrite_range(PIN_DATA_BASE, g);
  control = (col_zone << 6) | (row_zone << 4) | (1 << 2) | 0b01;
  digitalWrite(PIN_CH_SEL_1, (control >> 1) & 1);
  digitalWrite(PIN_CH_SEL_0, control & 1);
  delayNanoseconds(20);

  // Send B channel (ch_sel = 0b10)
  digitalWrite_range(PIN_DATA_BASE, b);
  control = (col_zone << 6) | (row_zone << 4) | (1 << 2) | 0b10;
  digitalWrite(PIN_CH_SEL_1, (control >> 1) & 1);
  digitalWrite(PIN_CH_SEL_0, control & 1);
  delayNanoseconds(20);

  // Clear pixel_valid
  digitalWrite(PIN_PIXEL_VALID, 0);
  delayNanoseconds(20);
}

// Signal end of frame
void frame_done() {
  digitalWrite(PIN_FRAME_DONE, 1);
  delayNanoseconds(20);
  digitalWrite(PIN_FRAME_DONE, 0);
  delayNanoseconds(20);
}

// Read detection results
struct DetectionResult {
  bool face_detected;
  bool skin_found;
  bool eyes_found;
  bool nose_found;
  bool mouth_found;
};

DetectionResult read_results() {
  DetectionResult result;
  result.face_detected = digitalRead(PIN_FACE_DET) != 0;
  result.skin_found    = digitalRead(PIN_SKIN_DET) != 0;
  result.eyes_found    = digitalRead(PIN_EYES_DET) != 0;
  result.nose_found    = digitalRead(PIN_NOSE_DET) != 0;
  result.mouth_found   = digitalRead(PIN_MOUTH_DET) != 0;
  return result;
}

// ============ CAMERA INTERFACE (STUB) ============

// NOTE: OV7670 camera control requires I2C and complex register configuration.
// This is a minimal stub. See OV7670 datasheet for full implementation.

void camera_init() {
  // Power on
  digitalWrite(PIN_CAM_PWDN, 0);
  delay(100);

  // Reset
  digitalWrite(PIN_CAM_RST, 0);
  delay(10);
  digitalWrite(PIN_CAM_RST, 1);
  delay(100);

  // TODO: Initialize I2C and configure camera registers
  // This requires: I2C communication, register writes for RGB565 mode, etc.
  // Refer to OV7670 datasheet for register values
  Serial.println("Camera initialized (stub - configure I2C separately)");
}

// Simulate pixel data (in real implementation, read from camera FIFO)
uint16_t read_camera_pixel() {
  // TODO: Replace with actual camera data read
  // For testing: return a fixed pixel value
  static uint8_t pattern = 0;
  pattern++;

  // Return RGB565 (R=200, G=150, B=100) as test pattern
  uint8_t r = (200 >> 3) & 0x1F;  // 5-bit
  uint8_t g = (150 >> 2) & 0x3F;  // 6-bit
  uint8_t b = (100 >> 3) & 0x1F;  // 5-bit
  return (r << 11) | (g << 5) | b;
}

// Convert RGB565 to RGB888
void rgb565_to_rgb888(uint16_t rgb565, uint8_t *r, uint8_t *g, uint8_t *b) {
  *r = ((rgb565 >> 11) & 0x1F) << 3;
  *g = ((rgb565 >> 5) & 0x3F) << 2;
  *b = (rgb565 & 0x1F) << 3;
}

// ============ MAIN LOOP ============

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("=== Face Detection Chip Test ===");

  // Initialize output pins
  for (int i = PIN_DATA_BASE; i < PIN_DATA_BASE + 8; i++) {
    pinMode(i, OUTPUT);
    digitalWrite(i, 0);
  }
  pinMode(PIN_CH_SEL_0, OUTPUT);
  pinMode(PIN_CH_SEL_1, OUTPUT);
  pinMode(PIN_PIXEL_VALID, OUTPUT);
  pinMode(PIN_FRAME_DONE, OUTPUT);
  pinMode(PIN_ROW_ZONE_0, OUTPUT);
  pinMode(PIN_ROW_ZONE_1, OUTPUT);
  pinMode(PIN_COL_ZONE_0, OUTPUT);
  pinMode(PIN_COL_ZONE_1, OUTPUT);

  // Initialize input pins
  pinMode(PIN_FACE_DET, INPUT);
  pinMode(PIN_SKIN_DET, INPUT);
  pinMode(PIN_EYES_DET, INPUT);
  pinMode(PIN_NOSE_DET, INPUT);
  pinMode(PIN_MOUTH_DET, INPUT);

  // Initialize camera
  pinMode(PIN_CAM_PCLK, INPUT);
  pinMode(PIN_CAM_VSYNC, INPUT);
  pinMode(PIN_CAM_PWDN, OUTPUT);
  pinMode(PIN_CAM_RST, OUTPUT);
  camera_init();

  Serial.println("Initialization complete");
}

void loop() {
  Serial.println("\n--- Frame capture ---");

  uint32_t pixel_count = 0;
  unsigned long start_time = millis();

  // Stream a frame
  for (uint16_t y = 0; y < FRAME_HEIGHT; y++) {
    for (uint16_t x = 0; x < FRAME_WIDTH; x++) {
      // Read pixel from camera
      uint16_t rgb565 = read_camera_pixel();
      uint8_t r, g, b;
      rgb565_to_rgb888(rgb565, &r, &g, &b);

      // Get zone for this pixel
      uint8_t row_zone = get_row_zone(y);
      uint8_t col_zone = get_col_zone(x);

      // Send to face detector
      send_pixel(r, g, b, row_zone, col_zone);
      pixel_count++;
    }
  }

  // Signal frame complete
  frame_done();

  unsigned long elapsed = millis() - start_time;
  Serial.print("Streamed ");
  Serial.print(pixel_count);
  Serial.print(" pixels in ");
  Serial.print(elapsed);
  Serial.println(" ms");

  // Read results
  DetectionResult result = read_results();

  Serial.println("Results:");
  Serial.print("  Face: ");
  Serial.println(result.face_detected ? "DETECTED" : "NOT detected");
  Serial.print("  Skin: ");
  Serial.println(result.skin_found ? "yes" : "no");
  Serial.print("  Eyes: ");
  Serial.println(result.eyes_found ? "yes" : "no");
  Serial.print("  Nose: ");
  Serial.println(result.nose_found ? "yes" : "no");
  Serial.print("  Mouth: ");
  Serial.println(result.mouth_found ? "yes" : "no");

  delay(2000);
}

// ============ HELPER FUNCTIONS ============

// Write 8-bit value to GPIO 0-7
void digitalWrite_range(uint8_t base_pin, uint8_t value) {
  for (int i = 0; i < 8; i++) {
    digitalWrite(base_pin + i, (value >> i) & 1);
  }
}

// Delay in nanoseconds (approximate - not cycle-accurate on Arduino)
void delayNanoseconds(uint32_t ns) {
  // On RP2040 at 125 MHz, this is very approximate
  // For production use, consider using hardware SPI or GPIO clock outputs
  if (ns >= 1000) {
    delayMicroseconds(ns / 1000);
  }
}
