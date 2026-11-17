/*
 * Copyright (c) 2026 WIZnet Co., Ltd.
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * @file    ov3660_dvp_module.h
 * @brief   Pin map: OV3660 DVP module on W6300-EVB-Pico2 — PLANNED, NOT VERIFIED.
 *
 * Status: no OV3660 driver in this tree yet and no hardware test. camera_probe
 * can already identify the chip (SCCB 0x3C, 16-bit registers); camera_stream
 * is skipped for this module until the driver lands.
 *
 * Wiring follows the same DVP layout as the other modules here. The clock and
 * control choices come from the OV3660 reference in the WIZnet wsm_driver
 * camera_stream example (XIAO ESP32-S3 Sense, esp32-camera): the module needs
 * an external XCLK, 20 MHz there, and PWDN/RESET are not wired — the sensor is
 * reset over SCCB. Confirm all of this on the module you use.
 */

#ifndef CAM_MODULE_OV3660_DVP_MODULE_H
#define CAM_MODULE_OV3660_DVP_MODULE_H

#define CAM_MODULE_NAME      "OV3660 DVP module (planned, not verified)"

#define CAM_PIN_SDA          0
#define CAM_PIN_SCL          1
#define CAM_PIN_VSYNC        4
#define CAM_PIN_D0           5       /* D0..D7 = GP5..GP12, PCLK GP13, HREF GP14 */
#define CAM_PIN_PWDN         (-1)    /* not wired in the reference */
#define CAM_PIN_RESET        (-1)    /* not wired; reset over SCCB */

#define CAM_PIN_XCLK         26      /* PWM, as for the OV2640 module */
#define CAM_XCLK_HZ          (20 * 1000 * 1000)

#define CAM_SCCB_HZ          (100 * 1000)

#endif
