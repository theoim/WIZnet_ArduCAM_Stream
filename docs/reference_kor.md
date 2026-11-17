# 레퍼런스

[README](../README_kor.md) · [English](reference.md)

## USB 콘솔

보드의 COM 포트를 아무 속도로나 엽니다(USB라서 속도 설정은 무시됩니다). 보드가
입력한 글자를 되돌려 보여 주지 않으므로 로컬 에코를 켜고 CR+LF로 전송하세요.

| 명령 | 하는 일 |
|---|---|
| `setup` | 관리자 계정이 없을 때만, 설정 모드를 5분 동안 엽니다 |
| `factory-reset` | 확인을 묻습니다. 10초 안에 `yes`를 입력하면 계정과 저장된 카메라 설정을 지우고 재시작합니다. 다른 입력은 취소입니다 |

콘솔에는 카메라 동작도 출력됩니다: TLS 핸드셰이크, 로그인, 해상도 변경, 오류.
부팅 배너는 펌웨어와 카메라 모듈 이름을 알려 줍니다.

```
=== WIZnet ArduCAM Stream 1.0.0 (toe <빌드 날짜>)  module: Arducam Quick-Bootup 3MP DVP (B0554) ===
```

배너는 대부분 터미널이 포트를 열기 전에 출력되므로, 보통은 그 뒤의 줄만 보입니다.

## 웹 페이지

| 패널 | 사용할 수 있는 사람 | 내용 |
|---|---|---|
| Picture | 관리자, 시청자 | 실시간 영상 |
| Control | 관리자 | 시작/정지, 해상도, **Link load** — 부하 상태에서 스트림이 버티는지 보기 위한 시험용 추가 트래픽 |
| Live performance | 관리자, 시청자 | 프레임률과 데이터 속도 그래프 |
| Access & accounts | 관리자 | 관리자 비밀번호 변경, 시청자 계정 설정·끄기 |
| Sensor controls | 관리자 | 카메라 드라이버가 제공하는 설정(밝기, 대비 …), **Save** |

페이지에서 바꾼 설정은 보드가 재시작할 때까지만 유지됩니다. **Save**를 누르면
해상도와 센서 설정이 플래시에 저장되고, 다음 부팅 때 적용됩니다. 단, 저장할 때와
같은 카메라 모델에서만 적용됩니다.

## HTTP API

모든 요청은 HTTPS입니다. 로그인 관련 경로를 빼면 `/api/login`이 준 세션 쿠키가
필요합니다. 상태를 바꾸는 POST에는 `X-CSRF-Token` 헤더도 필요하며, 그 값은
로그인한 상태에서 `GET /api/auth`가 알려 줍니다. 폼 본문은
`application/x-www-form-urlencoded`입니다.

| 메서드 | 경로 | 권한 | 하는 일 |
|---|---|---|---|
| GET | `/` | 누구나 | 페이지(gzip) |
| GET | `/api/auth` | 누구나 | 로그인 상태: `provisioned`, `setup_open`, `role`, `user`, `csrf` |
| POST | `/api/setup` | 누구나, 설정 모드에서만 | 관리자 생성: `user`, `pass` |
| POST | `/api/login` | 누구나 | `user`, `pass`. `cam_sid` 쿠키를 설정합니다 |
| POST | `/api/logout` | 시청자 | 세션 종료 |
| GET | `/stream` | 시청자 | MJPEG 스트림(`multipart/x-mixed-replace`) |
| GET | `/snapshot.jpg` | 시청자 | JPEG 한 장 |
| GET | `/api/status` | 시청자 | 프레임률, 프레임 크기, 드롭·TLS 카운터(JSON) |
| GET | `/api/controls` | 시청자 | 센서 설정 목록과 범위(JSON) |
| POST | `/api/res?v=1280x720` | 관리자 | 해상도 변경 |
| POST | `/api/cam` | 관리자 | 설정 변경. 예: `brightness=1&mirror=0` |
| POST | `/api/settings/save` | 관리자 | 해상도와 설정을 플래시에 저장 |
| POST | `/api/start`, `/api/stop` | 관리자 | 촬영 시작·정지 |
| POST | `/api/reset` | 관리자 | 센서 리셋 후 다시 초기화 |
| POST | `/api/account` | 관리자 | `role=admin&old=…&pass=…` 또는 `role=viewer&user=…&pass=…` 또는 `role=viewer&enabled=0` |

권한 칸의 "시청자"는 시청자 또는 관리자를 뜻합니다.

Python `requests` 예시:

```python
import requests
s = requests.Session()
s.verify = "~/.camera-stream-ca/ca.crt"          # ~는 홈 경로로 바꾸세요
s.post("https://192.168.11.7/api/login", data={"user": "admin", "pass": "…"})
csrf = s.get("https://192.168.11.7/api/auth").json()["csrf"]
s.post("https://192.168.11.7/api/res?v=640x480", headers={"X-CSRF-Token": csrf})
open("shot.jpg", "wb").write(s.get("https://192.168.11.7/snapshot.jpg").content)
```

### 상태 코드

| 코드 | 뜻 |
|---|---|
| 401 | 로그인하지 않았거나 세션이 끝났음. 또는 로그인 때 사용자 이름·비밀번호가 틀림 |
| 403 | 권한이 부족하거나, `X-CSRF-Token`이 없거나 틀림. 또는 설정 모드가 닫힌 상태에서 `/api/setup` |
| 409 | 다른 로그인이 스트림을 쓰는 중(`Retry-After: 10`). 또는 관리자가 이미 있는데 `/api/setup` |
| 415 | 폼 POST가 `application/x-www-form-urlencoded`가 아님 |
| 429 | 비밀번호를 너무 많이 틀림: 30초 기다리세요 |
| 400 | 요청이나 값의 형식이 잘못됐거나, 설정 값이 범위를 벗어남 |

## 해상도

| 카메라 | 해상도 | 기본값 |
|---|---|---|
| B0554 | 320x240, 640x480, 1280x720, 1600x1200, 1920x1080 | 1280x720 |
| OV2640 | 160x120, 176x144, 320x240, 352x288, 640x480, 800x600, 1024x768, 1280x1024, 1600x1200 | 800x600 |

OV2640은 800x600이 센서 고유의 미리보기 모드라 프레임률이 가장 좋습니다.
640x480과 1024x768 이상은 센서 전체 영역을 읽어서 느립니다. 640x480은 5.9 fps로
측정됐습니다.

카메라가 실제로 보내는 해상도는 `/api/status`의 `res`에 나옵니다. 프레임 크기(KB)도
함께 확인하세요. 센서가 해상도 변경을 받아들이지 않으면 오류가 아니라 예상과 다른
프레임 크기로 드러납니다.

## 핀맵

모든 모듈은 같은 DVP 배선(README 1단계)을 씁니다. 클럭과 전원 차단 핀만 다릅니다.

| 모듈 파일(`cam/modules/`) | XCLK | PWDN | SCCB | 상태 |
|---|---|---|---|---|
| `arducam_b0554.h` | 모듈 자체 오실레이터 | GP27 | 0x1F, 200 kHz | 시험 완료 |
| `ov2640_dvp.h` | GP26, 20 MHz PWM | GP27 | 0x30, 200 kHz | 시험 완료 |
| `ov3660_dvp_module.h` | GP26, 20 MHz PWM | 연결 안 함 | 0x3C, 100 kHz | 추가 예정, 미검증 |
| `ov5640_dvp_module.h` | 모듈 자체 오실레이터 | GP27 | 0x3C, 100 kHz | 칩 판별만 |

B0554는 이미지 센서가 버스에 직접 보이지 않습니다. 모듈 위의 제어 칩(SCCB 주소
`0x1F`)만 응답하고, 호스트는 그 제어 칩의 레지스터 하나를 써서 해상도를 바꿉니다.
그래서 센서 드라이버가 아니라 별도 드라이버(`cam/arducam_qb/`)를 둡니다.

## camera_probe

`camera_probe`는 네트워크 없이 카메라만 확인합니다.

```bash
cmake --build build_b0554 --target camera_probe
```

`camera_probe.uf2`를 올리면 3초마다 응답한 SCCB 주소와 알려진 카메라의 칩 ID를
출력합니다.

| 출력 | 뜻 |
|---|---|
| 알려진 주소와 칩 이름 | 카메라 배선과 전원이 정상 |
| `0x1F`와 `SENSOR_ID 0x039E` | Arducam B0554 |
| `nothing answered` | 3V3·GND → PWDN(Low여야 함) → 오실레이터 없는 모듈은 XCLK → SDA/SCL 순서로 확인 |

## 카메라 추가하기

코드는 세 층으로 나뉘어 있어, 새 카메라를 추가해도 네트워크와 캡처 코드는
건드리지 않습니다.

| 층 | 카메라마다 다른 것 | 위치 |
|---|---|---|
| 센서 드라이버 | 칩 ID, 레지스터 표, 해상도·포맷 | `cam/<sensor>/` |
| 모듈 핀맵 | XCLK, PWDN, RESET, SCCB 속도 | `cam/modules/<module>.h` |
| 공통 | SCCB 접근, 칩 판별, DVP 캡처, HTTPS 서버 | `cam/cam_sccb.*`, `cam/cam_probe.*`, `capture/` |

1. `camera_probe`로 실물의 SCCB 주소와 칩 ID를 먼저 읽습니다. 데이터시트 값은 그다음입니다.
2. `cam/modules/`의 핀맵을 복사합니다. 모듈에 오실레이터가 있으면
   `CAM_PIN_XCLK (-1)`로 두되, 오실레이터 주파수는 `CAM_XCLK_HZ`에 꼭 적습니다.
   센서 클럭 설정이 이 값을 기준으로 계산됩니다.
3. `cam/cam_driver.h`에 맞춰 `cam/<sensor>/`에 드라이버를 작성합니다: 칩 판별,
   초기화, 해상도 설정, 센서 설정, 능력(JPEG 여부, 최대 해상도). 다른 라이선스의
   레지스터 표는 라이선스 파일과 함께 `third_party/<sensor>/`에 둡니다.
4. `examples/camera_stream/CMakeLists.txt`의 `CAMERA_MODULE` 목록과 모듈 → 센서
   대응에 추가합니다.
5. 해상도마다 콘솔 출력이 아니라 프레임 크기(KB)로 확인합니다.

> **SCCB는 I2C와 조금 다릅니다.** 레지스터 읽기는 두 트랜잭션입니다. 주소를 쓰고
> STOP, 그다음 읽기입니다. repeated start를 쓰지 않습니다. `cam_sccb.c`가 이렇게
> 동작합니다. repeated start를 쓰면 많은 센서가 응답하지 않는데, 배선 문제처럼
> 보입니다.

## 시험

| 시험 | 실행 위치 | 확인하는 것 |
|---|---|---|
| `test/run_host_tests.sh` | PC(gcc) | 요청 파서, 연결 표, 센서 설정, 설정 저장, 계정과 세션 |
| `test/net_regression.py` | PC → 카메라 | HTTPS로 88개 항목: 경로, 한도, 잘못된 요청, 로그인, 권한, CSRF, 잠금 |

`net_regression.py`에는 관리자와 시청자 계정이 필요합니다.

```bash
export CAM_ADMIN_USER=… CAM_ADMIN_PASS=… CAM_VIEWER_USER=… CAM_VIEWER_PASS=…
python examples/camera_stream/test/net_regression.py --host 192.168.11.7
```

실행 전에 카메라 페이지를 닫으세요. 시험이 스트림을 가져가는데, 열린 페이지가
스트림을 두고 경쟁합니다.
