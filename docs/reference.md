# Reference

[README](../README.md) · [한국어](reference_kor.md)

## USB console

Open the board's COM port at any speed (it is USB, the speed setting is
ignored). Turn on local echo and send CR+LF: the board does not echo.

| Command | What it does |
|---|---|
| `setup` | Opens setup mode for 5 minutes, only while there is no admin account |
| `factory-reset` | Asks for confirmation. Type `yes` within 10 s to erase the accounts and saved camera settings and restart. Anything else cancels |

The console also prints what the camera does: TLS handshakes, logins,
resolution changes and errors. The boot banner names the firmware and the
camera module:

```
=== WIZnet ArduCAM Stream 1.0.0 (toe <build date>)  module: Arducam Quick-Bootup 3MP DVP (B0554) ===
```

The banner is printed before most terminals have opened the port, so you
usually only see the lines that follow.

## Web page

| Panel | Who can use it | What it has |
|---|---|---|
| Picture | admin, viewer | The live stream |
| Control | admin | Start/stop, resolution, and **Link load** — extra test traffic to see how the stream holds up under load |
| Live performance | admin, viewer | Frame rate and data rate graphs |
| Access & accounts | admin | Change the admin password, set or turn off the viewer |
| Sensor controls | admin | The controls the camera driver offers (brightness, contrast, …), **Save** |

Changes on the page last until the board restarts. **Save** writes the
resolution and sensor controls to flash, and the board applies them at the
next start — only on the same camera model they were saved on.

## HTTP API

Every request goes over HTTPS. Except the login routes, each needs the
session cookie from `/api/login`. Every POST that changes something also
needs the `X-CSRF-Token` header, whose value `GET /api/auth` returns while
logged in. Form bodies are `application/x-www-form-urlencoded`.

| Method | Path | Role | What it does |
|---|---|---|---|
| GET | `/` | anyone | The page (gzip) |
| GET | `/api/auth` | anyone | Login state: `provisioned`, `setup_open`, `role`, `user`, `csrf` |
| POST | `/api/setup` | anyone, setup mode only | Create the admin: `user`, `pass` |
| POST | `/api/login` | anyone | `user`, `pass`. Sets the `cam_sid` cookie |
| POST | `/api/logout` | viewer | Ends the session |
| GET | `/stream` | viewer | MJPEG stream (`multipart/x-mixed-replace`) |
| GET | `/snapshot.jpg` | viewer | One JPEG |
| GET | `/api/status` | viewer | Frame rate, frame size, drop and TLS counters (JSON) |
| GET | `/api/controls` | viewer | The sensor controls and their ranges (JSON) |
| POST | `/api/res?v=1280x720` | admin | Change the resolution |
| POST | `/api/cam` | admin | Set controls, e.g. `brightness=1&mirror=0` |
| POST | `/api/settings/save` | admin | Save resolution and controls to flash |
| POST | `/api/start`, `/api/stop` | admin | Start or stop capturing |
| POST | `/api/reset` | admin | Reset and re-initialise the sensor |
| POST | `/api/account` | admin | `role=admin&old=…&pass=…`, or `role=viewer&user=…&pass=…`, or `role=viewer&enabled=0` |

"viewer" in the Role column means viewer or admin.

Example with Python `requests`:

```python
import requests
s = requests.Session()
s.verify = "~/.camera-stream-ca/ca.crt"          # expand ~ to your home
s.post("https://192.168.11.7/api/login", data={"user": "admin", "pass": "…"})
csrf = s.get("https://192.168.11.7/api/auth").json()["csrf"]
s.post("https://192.168.11.7/api/res?v=640x480", headers={"X-CSRF-Token": csrf})
open("shot.jpg", "wb").write(s.get("https://192.168.11.7/snapshot.jpg").content)
```

### Status codes

| Code | Meaning |
|---|---|
| 401 | Not logged in, the session ended, or a wrong user name or password at login |
| 403 | The role is too low, the `X-CSRF-Token` is missing or wrong, or `/api/setup` while setup mode is closed |
| 409 | The stream is in use by another login (`Retry-After: 10`), or `/api/setup` when an admin already exists |
| 415 | A form POST without `application/x-www-form-urlencoded` |
| 429 | Too many wrong passwords: wait 30 s |
| 400 | The request or a value is malformed, or a control value is out of range |

## Resolutions

| Camera | Sizes | Default |
|---|---|---|
| B0554 | 320x240, 640x480, 1280x720, 1600x1200, 1920x1080 | 1280x720 |
| OV2640 | 160x120, 176x144, 320x240, 352x288, 640x480, 800x600, 1024x768, 1280x1024, 1600x1200 | 800x600 |

On the OV2640, 800x600 is the sensor's native preview mode and gives the
best frame rate. 640x480 and 1024x768 and above read the full sensor array
and are slower — 640x480 was measured at 5.9 fps.

The camera reports the size it really sends in `/api/status` (`res`). Check
the frame size in KB too: a size write the sensor did not take shows up as
an unexpected frame size, not as an error.

## Pin maps

All modules use the same DVP wiring (README Step 1). They differ in clock and
power-down:

| Module file (`cam/modules/`) | XCLK | PWDN | SCCB | Status |
|---|---|---|---|---|
| `arducam_b0554.h` | on-module oscillator | GP27 | 0x1F, 200 kHz | tested |
| `ov2640_dvp.h` | GP26, 20 MHz PWM | GP27 | 0x30, 200 kHz | tested |
| `ov3660_dvp_module.h` | GP26, 20 MHz PWM | not wired | 0x3C, 100 kHz | planned, not verified |
| `ov5640_dvp_module.h` | on-module oscillator | GP27 | 0x3C, 100 kHz | probe only |

The B0554 does not show its image sensor on the bus. Only a controller on the
module answers (SCCB address `0x1F`), and the host sets the resolution by
writing one of that controller's registers. So it has its own driver
(`cam/arducam_qb/`) instead of a sensor driver.

## camera_probe

`camera_probe` checks a camera without the network:

```bash
cmake --build build_b0554 --target camera_probe
```

Flash `camera_probe.uf2`. Every 3 s it prints which SCCB addresses answered
and the chip ID of every known camera.

| Output | Meaning |
|---|---|
| A known address and chip name | The camera is wired and powered |
| `0x1F` with `SENSOR_ID 0x039E` | Arducam B0554 |
| `nothing answered` | Check 3V3 and GND, then PWDN (must be low), then XCLK for modules without an oscillator, then SDA/SCL |

## Adding a camera

The code is split in three layers, so a new camera does not touch the
network or capture code:

| Layer | What differs per camera | Where |
|---|---|---|
| Sensor driver | Chip ID, register tables, resolution and format | `cam/<sensor>/` |
| Module pin map | XCLK, PWDN, RESET, SCCB speed | `cam/modules/<module>.h` |
| Shared | SCCB access, chip probe, DVP capture, HTTPS server | `cam/cam_sccb.*`, `cam/cam_probe.*`, `capture/` |

1. Run `camera_probe` and read the SCCB address and chip ID from the real
   part, before trusting the datasheet.
2. Copy a pin map in `cam/modules/`. If the module has its own oscillator,
   set `CAM_PIN_XCLK (-1)` but still write the oscillator frequency in
   `CAM_XCLK_HZ` — sensor clock settings are calculated from it.
3. Write the driver in `cam/<sensor>/` against `cam/cam_driver.h`: probe,
   init, set resolution, controls, and capabilities (JPEG or not, maximum
   size). Register tables under another license go to
   `third_party/<sensor>/` with their license file.
4. Add the module name to `CAMERA_MODULE` and the module → sensor mapping in
   `examples/camera_stream/CMakeLists.txt`.
5. Check the frame size in KB at each resolution, not only the console.

> **SCCB is not quite I2C.** A register read is two transactions — write the
> address, STOP, then read — with no repeated start. `cam_sccb.c` does it this
> way. A repeated start makes many sensors stop answering, which looks like a
> wiring fault.

## Tests

| Test | Where it runs | What it checks |
|---|---|---|
| `test/run_host_tests.sh` | PC (gcc) | Request parser, connection table, controls, settings store, accounts and sessions |
| `test/net_regression.py` | PC → camera | 88 checks over HTTPS: routes, limits, malformed requests, login, roles, CSRF, lockout |

`net_regression.py` needs an admin and a viewer account:

```bash
export CAM_ADMIN_USER=… CAM_ADMIN_PASS=… CAM_VIEWER_USER=… CAM_VIEWER_PASS=…
python examples/camera_stream/test/net_regression.py --host 192.168.11.7
```

Close the camera page before running it. The test takes the stream, and a
page left open competes for it.
