# Build and security

[README](../README.md) · [한국어](build-and-security_kor.md)

## What to install

| Tool | Tested version | Note |
|---|---|---|
| Git | any | `--recursive` fetches the pinned submodules |
| CMake | 3.13 or later | |
| Arm GNU toolchain | 10.3-2021.10 (`arm-none-eabi-gcc`) | on `PATH` |
| A make tool | MinGW Makefiles (Windows) | Ninja or Unix Makefiles on Linux/macOS — not tested |
| Python 3 | 3.12 | with `cryptography`: `python -m pip install cryptography` |

The Raspberry Pi Pico SDK (2.2.0), Mbed TLS (3.6.0) and the WIZnet ioLibrary
come with the repository as git submodules in `libraries/`. No separate
`PICO_SDK_PATH` is needed.

> **Clone with `--recursive`.** Without it `libraries/` is empty and `cmake`
> stops at the SDK import. In a clone made without it, run
> `git submodule update --init --recursive`.

## Build options

| Option | Default | What it does |
|---|---|---|
| `CAMERA_MODULE` | `arducam_b0554` | Camera pin map and driver: `arducam_b0554`, `ov2640_dvp`. `ov3660_dvp_module` and `ov5640_dvp_module` build `camera_probe` only |
| `CAM_IP` | `192.168.11.7` | The camera's address. The certificate is made for this address |
| `CMAKE_BUILD_TYPE` | — | `Release` recommended. Debug measured the same fps (see test results) |
| `CAM_SETUP_SERIAL` | `ON` | `setup` and `factory-reset` on the USB console |
| `EXHIBITION_SIMPLE_UI` | `OFF` | `ON` paints only the name, picture and graphs — a kiosk screen without the account and control panels |

Keep **one build directory per camera** (`build_b0554`, `build_ov2640`, …).
Every build directory has its own key and certificate, and an image built
for one module does not drive another.

### Targets

| Target | What it is |
|---|---|
| `camera_stream_https` | The camera firmware: HTTPS on port 443, with login |
| `camera_probe` | No network. Powers the camera, scans the SCCB bus and prints what answered on the USB console every 3 s |
| `camera_plain_dev` | Only with `-DCAM_PLAIN_HTTP_DEV=ON`. Plain HTTP on port 80 **without login** — anyone on the network can watch and change settings. For development |

## Another address

```bash
cmake -S . -B build_b0554 -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release \
      -DCAMERA_MODULE=arducam_b0554 -DCAM_IP=192.168.1.50
cmake --build build_b0554 --target camera_stream_https
```

**What happens:** the address is compiled into the firmware, and the
certificate is made again for the new address.

**Why both at once:** a browser checks that the address in the URL is the
address written in the certificate. A firmware at one address with a
certificate for another gets a security warning.

**So:** change the address only through `CAM_IP`. The subnet mask
(`255.255.255.0`) and gateway (`x.x.x.1`) are in `stream_config.h`
(`NET_SUBNET_MASK`, `NET_GATEWAY`); change them there if your network differs.

### Two cameras on one network

Each camera needs its own `CAM_IP` **and** its own MAC address. The MAC is
`NET_MAC_ADDR` in `examples/camera_stream/stream_config.h`
(`00:08:DC:12:34:60`). Two boards with the same MAC confuse the switch and
the PC, and both cameras drop connections at random.

## The certificate

`cmake` runs `examples/camera_stream/tools/make_https_cert.py`, which makes:

| File | Where | What |
|---|---|---|
| `ca.key`, `ca.crt` | `~/.camera-stream-ca/` | Your certificate authority. Made once, reused by every build |
| `https_cert.c` | the build directory | This camera's private key and certificate (P-256), signed by your CA, for `CAM_IP`, valid 397 days |

The certificate is made when the build directory has none, or when
`CAM_IP` changed. Otherwise the same one is kept, so rebuilding does not make
the browser warn again.

**To make a new one** (it expired, or the key may have leaked): delete
`examples/camera_stream/https_cert.c` in the build directory, run `cmake`
again, rebuild and flash.

**To trust the CA** on a viewing PC:

| OS | Command |
|---|---|
| Windows | `certutil -addstore -user Root "%USERPROFILE%\.camera-stream-ca\ca.crt"` |
| macOS | `security add-trusted-cert -r trustRoot -k ~/Library/Keychains/login.keychain-db ~/.camera-stream-ca/ca.crt` |
| Linux (Chrome) | `certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n camera-stream-ca -i ~/.camera-stream-ca/ca.crt` |
| Firefox | Settings → Privacy & Security → Certificates → View Certificates → Authorities → Import |

To check the connection from a script without trusting the CA system-wide:

```bash
curl --cacert ~/.camera-stream-ca/ca.crt https://192.168.11.7/api/auth
```

On Windows curl add `--ssl-no-revoke`: your CA publishes no revocation
list, and Windows curl fails when it cannot check one.

> **Never commit `ca.key` or `https_cert.c`.** `.gitignore` already keeps
> the generated files out of the repository. Anyone with `ca.key` can make
> certificates every PC that trusts your CA accepts.

## What the security covers

| Area | What the firmware does |
|---|---|
| Transport | TLS 1.2 only, ECDHE-ECDSA on P-256. ChaCha20-Poly1305 first, AES-128-GCM for clients without it. Port 80 is not opened |
| Accounts | One admin and one viewer. No default password: the first admin is created in setup mode |
| Passwords | Stored as PBKDF2-HMAC-SHA256 with a random 16-byte salt, 5,000 iterations; never stored as text. 10–64 characters |
| Wrong passwords | After 5 failures, logins are refused (`429`) for 30 s |
| Sessions | Cookie `cam_sid` (Secure, HttpOnly, SameSite=Strict). Ends after 30 min idle or 12 h. Up to 4 sessions |
| Changes | Every state-changing request is a POST with an `X-CSRF-Token` header, so another web page cannot change the camera through your browser |
| Roles | The viewer can watch and read status. Only the admin changes the resolution, sensor controls, accounts and saved settings |

**Why only 5,000 PBKDF2 iterations:** each iteration costs 72 µs on the
RP2350 at 200 MHz, so 5,000 is 360 ms per login, measured. Server guidance
asks for far more, which a microcontroller cannot pay on every login. The
hash stays in the board's flash, and online guessing is limited by the
5-failure lock — so the minimum length of 10 characters carries the rest.
Choose a long password.

### Setup mode and the USB console

`CAM_SETUP_SERIAL=ON` lets anyone at the USB port open setup mode (when no
admin exists) or erase the accounts with `factory-reset`. That is physical
access, which the board cannot defend against anyway. A product with a setup
button can build with `-DCAM_SETUP_SERIAL=OFF`; the page then says setup mode
cannot be opened from this firmware.

### What is not covered

- No firmware signing or secure boot: anyone with the board in hand can
  flash other firmware.
- The settings in flash (including the password hashes) are not encrypted.
- The firmware does not check the clock, so the certificate's dates are only
  checked by the browser.
