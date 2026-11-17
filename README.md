# WIZnet ArduCAM Stream

Firmware 1.0.0 · [한국어](README_kor.md)

Turns a W6300-EVB-Pico2 and a DVP camera module into a network camera you
watch in a browser over **HTTPS**, with a login. The W6300 chip handles
TCP/IP in hardware, so the RP2350 spends its time on the camera and on
encryption.

```
 DVP camera ──8-bit parallel──►  W6300-EVB-Pico2  ──Ethernet──►  browser
 (B0554, OV2640)                 (HTTPS server)      https://192.168.11.7/
```

## Cameras

| Camera | Build option `CAMERA_MODULE` | Default size | Measured | Tested |
|---|---|---|---|---|
| **Arducam Quick-Bootup 3MP DVP (B0554)** — reference | `arducam_b0554` | 1280x720 | **30 fps** | ✅ |
| OV2640 DVP module | `ov2640_dvp` | 800x600 | 17 fps | ✅ |
| OV3660 DVP module | `ov3660_dvp_module` | — | — | ⬜ planned: pin map only |

✅ tested on hardware · ⬜ not yet. The fps numbers are measured over HTTPS
with one viewer; see [Test results](docs/test-results.md).

### Why there is no prebuilt firmware

HTTPS needs a **private key** inside the camera. Whoever has the key can
pretend to be the camera.

A prebuilt `.uf2` file would put the same key in every camera, and anyone who
downloaded the file would have it.

So you build the firmware yourself. The build makes a new key and
certificate for your camera automatically — there is no separate key step.

## Quick start

| Step | Contents |
|---|---|
| 1 | Wire the camera |
| 2 | Build the firmware |
| 3 | Flash it and set the PC address |
| 4 | Trust the certificate once |
| 5 | Create the admin account and watch |

### What you need

- W6300-EVB-Pico2, a USB cable and an Ethernet cable
- A camera module from the table above, and jumper wires
- A PC with Git, CMake, the Arm GNU toolchain and Python 3 — see
  [Build and security](docs/build-and-security.md#what-to-install)
- A serial terminal, for example [Tera Term](https://teratermproject.github.io)

## Step 1: Wire the camera

| Camera pin | W6300-EVB-Pico2 | Note |
|---|---|---|
| 3V3 / VCC | 3V3(OUT) | check your module's supply voltage |
| GND | GND | |
| SDA (SIOD) | GP0 | SCCB data |
| SCL (SIOC) | GP1 | SCCB clock |
| VSYNC | GP4 | |
| D0 … D7 | GP5 … GP12 | D0 on GP5, D7 on GP12 |
| PCLK | GP13 | |
| HREF | GP14 | |
| PWDN | GP27 | |
| XCLK | GP26 | **OV2640 only.** The B0554 has its own clock |

> **D0–D7, PCLK and HREF must stay on GP5–GP14, in this order.** The
> capture reads these ten pins as one block, so a single swapped wire shifts
> every byte of the picture. GP15–GP22 are taken by the W6300 on the board.

**SCCB** is the camera's control bus, almost the same as I2C. **DVP** is the
8-bit parallel bus the picture comes over: one byte on D0–D7 for every PCLK
pulse, framed by VSYNC (frame) and HREF (line).

## Step 2: Build the firmware

```bash
git clone --recursive https://github.com/theoim/WIZnet_ArduCAM_Stream.git
cd WIZnet_ArduCAM_Stream
python -m pip install cryptography

cmake -S . -B build_b0554 -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release -DCAMERA_MODULE=arducam_b0554
cmake --build build_b0554 --target camera_stream_https
```

For the OV2640, use `-DCAMERA_MODULE=ov2640_dvp` and another build
directory such as `build_ov2640`. `"MinGW Makefiles"` is for Windows; on
Linux or macOS leave out `-G` (see [Build and security](docs/build-and-security.md)).

The first `cmake` line also makes the camera's certificate and prints this:

```
[cert] created CA      C:\Users\you\.camera-stream-ca\ca.crt
[cert] camera certificate for https://192.168.11.7/ -> .../https_cert.c
[cert] To open the camera page without a browser warning, trust the CA once on
[cert] the viewing PC (only needed the first time):
[cert]   Windows : certutil -addstore -user Root "C:\Users\you\.camera-stream-ca\ca.crt"
```

Keep that output; Step 4 uses the trust command.

The firmware is `build_b0554/examples/camera_stream/camera_stream_https.uf2`.

## Step 3: Flash it and set the PC address

1. Hold **BOOTSEL** on the board and plug in the USB cable. A drive appears.
2. Drag `camera_stream_https.uf2` onto the drive. The board restarts.
3. Connect the Ethernet cable from the board to the PC.

| Item | Value |
|---|---|
| Camera address | `https://192.168.11.7/` |
| Subnet mask | `255.255.255.0` |
| Gateway | `192.168.11.1` |

The camera has a **fixed address**; it does not use DHCP (automatic
addresses). Set the PC's Ethernet adapter to a static address on the same
network, for example `192.168.11.100` / `255.255.255.0`.

> **Check with ping first.** `ping 192.168.11.7` should answer before you
> open the browser.

To use another address, build with `-DCAM_IP=192.168.1.50`. The certificate
is made for that address at the same time.

## Step 4: Trust the certificate once

Run the trust command the build printed, on the PC that will open the camera
page. On Windows:

```
certutil -addstore -user Root "%USERPROFILE%\.camera-stream-ca\ca.crt"
```

**What it is:** the build made two things — a small certificate authority
(CA) of your own in `~/.camera-stream-ca`, and the camera's certificate,
signed by that CA.

**Why:** a browser only trusts certificates signed by a CA it knows. Your
own CA is unknown until you add it, so without this step the browser shows a
security warning.

**So:** trust the CA once per PC. Every camera you build later is signed by
the same CA, so the browser keeps trusting them. Keep `ca.key` private: anyone
with it can make certificates your PC accepts.

Restart the browser after this step. Firefox has its own list: Settings →
Privacy & Security → Certificates → View Certificates → Authorities → Import.

## Step 5: Create the admin account and watch

The camera has **no default password**. The first account is created in
**setup mode**, which only someone at the board's USB port can open.

1. Open `https://192.168.11.7/`. The page says **Set up this camera**.
2. Open the board's COM port in the terminal and type `setup`. The board
   answers:

   ```
   [auth] setup mode OPEN for 5 minutes - create the admin in the browser
   ```

3. Reload the page. Choose a user name and a password of at least
   10 characters, then **Create admin**.
4. The picture appears. In the **Access & accounts** panel you can add a
   **viewer** account, which can watch but not change settings.

> **Turn on local echo and send CR+LF.** The board does not echo what you
> type. In Tera Term: Setup → Terminal → Transmit `CR+LF`, and check Local
> echo.

## Troubleshooting

### The browser shows a security warning

The CA is not trusted on this PC, or the browser was not restarted. Do
Step 4 again. If you rebuilt in a **new** build directory with a different
`CAM_IP`, the page must be opened at that address.

### The page says "No admin account yet"

Setup mode is closed. Type `setup` on the USB console and reload within
5 minutes.

### The picture freezes or keeps reconnecting

The camera sends **one live stream at a time**. Two tabs in the same browser
share one login, so they keep taking the stream from each other. Close the
other tabs, wait about 30 s for their connections to time out, and reload.

If a different login is already watching, the page cannot get the stream
(`409 Conflict`) until that one stops — except the admin, who takes it over
from a viewer.

### Nothing on the page, `ping` fails

The PC is not on `192.168.11.x`, or the cable is not connected. Check the
PC's static address.

### Black picture or no frames

Check the wiring of Step 1, especially D0–D7 and PCLK. For the OV2640, XCLK
on GP26 must be connected. Build `camera_probe` to check the camera alone —
see [Reference](docs/reference.md#camera_probe).

### `cmake` stops with "HTTPS certificate not made"

Python's `cryptography` package is missing. Run
`python -m pip install cryptography` and run `cmake` again.

### Forgot the admin password

Type `factory-reset` on the USB console, then `yes` within 10 s. The
accounts and saved camera settings are erased and the board restarts as new.
Then do Step 5 again.

## Known limitations

| What | Why | What to do |
|---|---|---|
| One live stream at a time | A design choice: the camera's whole frame rate goes to one viewer, and who may watch stays simple to reason about. | Watch from one page. The admin can take the stream over from the viewer. |
| Fixed IP and MAC address, no DHCP | Both are build-time settings, so the camera is always at the same place without a DHCP server. | Use `-DCAM_IP`. For two cameras on one network, also change `NET_MAC_ADDR` in `stream_config.h`. |
| Setup and factory reset need the USB console | The board has no button for them, and the USB port means physical access. | Keep the board where strangers cannot plug into it. |
| The private key is inside the firmware file | The camera needs it to serve HTTPS. | Do not share the `.uf2` file or the build directory. Build once per camera. |
| The certificate expires after 397 days | Browsers refuse server certificates valid for longer. | Delete `https_cert.c` in the build directory, run `cmake` again, rebuild and flash. |
| OV3660 is not supported yet | No working OV3660 hardware has been tested. | The pin map is in `cam/modules/ov3660_dvp_module.h`; the driver is planned. |

## Going further

| Document | Read it when |
|---|---|
| [Build and security](docs/build-and-security.md) | You want another address, Linux/macOS, or to know what the security covers |
| [Reference](docs/reference.md) | You need the console commands, the HTTP API, or want to add a camera |
| [Test results](docs/test-results.md) | You want the measurements behind the numbers above |

## License

Apache-2.0 for this project's code. Third-party components keep their own
licenses — Mbed TLS (Apache-2.0), Raspberry Pi Pico SDK (BSD-3-Clause),
WIZnet ioLibrary (MIT), OV2640 register tables from ArduCAM (MIT). See
[NOTICE](NOTICE).
