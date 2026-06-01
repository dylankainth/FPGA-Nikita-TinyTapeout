import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Zone constants matching pin mapping
ROW_EYE   = 0b00
ROW_NOSE  = 0b01
ROW_MOUTH = 0b10
COL_LEFT  = 0b00
COL_RIGHT = 0b01
COL_CENTRE = 0b10

async def send_pixel(dut, r, g, b, row_zone=0, col_zone=0):
    """Send one complete pixel (R then G then B channel)."""
    for ch, val in enumerate([r, g, b]):
        dut.ui_in.value  = val
        # uio_in: [7:6]=col_zone, [5:4]=row_zone, [3]=frame_done,
        #         [2]=pixel_valid, [1:0]=ch_sel
        dut.uio_in.value = (col_zone << 6) | (row_zone << 4) | (1 << 2) | ch
        await RisingEdge(dut.clk)
    dut.uio_in.value = 0

async def end_frame(dut):
    dut.uio_in.value = (1 << 3)  # frame_done
    await RisingEdge(dut.clk)
    dut.uio_in.value = 0
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_face_detected(dut):
    """Send a synthetic face: skin pixels + eye/nose/mouth dark regions."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.ena.value   = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await Timer(30, units="ns")
    dut.rst_n.value = 1

    # Send 100 skin-coloured pixels (will be >5% of 200-pixel frame)
    for _ in range(100):
        await send_pixel(dut, 200, 150, 100)

    # 100 non-skin background pixels
    for _ in range(100):
        await send_pixel(dut, 50, 50, 200)

    # Eye region: 200 dark pixels each side
    for _ in range(200):
        await send_pixel(dut, 30, 30, 30, ROW_EYE, COL_LEFT)
    for _ in range(200):
        await send_pixel(dut, 30, 30, 30, ROW_EYE, COL_RIGHT)

    # Nose region: 300 dark pixels centre
    for _ in range(300):
        await send_pixel(dut, 50, 50, 50, ROW_NOSE, COL_CENTRE)

    # Mouth region: 400 dark pixels centre (more than nose → mouth_ok)
    for _ in range(400):
        await send_pixel(dut, 50, 50, 50, ROW_MOUTH, COL_CENTRE)

    await end_frame(dut)

    assert dut.uo_out.value & 0b00001 == 1, "face_detected should be high"
    assert dut.uo_out.value & 0b00010 == 2, "skin_found should be high"
    assert dut.uo_out.value & 0b00100 == 4, "eyes_found should be high"
    assert dut.uo_out.value & 0b01000 == 8, "nose_found should be high"
    assert dut.uo_out.value & 0b10000 == 16, "mouth_found should be high"
    print(f"PASS — uo_out = {bin(int(dut.uo_out.value))}")


@cocotb.test()
async def test_no_face(dut):
    """Send only background pixels — no face expected."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0; dut.ena.value = 1
    dut.ui_in.value = 0; dut.uio_in.value = 0
    await Timer(30, units="ns")
    dut.rst_n.value = 1

    for _ in range(500):
        await send_pixel(dut, 50, 100, 180)  # blue background, no skin

    await end_frame(dut)

    assert dut.uo_out.value & 0x01 == 0, "face_detected should be low"
    print("PASS — no false positive on background image")
