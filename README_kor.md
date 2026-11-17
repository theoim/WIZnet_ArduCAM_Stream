# WIZnet ArduCAM Stream

펌웨어 1.0.0 · [English](README.md)

W6300-EVB-Pico2와 DVP 카메라 모듈로 브라우저에서 보는 네트워크 카메라를
만듭니다. 영상은 **HTTPS**(암호화된 웹 연결)로 전송되고 로그인이 필요합니다.
W6300 칩이 TCP/IP를 하드웨어로 처리하므로, RP2350은 카메라와 암호화에 시간을
씁니다.

```
 DVP 카메라 ──8비트 병렬──►  W6300-EVB-Pico2  ──이더넷──►  브라우저
 (B0554, OV2640)            (HTTPS 서버)        https://192.168.11.7/
```

## 지원 카메라

| 카메라 | 빌드 옵션 `CAMERA_MODULE` | 기본 해상도 | 실측 | 시험 상태 |
|---|---|---|---|---|
| **Arducam Quick-Bootup 3MP DVP (B0554)** — 기준 카메라 | `arducam_b0554` | 1280x720 | **30 fps** | ✅ |
| OV2640 DVP 모듈 | `ov2640_dvp` | 800x600 | 17 fps | ✅ |
| OV3660 DVP 모듈 | `ov3660_dvp_module` | — | — | ⬜ 추가 예정: 핀맵만 있음 |

✅ 실기 시험 완료 · ⬜ 아직 시험하지 않음. fps는 HTTPS로 시청자 1명이 볼 때
측정한 값입니다. 자세한 내용은 [시험 결과](docs/test-results_kor.md)를 참고하세요.

### 미리 빌드한 펌웨어를 제공하지 않는 이유

HTTPS를 쓰려면 카메라 안에 **개인 키**가 있어야 합니다. 이 키를 가진 사람은
카메라인 것처럼 행세할 수 있습니다.

미리 빌드한 `.uf2` 파일을 배포하면 모든 카메라가 같은 키를 갖게 되고, 파일을
내려받은 사람 누구나 그 키를 갖게 됩니다.

그래서 펌웨어는 직접 빌드합니다. 빌드할 때 카메라마다 새 키와 인증서가
자동으로 만들어지므로, 키를 따로 만드는 단계는 없습니다.

## 빠른 시작

| 단계 | 내용 |
|---|---|
| 1 | 카메라 배선 |
| 2 | 펌웨어 빌드 |
| 3 | 펌웨어 올리기와 PC 주소 설정 |
| 4 | 인증서 신뢰 등록(최초 1회) |
| 5 | 관리자 계정 만들고 영상 보기 |

### 준비물

- W6300-EVB-Pico2, USB 케이블, 이더넷 케이블
- 위 표의 카메라 모듈과 점퍼선
- Git, CMake, Arm GNU 툴체인, Python 3가 설치된 PC —
  [빌드와 보안](docs/build-and-security_kor.md#설치할-것) 참고
- 시리얼 터미널(예: [Tera Term](https://teratermproject.github.io))

## 1단계: 카메라 배선

| 카메라 핀 | W6300-EVB-Pico2 | 비고 |
|---|---|---|
| 3V3 / VCC | 3V3(OUT) | 모듈의 전원 전압을 확인하세요 |
| GND | GND | |
| SDA (SIOD) | GP0 | SCCB 데이터 |
| SCL (SIOC) | GP1 | SCCB 클럭 |
| VSYNC | GP4 | |
| D0 … D7 | GP5 … GP12 | D0은 GP5, D7은 GP12 |
| PCLK | GP13 | |
| HREF | GP14 | |
| PWDN | GP27 | |
| XCLK | GP26 | **OV2640만 연결.** B0554는 자체 클럭이 있습니다 |

> **D0–D7, PCLK, HREF는 반드시 GP5–GP14에 이 순서대로 연결합니다.** 영상
> 수신부는 이 10개 핀을 한 묶음으로 읽기 때문에, 선 하나만 바뀌어도 영상의 모든
> 바이트가 어긋납니다. GP15–GP22는 보드의 W6300이 사용합니다.

**SCCB**는 카메라 설정용 버스로, I2C와 거의 같습니다. **DVP**는 영상이 들어오는
8비트 병렬 버스입니다. PCLK 펄스마다 D0–D7으로 1바이트가 들어오고, VSYNC(프레임)와
HREF(줄)가 그 범위를 알려 줍니다.

## 2단계: 펌웨어 빌드

```bash
git clone --recursive https://github.com/theoim/WIZnet_ArduCAM_Stream.git
cd WIZnet_ArduCAM_Stream
python -m pip install cryptography

cmake -S . -B build_b0554 -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release -DCAMERA_MODULE=arducam_b0554
cmake --build build_b0554 --target camera_stream_https
```

OV2640은 `-DCAMERA_MODULE=ov2640_dvp`로, `build_ov2640` 같은 다른 빌드
디렉터리에서 빌드합니다. `"MinGW Makefiles"`는 Windows용입니다. Linux나 macOS에서는
`-G`를 빼세요([빌드와 보안](docs/build-and-security_kor.md) 참고).

첫 번째 `cmake` 명령이 카메라 인증서도 함께 만들고 다음을 출력합니다.

```
[cert] created CA      C:\Users\you\.camera-stream-ca\ca.crt
[cert] camera certificate for https://192.168.11.7/ -> .../https_cert.c
[cert] To open the camera page without a browser warning, trust the CA once on
[cert] the viewing PC (only needed the first time):
[cert]   Windows : certutil -addstore -user Root "C:\Users\you\.camera-stream-ca\ca.crt"
```

이 출력은 4단계에서 신뢰 등록 명령으로 사용합니다.

펌웨어 파일은 `build_b0554/examples/camera_stream/camera_stream_https.uf2`입니다.

## 3단계: 펌웨어 올리기와 PC 주소 설정

1. 보드의 **BOOTSEL** 버튼을 누른 채 USB 케이블을 연결합니다. PC에 드라이브가 나타납니다.
2. `camera_stream_https.uf2`를 드라이브로 끌어 놓습니다. 보드가 스스로 재시작합니다.
3. 이더넷 케이블로 보드와 PC를 연결합니다.

| 항목 | 값 |
|---|---|
| 카메라 주소 | `https://192.168.11.7/` |
| 서브넷 마스크 | `255.255.255.0` |
| 게이트웨이 | `192.168.11.1` |

카메라는 **고정 주소**를 씁니다. DHCP(주소 자동 할당)는 사용하지 않습니다.
그래서 PC의 이더넷 어댑터를 같은 네트워크의 고정 주소로 설정해야 합니다.
예: `192.168.11.100` / `255.255.255.0`.

> **먼저 ping으로 확인하세요.** 브라우저를 열기 전에 `ping 192.168.11.7`이
> 응답해야 합니다.

다른 주소를 쓰려면 `-DCAM_IP=192.168.1.50`으로 빌드합니다. 인증서도 그 주소로
함께 만들어집니다.

## 4단계: 인증서 신뢰 등록(최초 1회)

카메라 페이지를 열 PC에서, 빌드가 출력한 신뢰 등록 명령을 실행합니다. Windows는
다음과 같습니다.

```
certutil -addstore -user Root "%USERPROFILE%\.camera-stream-ca\ca.crt"
```

**무엇인가:** 빌드는 두 가지를 만들었습니다. 하나는 `~/.camera-stream-ca`에 있는
나만의 작은 인증 기관(CA)이고, 다른 하나는 그 CA가 서명한 카메라 인증서입니다.

**왜 필요한가:** 브라우저는 자기가 아는 CA가 서명한 인증서만 신뢰합니다. 나만의
CA는 등록하기 전까지 브라우저가 모르므로, 이 단계를 건너뛰면 보안 경고가 뜹니다.

**그래서:** PC마다 CA를 한 번만 등록합니다. 나중에 빌드하는 카메라도 같은 CA로
서명되므로 계속 신뢰됩니다. `ca.key`는 남에게 주지 마세요. 이 파일이 있으면
내 PC가 받아들이는 인증서를 누구나 만들 수 있습니다.

등록한 뒤 브라우저를 다시 시작합니다. Firefox는 목록을 따로 씁니다: 설정 →
개인 정보 및 보안 → 인증서 → 인증서 보기 → 인증 기관 → 가져오기.

## 5단계: 관리자 계정 만들고 영상 보기

카메라에는 **기본 비밀번호가 없습니다.** 첫 계정은 **설정 모드**에서 만들며,
설정 모드는 보드의 USB 포트에 접근할 수 있는 사람만 열 수 있습니다.

1. `https://192.168.11.7/`을 엽니다. 페이지에 **Set up this camera**가 보입니다.
2. 터미널에서 보드의 COM 포트를 열고 `setup`을 입력합니다. 보드가 다음과 같이
   답합니다.

   ```
   [auth] setup mode OPEN for 5 minutes - create the admin in the browser
   ```

3. 페이지를 새로 고칩니다. 사용자 이름과 10자 이상의 비밀번호를 정하고
   **Create admin**을 누릅니다.
4. 영상이 나옵니다. **Access & accounts** 패널에서 **viewer**(시청자) 계정을
   추가할 수 있습니다. 시청자는 영상만 보고 설정은 바꿀 수 없습니다.

> **로컬 에코를 켜고 CR+LF로 전송하세요.** 보드는 입력한 글자를 되돌려 보여
> 주지 않습니다. Tera Term: 설정 → 단말 → 송신 `CR+LF`, 로컬 에코 체크.

## 문제 해결

### 브라우저에 보안 경고가 뜹니다

이 PC에 CA가 등록되지 않았거나, 등록 후 브라우저를 다시 시작하지 않았습니다.
4단계를 다시 하세요. 다른 `CAM_IP`로 **새** 빌드 디렉터리에서 빌드했다면 그
주소로 페이지를 열어야 합니다.

### 페이지에 "No admin account yet"이 보입니다

설정 모드가 닫혀 있습니다. USB 콘솔에서 `setup`을 입력하고 5분 안에 페이지를
새로 고치세요.

### 영상이 멈추거나 계속 다시 연결됩니다

카메라는 **한 번에 하나의 영상 스트림**만 보냅니다. 같은 브라우저의 두 탭은
로그인을 공유하므로 서로 스트림을 빼앗습니다. 다른 탭을 닫고, 연결이 끊길 때까지
30초쯤 기다린 뒤 새로 고치세요.

다른 로그인이 이미 보고 있으면, 그 시청이 끝날 때까지 스트림을 받을 수
없습니다(`409 Conflict`). 단, 관리자는 시청자의 스트림을 넘겨받을 수 있습니다.

### 페이지가 안 열리고 `ping`도 실패합니다

PC가 `192.168.11.x` 네트워크에 있지 않거나 케이블이 연결되지 않았습니다. PC의
고정 주소를 확인하세요.

### 영상이 검거나 프레임이 오지 않습니다

1단계 배선, 특히 D0–D7과 PCLK를 확인하세요. OV2640은 GP26의 XCLK가 연결되어 있어야
합니다. 카메라만 따로 확인하려면 `camera_probe`를 빌드합니다 —
[레퍼런스](docs/reference_kor.md#camera_probe) 참고.

### `cmake`가 "HTTPS certificate not made"로 멈춥니다

Python `cryptography` 패키지가 없습니다. `python -m pip install cryptography`를
실행하고 `cmake`를 다시 실행하세요.

### 관리자 비밀번호를 잊었습니다

USB 콘솔에서 `factory-reset`을 입력하고 10초 안에 `yes`를 입력합니다. 계정과
저장된 카메라 설정이 지워지고 보드가 새 보드처럼 재시작합니다. 그다음 5단계를
다시 하세요.

## 알려진 한계

| 무엇 | 왜 | 어떻게 |
|---|---|---|
| 영상 스트림은 한 번에 하나 | 설계상 선택입니다. 카메라의 프레임률 전부를 시청자 한 명에게 주고, 누가 볼 수 있는지 규칙을 단순하게 유지합니다. | 한 페이지에서 보세요. 관리자는 시청자의 스트림을 넘겨받을 수 있습니다. |
| IP·MAC 주소 고정, DHCP 없음 | 둘 다 빌드 때 정해지므로, DHCP 서버 없이도 카메라가 항상 같은 주소에 있습니다. | `-DCAM_IP`를 쓰세요. 한 네트워크에 카메라 두 대를 두려면 `stream_config.h`의 `NET_MAC_ADDR`도 바꾸세요. |
| 설정 모드와 공장 초기화에 USB 콘솔 필요 | 보드에 전용 버튼이 없고, USB 포트 접근은 곧 물리적 접근입니다. | 낯선 사람이 USB를 꽂을 수 없는 곳에 보드를 두세요. |
| 펌웨어 파일 안에 개인 키가 있음 | HTTPS를 제공하려면 카메라가 키를 갖고 있어야 합니다. | `.uf2` 파일과 빌드 디렉터리를 공유하지 마세요. 카메라마다 빌드하세요. |
| 인증서는 397일 뒤 만료 | 브라우저는 그보다 긴 서버 인증서를 거부합니다. | 빌드 디렉터리의 `https_cert.c`를 지우고 `cmake`를 다시 실행한 뒤 빌드해서 올리세요. |
| OV3660은 아직 미지원 | 동작하는 OV3660 하드웨어로 시험하지 못했습니다. | 핀맵은 `cam/modules/ov3660_dvp_module.h`에 있고, 드라이버는 추가 예정입니다. |

## 더 알아보기

| 문서 | 이럴 때 읽으세요 |
|---|---|
| [빌드와 보안](docs/build-and-security_kor.md) | 다른 주소, Linux/macOS 빌드, 보안이 무엇을 보호하는지 알고 싶을 때 |
| [레퍼런스](docs/reference_kor.md) | 콘솔 명령, HTTP API가 필요하거나 카메라를 추가하고 싶을 때 |
| [시험 결과](docs/test-results_kor.md) | 위 수치의 측정 근거를 보고 싶을 때 |

## 라이선스

이 프로젝트의 코드는 Apache-2.0입니다. 서드파티 구성요소는 각자의 라이선스를
따릅니다 — Mbed TLS(Apache-2.0), Raspberry Pi Pico SDK(BSD-3-Clause), WIZnet
ioLibrary(MIT), ArduCAM의 OV2640 레지스터 표(MIT). [NOTICE](NOTICE)를 참고하세요.
