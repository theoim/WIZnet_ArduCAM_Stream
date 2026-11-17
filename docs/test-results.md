# Test results

[README](../README.md) · [한국어](test-results_kor.md)

Measured 2026-11-17 on W6300-EVB-Pico2 boards, PC (Windows 11) on the same
Ethernet network, HTTPS with one logged-in viewer.

## Frame rate

A script logs in, reads `/stream` for 30 s and counts complete JPEG frames.

| Camera | Size | Build | Frames in 30 s | fps | Avg. frame | Data rate | Dropped |
|---|---|---|---|---|---|---|---|
| B0554 | 1280x720 | Release, 1.0.0 | 907 | **30.15** | 24.8 KB | 6.2 Mbps | 0 |
| B0554 | 1280x720 | Release | 905 | 30.16 | 24.1 KB | 6.0 Mbps | 0 |
| B0554 | 1280x720 | Debug | 906 | 30.16 | 24.2 KB | 6.0 Mbps | 0 |
| OV2640 | 800x600 | Release, 1.0.0 | 523 | **17.28** | 12.8 KB | 1.8 Mbps | 0 |
| OV2640 | 800x600 | Release | — | 17.28 | — | — | 0 |
| OV2640 | 800x600 | Debug | — | 17.28 | — | — | 0 |

**What limits the rate:** the camera, not the network or the encryption.
The board reports per frame how long it waits for the frame to start
(`vsync_ms`), reads it (`read_ms`) and sends it (`send_ms`):

| Camera | vsync_ms | read_ms | send_ms |
|---|---|---|---|
| B0554 1280x720 | 10 | 22 | 10 |
| OV2640 800x600 | 10 | 47 | 5 |

Core 1 captures the next frame into a second buffer while core 0 sends the
last one, so the frame period is the longer of reading and sending, not
their sum. Sending takes 5–10 ms, less than reading on both cameras.

The B0554 delivers 30 frames per second at 720p and the board keeps every
one. The OV2640 takes 47 ms to clock out one 800x600 frame, so it cannot go
much above 20 frames per second.

**So** Debug and Release give the same frame rate on both cameras. Either
works; the README uses Release.

## Regression

`test/net_regression.py`, 88 checks over HTTPS: routes, request limits,
malformed requests, login, roles, CSRF, session and lockout.

| Camera | Firmware | Result |
|---|---|---|
| B0554 | 1.0.0 Release | **88/88**, three runs in a row |
| OV2640 | 1.0.0 Release | **88/88**, three runs in a row |

Memory in use did not change across a run (272,320 of 532,480 bytes of SRAM
before and after on the B0554, 272,328 on the OV2640).

### Found during this test: lost connections

**What:** while the regression ran, one connection in a few dozen was reset
during the TLS handshake — each run in a different test. The console showed
`Socket 1 listen failed` at the same moment.

**Why:** after a connection closes, the board puts the socket back into
LISTEN. If a new client's SYN arrives in the same instant, the W6300 has
already moved the socket on to SYNRECV. The stock ioLibrary `listen()`
reads the state once, sees "not LISTEN", and closes the socket — the client
gets a reset (ioLibrary issue #127).

**What was done:** `net/wiz_transport.c` arms listeners with its own
`wt_listen()`, which counts SYNRECV and ESTABLISHED as success and never
closes the socket. On the B0554, 0 of 5 runs passed before the fix and 4 of 4
after it; the OV2640 passed 3 of 3 after it.

## TLS

From the board console (B0554 image, RP2350 at 200 MHz):

| Handshake | CPU | Wall clock |
|---|---|---|
| Full (ECDHE-ECDSA P-256) | 166 ms | 181 ms |
| Resumed (session ticket) | 4–9 ms | 4–28 ms |

The page reconnects with a resumed handshake, so after the first one the
cost is a few milliseconds.

## Login

PBKDF2 with 5,000 iterations: 357 ms per login on the board (console
`[auth] login … (357 ms)`).
