import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

ROW_EYE    = 0b00
ROW_NOSE   = 0b01
ROW_MOUTH  = 0b10
COL_LEFT   = 0b00
COL_RIGHT  = 0b01
COL_CENTRE = 0b10

async def send_pixel(dut, r, g, b, row_zone=0, col_zone=0):
    """Send one complete pixel (R then G then B channel)."""
    for ch, val in enumerate([r, g, b]):
        dut.ui_in.value  = val
        dut.uio_in.value = (col_zone << 6) | (row_zone << 4) | (1 << 2) | ch
        await RisingEdge(dut.clk)
    dut.uio_in.value = 0

async def end_frame(dut):
    dut.uio_in.value = (1 << 3)  # frame_done
    await RisingEdge(dut.clk)
    dut.uio_in.value = 0
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_multi_frame_reset(dut):
    """Test that each frame resets counters (no accumulation across frames)."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value  = 0
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    await Timer(30, unit="ns")
    dut.rst_n.value  = 1

    # Frame 1: Minimal face (just barely passes)
    for _ in range(200):
        await send_pixel(dut, 200, 150, 100)  # skin
    for _ in range(100):
        await send_pixel(dut, 50, 50, 200)    # background
    for _ in range(60):
        await send_pixel(dut, 30, 30, 30, ROW_EYE, COL_LEFT)
    for _ in range(60):
        await send_pixel(dut, 30, 30, 30, ROW_EYE, COL_RIGHT)
    for _ in range(60):
        await send_pixel(dut, 50, 50, 50, ROW_NOSE, COL_CENTRE)
    for _ in range(70):
        await send_pixel(dut, 50, 50, 50, ROW_MOUTH, COL_CENTRE)
    
    await end_frame(dut)
    out1 = int(dut.uo_out.value)
    frame1_face = (out1 & 0x01) != 0
    dut._log.info(f"Frame 1: face_detected = {frame1_face}")

    # Frame 2: No skin (should not detect face)
    for _ in range(300):
        await send_pixel(dut, 50, 50, 200)  # blue background
    
    await end_frame(dut)
    out2 = int(dut.uo_out.value)
    frame2_face = (out2 & 0x01) != 0
    dut._log.info(f"Frame 2: face_detected = {frame2_face}")
    
    assert not frame2_face, f"Frame 2 should have no face due to reset, got {bin(out2)}"
    dut._log.info("PASS — Frame 2 correctly reset")

@cocotb.test()
async def test_held_frame_done(dut):
    """Test frame_done edge detection with held signal."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value  = 0
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    await Timer(30, unit="ns")
    dut.rst_n.value  = 1

    # Send minimal face
    for _ in range(200):
        await send_pixel(dut, 200, 150, 100)
    for _ in range(100):
        await send_pixel(dut, 50, 50, 200)
    for _ in range(60):
        await send_pixel(dut, 30, 30, 30, ROW_EYE, COL_LEFT)
    for _ in range(60):
        await send_pixel(dut, 30, 30, 30, ROW_EYE, COL_RIGHT)
    for _ in range(60):
        await send_pixel(dut, 50, 50, 50, ROW_NOSE, COL_CENTRE)
    for _ in range(70):
        await send_pixel(dut, 50, 50, 50, ROW_MOUTH, COL_CENTRE)
    
    # Hold frame_done high for multiple cycles
    dut.uio_in.value = (1 << 3)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)  # Hold for 3 cycles
    dut.uio_in.value = 0
    await RisingEdge(dut.clk)
    
    out = int(dut.uo_out.value)
    dut._log.info(f"Held frame_done: uo_out = {bin(out)}")
    
    # Should still have valid results (not over-incremented)
    skin_det = (out & 0x02) != 0
    assert skin_det, "Should still detect after held frame_done"
    dut._log.info("PASS — Held frame_done handled correctly")

@cocotb.test()
async def test_imbalanced_eyes(dut):
    """Test eye balance check (left/right symmetry)."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value  = 0
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    await Timer(30, unit="ns")
    dut.rst_n.value  = 1

    # Send skin and features but imbalanced eyes
    for _ in range(200):
        await send_pixel(dut, 200, 150, 100)  # skin
    for _ in range(100):
        await send_pixel(dut, 50, 50, 200)    # background
    for _ in range(200):  # left eye: 200
        await send_pixel(dut, 30, 30, 30, ROW_EYE, COL_LEFT)
    for _ in range(30):   # right eye: 30 (too imbalanced, right < left/4 = 50)
        await send_pixel(dut, 30, 30, 30, ROW_EYE, COL_RIGHT)
    for _ in range(60):
        await send_pixel(dut, 50, 50, 50, ROW_NOSE, COL_CENTRE)
    for _ in range(70):
        await send_pixel(dut, 50, 50, 50, ROW_MOUTH, COL_CENTRE)
    
    await end_frame(dut)
    out = int(dut.uo_out.value)
    face_det = (out & 0x01) != 0
    eyes_det = (out & 0x04) != 0
    
    dut._log.info(f"Imbalanced eyes: face_detected={face_det}, eyes_detected={eyes_det}")
    assert not face_det, "Should not detect face with imbalanced eyes"
    assert not eyes_det, "Should not detect eyes when imbalanced"
    dut._log.info("PASS — Imbalanced eyes correctly rejected")
