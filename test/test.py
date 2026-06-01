# SPDX-FileCopyrightText: © 2024 Nikita
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Zone constants matching pin mapping
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
async def test_face_detected(dut):
    """Send a synthetic face: skin pixels + eye/nose/mouth dark regions."""
    clock = Clock(dut.clk, 10, unit="ns")   # fixed: unit not units
    cocotb.start_soon(clock.start())

    dut.rst_n.value  = 0
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    await Timer(30, unit="ns")              # fixed: unit not units
    dut.rst_n.value  = 1

    # 100 skin pixels (>5% of total)
    for _ in range(100):
        await send_pixel(dut, 200, 150, 100)

    # 100 non-skin background
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

    # Mouth region: 400 dark pixels centre (more than nose)
    for _ in range(400):
        await send_pixel(dut, 50, 50, 50, ROW_MOUTH, COL_CENTRE)

    await end_frame(dut)

    # fixed: cast to int() before bitwise &
    out = int(dut.uo_out.value)
    assert out & 0b00001 == 0b00001, f"face_detected should be high, got {bin(out)}"
    assert out & 0b00010 == 0b00010, f"skin_found should be high, got {bin(out)}"
    assert out & 0b00100 == 0b00100, f"eyes_found should be high, got {bin(out)}"
    assert out & 0b01000 == 0b01000, f"nose_found should be high, got {bin(out)}"
    assert out & 0b10000 == 0b10000, f"mouth_found should be high, got {bin(out)}"
    dut._log.info(f"PASS — uo_out = {bin(out)}")


@cocotb.test()
async def test_no_face(dut):
    """Send only background pixels — no face expected."""
    clock = Clock(dut.clk, 10, unit="ns")   # fixed: unit not units
    cocotb.start_soon(clock.start())

    dut.rst_n.value  = 0
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    await Timer(30, unit="ns")              # fixed: unit not units
    dut.rst_n.value  = 1

    for _ in range(500):
        await send_pixel(dut, 50, 100, 180)  # blue background, no skin

    await end_frame(dut)

    out = int(dut.uo_out.value)             # fixed: cast to int()
    assert out & 0x01 == 0, f"face_detected should be low, got {bin(out)}"
    dut._log.info("PASS — no false positive on background image")
