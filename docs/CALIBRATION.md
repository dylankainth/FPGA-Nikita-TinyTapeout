# Threshold Calibration Guide

This guide explains how to tune the face detection thresholds for your specific lighting conditions and camera setup.

## Overview

The face detector uses three types of thresholds:

1. **Skin Tone** — RGB ranges for skin pixel classification
2. **Darkness** — Brightness thresholds for eye/feature detection
3. **Geometry** — Feature size and balance constraints

All thresholds are defined in `src/project.v` and require design recompilation to change.

## Test Images

Before calibrating, prepare test images:

### Good Test Set
- **Face (frontal)** — Clear face, neutral lighting, 40-60 cm from camera
- **Face (angle)** — Face at 45° angle
- **Face (dim)** — Same face under dim lighting (no shadows)
- **Background** — Empty scene without faces (walls, objects)
- **Skin objects** — Non-face skin (arm, hand) to detect false positives

### Process Each Test Image

For each test image, capture a frame and record:
- `face_detected` flag
- Individual feature flags (skin, eyes, nose, mouth)
- Lighting level (lux, or subjective: bright/normal/dim)
- Comments (why detected/missed, etc.)

## 1. Skin Tone Threshold Tuning

The skin classifier is defined in `src/project.v` lines 49-55:

```verilog
wire skin_px = (
    (r_reg > 8'd95)  && (g_reg > 8'd40)  && (b_now > 8'd20)  &&
    (r_reg > g_reg)  && (r_reg > b_now)  &&
    ((r_reg - g_reg) > 8'd15) &&
    ((r_reg - b_now) > 8'd20) &&
    (r_reg < 8'd240) && (g_reg < 8'd200) && (b_now < 8'd170)
);
```

### Typical Values by Lighting

| Condition | R min | R max | G min | G max | B min | B max |
|-----------|-------|-------|-------|-------|-------|-------|
| Bright    | 110   | 220   | 50    | 180   | 30    | 150   |
| Normal    | 95    | 240   | 40    | 200   | 20    | 170   |
| Dim       | 80    | 255   | 30    | 220   | 15    | 185   |

### Tuning Steps

1. **Capture a clear face image** in your target lighting
2. **Check skin detection**: If all face pixels are classified as skin:
   - Thresholds are correct ✓
3. **If no face pixels detected:**
   - Lower all minimums (R_min, G_min, B_min by 10-20)
   - Increase all maximums (R_max, G_max, B_max by 10-20)
   - Recompile and test
4. **If too many false positives** (non-face pixels detected as skin):
   - Increase minimums
   - Decrease maximums
   - Increase differential thresholds (R-G, R-B)

### R-G and R-B Differentials

These detect the orange-ness of skin:

- **R-G threshold** (default: 15) — Controls red vs green discrimination
  - Increase to eliminate yellow/green tones (higher tolerance)
  - Decrease for stricter orange requirement
- **R-B threshold** (default: 20) — Controls red vs blue discrimination
  - Increase to accept cooler skin tones
  - Decrease for warmer skin only

**For different skin tones:**
- **Light skin (European):** Use defaults or increase R-G slightly
- **Warm skin (Latin, African):** Use defaults
- **Cool skin (Asian):** Decrease R-G, increase R-B
- **Very dark skin:** Increase all minimums significantly

## 2. Feature Detection Threshold Tuning

Feature detection uses brightness thresholds (sum of R+G+B):

```verilog
wire [9:0] brightness = {2'b0, r_reg} + {2'b0, g_reg} + {2'b0, b_now};
wire dark_eye  = (brightness < 10'd150);
wire dark_feat = (brightness < 10'd200);
```

### Typical Values

| Feature | Typical | Dim | Bright |
|---------|---------|-----|--------|
| Eyes    | 150     | 100 | 180    |
| Nose    | 200     | 150 | 230    |
| Mouth   | 200     | 150 | 230    |

### Tuning Steps

1. **Capture a face** with good eyes and mouth visibility
2. **Check darkness detection:**
   - If eyes are detected: ✓ correct
   - If eyes missed: lower dark_eye threshold (120, 100, 80...)
3. **Check nose/mouth:**
   - If detected: ✓ correct
   - If missed: lower dark_feat threshold
4. **Avoid false positives:**
   - If shadows detected as eyes: raise dark_eye threshold
   - If noisy regions detected: raise dark_feat threshold

## 3. Geometry Constraint Tuning

Geometry constraints ensure detected features look face-like:

```verilog
wire eyes_ok = (left_eye_dark  > 18'd50)    &&  // Min dark pixels (50)
               (right_eye_dark > 18'd50)    &&
               (left_eye_dark  < 18'd50000) &&  // Max (prevent saturation)
               (right_eye_dark < 18'd50000) &&
               (left_eye_dark  > (right_eye_dark >> 2)) &&  // Balance: L > R/4
               (right_eye_dark > (left_eye_dark  >> 2));    // Balance: R > L/4

wire nose_ok  = (nose_dark  > 18'd50) && (nose_dark  < 18'd100000);

wire mouth_ok = (mouth_dark > 18'd50) &&
                (mouth_dark < 18'd100000) &&
                (mouth_dark > nose_dark);  // Mouth > nose (hierarchy)
```

### Tuning Steps

1. **Eye balance (>>2 = 4:1 ratio):**
   - If rejecting valid faces: reduce ratio (>> 3 = 8:1)
   - If accepting asymmetric objects: increase ratio (>> 1 = 2:1)

2. **Feature minimums (default: 50):**
   - Increase if false positives (small noise detected as features)
   - Decrease if missing features (raise = 100, 150...)

3. **Feature maximums (default: 50000 for eyes, 100000 for nose/mouth):**
   - Usually don't need tuning
   - Increase if large frames reject face
   - Decrease if face too close to camera

4. **Mouth > Nose constraint:**
   - Always enforced (mouth should be darker than nose)
   - If rejected: check lighting (nose may be shadowed)

## 4. Full Tuning Workflow

### Phase 1: Get Any Face Detection

1. Start with default thresholds
2. Capture a clear face image
3. If detected: continue to Phase 2
4. If not detected:
   - Reduce all skin tone minimums by 20
   - Reduce darkness thresholds by 50
   - Recompile and test

### Phase 2: Improve Accuracy

1. Test on 5-10 face images
2. Measure false negatives (faces missed)
   - If >2 missed: lower thresholds
3. Measure false positives (non-faces detected)
   - If >1 false positive: raise thresholds
4. Iterate, adjusting one threshold at a time

### Phase 3: Optimize for Your Environment

1. Test under different lighting (bright, normal, dim)
2. For each lighting condition, document which thresholds work
3. Choose thresholds that cover your expected range
4. If range is wide, consider dynamic threshold selection (in microcontroller)

## Diagnostic Output

To debug threshold issues, you can add serial output in your Arduino code:

```cpp
// Log skin detection stats
void analyze_frame() {
  uint32_t skin_pixels = 0;
  uint32_t dark_pixels = 0;
  
  // Capture and analyze
  for (uint16_t y = 0; y < FRAME_HEIGHT; y++) {
    for (uint16_t x = 0; x < FRAME_WIDTH; x++) {
      uint16_t rgb565 = read_camera_pixel();
      uint8_t r, g, b;
      rgb565_to_rgb888(rgb565, &r, &g, &b);
      
      // Check if would be classified as skin
      if (is_skin(r, g, b)) skin_pixels++;
      
      // Check if would be dark
      uint16_t brightness = r + g + b;
      if (brightness < 150) dark_pixels++;
    }
  }
  
  Serial.print("Skin pixels: ");
  Serial.println(skin_pixels);
  Serial.print("Dark pixels: ");
  Serial.println(dark_pixels);
}

bool is_skin(uint8_t r, uint8_t g, uint8_t b) {
  return (r > 95) && (g > 40) && (b > 20) &&
         (r > g) && (r > b) &&
         ((r - g) > 15) && ((r - b) > 20) &&
         (r < 240) && (g < 200) && (b < 170);
}
```

This helps verify thresholds are being met before recompiling the chip.

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Always detects face | Thresholds too loose | Raise skin tone minimums |
| Never detects face | Thresholds too strict | Lower skin tone minimums |
| Detects skin but not full face | Feature thresholds too strict | Lower darkness thresholds |
| False positives on objects | Geometry too loose | Increase feature minimums |
| Detects only well-lit faces | Thresholds tuned for bright | Document as bright-only; adjust minimums |
| Fails at high resolution | Too few dark pixels per zone | Adjust based on resolution |

## Recommended Starting Points

### Consumer Lighting (Indoor)
```
Skin: R(95-240), G(40-200), B(20-170), R-G>15, R-B>20
Eyes: brightness < 150
Nose: brightness < 200
Mouth: brightness < 200, > nose
Features: each > 50 pixels
```

### Professional Lighting (Studio)
```
Skin: R(110-220), G(50-180), B(30-150), R-G>20, R-B>25
Eyes: brightness < 120
Nose: brightness < 180
Mouth: brightness < 180, > nose
Features: each > 100 pixels (higher threshold)
```

### Low Light (Dim Room)
```
Skin: R(80-255), G(30-220), B(15-185), R-G>10, R-B>15
Eyes: brightness < 180
Nose: brightness < 230
Mouth: brightness < 230, > nose
Features: each > 30 pixels (lower threshold)
```

## Verification Checklist

After calibration, verify:
- [ ] Clear face detected in target lighting
- [ ] No false positives on backgrounds
- [ ] Works across expected face distances (30-80 cm)
- [ ] Works for multiple skin tones
- [ ] Accepted face images 85%+ of the time
- [ ] Rejected non-face images 95%+ of the time
- [ ] Documented thresholds used
- [ ] Estimated accuracy in your environment

## Need Help?

If thresholds don't converge, check:
1. **Camera focus** — Blurry images won't have clear eye/nose boundaries
2. **Lighting consistency** — Shadows or glare can confuse classifier
3. **Resolution** — Very high resolution needs scaled thresholds
4. **Zone mapping** — Verify zones match your image dimensions
5. **Sample size** — 5-10 images may not be enough; test with 20+

Consider collecting actual images in your environment and building a ground-truth dataset to validate accuracy empirically.
