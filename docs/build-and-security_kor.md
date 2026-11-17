# 빌드와 보안

[README](../README_kor.md) · [English](build-and-security.md)

## 설치할 것

| 도구 | 시험한 버전 | 비고 |
|---|---|---|
| Git | 무관 | `--recursive`로 고정된 서브모듈까지 받습니다 |
| CMake | 3.13 이상 | |
| Arm GNU 툴체인 | 10.3-2021.10 (`arm-none-eabi-gcc`) | `PATH`에 등록 |
| make 도구 | MinGW Makefiles (Windows) | Linux/macOS는 Ninja 또는 Unix Makefiles — 시험하지 않음 |
| Python 3 | 3.12 | `cryptography` 필요: `python -m pip install cryptography` |

Raspberry Pi Pico SDK(2.2.0), Mbed TLS(3.6.0), WIZnet ioLibrary는 `libraries/`에
git 서브모듈로 들어 있습니다. `PICO_SDK_PATH`를 따로 설정할 필요가 없습니다.

> **`--recursive`로 클론하세요.** 빠뜨리면 `libraries/`가 비어 있어 `cmake`가 SDK
> 가져오기 단계에서 멈춥니다. 이미 클론했다면 `git submodule update --init --recursive`를
> 실행하세요.

## 빌드 옵션

| 옵션 | 기본값 | 하는 일 |
|---|---|---|
| `CAMERA_MODULE` | `arducam_b0554` | 카메라 핀맵과 드라이버: `arducam_b0554`, `ov2640_dvp`. `ov3660_dvp_module`, `ov5640_dvp_module`은 `camera_probe`만 빌드됩니다 |
| `CAM_IP` | `192.168.11.7` | 카메라 주소. 인증서도 이 주소로 만들어집니다 |
| `CMAKE_BUILD_TYPE` | — | `Release` 권장. Debug도 fps는 같았습니다(시험 결과 참고) |
| `CAM_SETUP_SERIAL` | `ON` | USB 콘솔의 `setup`, `factory-reset` 명령 |
| `EXHIBITION_SIMPLE_UI` | `OFF` | `ON`이면 이름·영상·그래프만 보이는 키오스크 화면이 됩니다. 계정·제어 패널이 사라집니다 |

**카메라마다 빌드 디렉터리를 따로 두세요**(`build_b0554`, `build_ov2640` …). 빌드
디렉터리마다 키와 인증서가 따로 있고, 한 모듈용으로 빌드한 이미지는 다른 모듈을
구동하지 못합니다.

### 타깃

| 타깃 | 내용 |
|---|---|
| `camera_stream_https` | 카메라 펌웨어: 443 포트 HTTPS, 로그인 |
| `camera_plain_dev` | `-DCAM_PLAIN_HTTP_DEV=ON`일 때만 빌드. 80 포트 평문 HTTP, **로그인 없음** — 네트워크의 누구나 보고 설정을 바꿀 수 있습니다. 개발용입니다 |
| `camera_probe` | 네트워크 없음. 카메라 전원을 켜고 SCCB 버스를 스캔해, 응답한 장치를 3초마다 USB 콘솔에 출력합니다 |

## 다른 주소 쓰기

```bash
cmake -S . -B build_b0554 -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release \
      -DCAMERA_MODULE=arducam_b0554 -DCAM_IP=192.168.1.50
cmake --build build_b0554 --target camera_stream_https
```

**무엇이 일어나나:** 주소가 펌웨어에 들어가고, 인증서도 새 주소로 다시 만들어집니다.

**왜 둘을 같이 바꾸나:** 브라우저는 URL의 주소가 인증서에 적힌 주소와 같은지
확인합니다. 펌웨어 주소와 인증서 주소가 다르면 보안 경고가 뜹니다.

**그래서:** 주소는 `CAM_IP`로만 바꿉니다. 서브넷 마스크(`255.255.255.0`)와
게이트웨이(`x.x.x.1`)는 `stream_config.h`의 `NET_SUBNET_MASK`, `NET_GATEWAY`에
있으니, 네트워크가 다르면 그곳을 고치세요.

### 한 네트워크에 카메라 두 대

카메라마다 `CAM_IP`와 **MAC 주소**가 모두 달라야 합니다. MAC은
`examples/camera_stream/stream_config.h`의 `NET_MAC_ADDR`(`00:08:DC:12:34:60`)입니다.
같은 MAC을 가진 보드가 두 대면 스위치와 PC가 둘을 구분하지 못해, 두 카메라 모두
연결이 불규칙하게 끊깁니다.

## 인증서

`cmake`가 `examples/camera_stream/tools/make_https_cert.py`를 실행해 다음을 만듭니다.

| 파일 | 위치 | 내용 |
|---|---|---|
| `ca.key`, `ca.crt` | `~/.camera-stream-ca/` | 나만의 인증 기관(CA). 한 번 만들고 모든 빌드가 재사용합니다 |
| `https_cert.c` | 빌드 디렉터리 | 이 카메라의 개인 키와 인증서(P-256). CA가 서명, `CAM_IP`용, 유효기간 397일 |

인증서는 빌드 디렉터리에 아직 없거나 `CAM_IP`가 바뀌었을 때만 만들어집니다. 그
외에는 기존 것을 유지하므로, 다시 빌드해도 브라우저 경고가 다시 뜨지 않습니다.

**새로 만들려면**(만료됐거나 키 유출이 의심될 때): 빌드 디렉터리의
`examples/camera_stream/https_cert.c`를 지우고 `cmake`를 다시 실행한 뒤 빌드해서
올립니다.

**CA를 신뢰 등록하려면**(카메라를 볼 PC에서):

| OS | 명령 |
|---|---|
| Windows | `certutil -addstore -user Root "%USERPROFILE%\.camera-stream-ca\ca.crt"` |
| macOS | `security add-trusted-cert -r trustRoot -k ~/Library/Keychains/login.keychain-db ~/.camera-stream-ca/ca.crt` |
| Linux (Chrome) | `certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n camera-stream-ca -i ~/.camera-stream-ca/ca.crt` |
| Firefox | 설정 → 개인 정보 및 보안 → 인증서 → 인증서 보기 → 인증 기관 → 가져오기 |

CA를 시스템에 등록하지 않고 스크립트에서 연결을 확인하려면:

```bash
curl --cacert ~/.camera-stream-ca/ca.crt https://192.168.11.7/api/auth
```

Windows의 curl은 `--ssl-no-revoke`를 붙이세요. 나만의 CA는 인증서 폐기 목록을
제공하지 않는데, Windows curl은 폐기 여부를 확인하지 못하면 실패합니다.

> **`ca.key`와 `https_cert.c`는 절대 커밋하지 마세요.** 생성된 파일은 `.gitignore`가
> 이미 저장소에서 빼고 있습니다. `ca.key`가 있으면, 이 CA를 신뢰하는 모든 PC가
> 받아들이는 인증서를 누구나 만들 수 있습니다.

## 보안이 다루는 범위

| 영역 | 펌웨어가 하는 일 |
|---|---|
| 전송 | TLS 1.2만, P-256 ECDHE-ECDSA. ChaCha20-Poly1305 우선, 지원하지 않는 클라이언트는 AES-128-GCM. 80 포트는 열지 않습니다 |
| 계정 | 관리자 1개, 시청자 1개. 기본 비밀번호 없음: 첫 관리자는 설정 모드에서 만듭니다 |
| 비밀번호 | 16바이트 무작위 salt와 PBKDF2-HMAC-SHA256 5,000회로 저장. 원문은 저장하지 않습니다. 10–64자 |
| 틀린 비밀번호 | 5회 실패하면 30초 동안 로그인을 거부합니다(`429`) |
| 세션 | 쿠키 `cam_sid`(Secure, HttpOnly, SameSite=Strict). 30분 동안 사용이 없거나 12시간이 지나면 끝납니다. 최대 4개 |
| 변경 요청 | 상태를 바꾸는 요청은 모두 `X-CSRF-Token` 헤더가 있는 POST입니다. 그래서 다른 웹페이지가 내 브라우저를 통해 카메라 설정을 바꿀 수 없습니다 |
| 권한 | 시청자는 영상과 상태만 봅니다. 해상도·센서 설정·계정·설정 저장은 관리자만 합니다 |

**PBKDF2가 5,000회뿐인 이유:** 200 MHz RP2350에서 1회에 72 µs가 걸려, 5,000회면
로그인 한 번에 360 ms입니다(실측). 서버 권장치는 이보다 훨씬 많지만,
마이크로컨트롤러가 로그인마다 그 비용을 낼 수는 없습니다. 해시는 보드 플래시에만
있고 온라인 추측은 5회 실패 잠금이 막으므로, 나머지는 최소 10자의 비밀번호
길이가 맡습니다. 긴 비밀번호를 쓰세요.

### 설정 모드와 USB 콘솔

`CAM_SETUP_SERIAL=ON`이면 USB 포트에 접근한 사람은 누구나 설정 모드를 열 수
있고(관리자가 없을 때), `factory-reset`으로 계정을 지울 수 있습니다. 이는 물리적
접근이며, 보드는 원래 물리적 접근을 막을 수 없습니다. 설정 버튼이 있는 제품은
`-DCAM_SETUP_SERIAL=OFF`로 빌드할 수 있습니다. 이 경우 페이지는 이 펌웨어로는 설정
모드를 열 수 없다고 안내합니다.

### 다루지 않는 것

- 펌웨어 서명이나 보안 부팅이 없습니다. 보드를 손에 쥔 사람은 다른 펌웨어를 올릴 수 있습니다.
- 플래시에 저장된 설정(비밀번호 해시 포함)은 암호화되지 않습니다.
- 펌웨어는 시계를 확인하지 않으므로, 인증서의 유효기간은 브라우저만 확인합니다.
