#!/usr/bin/env python3
# Copyright (c) 2026 WIZnet Co., Ltd.
# SPDX-License-Identifier: Apache-2.0
"""Make the camera's HTTPS key and certificate.

CMake runs this at configure time when the build has no certificate yet, or
when -DCAM_IP changed. It can also be run by hand:

    python tools/make_https_cert.py --ip 192.168.11.7 --out build/https_cert.c

Two things are produced, kept apart on purpose:

  ~/.camera-stream-ca/ca.key, ca.crt
      A certificate authority (CA) of your own. Created once and reused, so a
      browser that trusts it keeps trusting every camera you build. It stays
      OUTSIDE the repository: whoever has ca.key can make certificates your
      browser accepts.

  <out>  (C source, inside the build directory)
      This camera's private key and certificate, signed by that CA, valid for
      the camera's IP address. A new key for every build directory, so no two
      cameras share one. Never commit it.

Needs the 'cryptography' package:  pip install cryptography
"""

import argparse
import datetime
import hashlib
import ipaddress
import os
import sys

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
except ImportError:
    sys.exit("make_https_cert.py: the Python package 'cryptography' is missing.\n"
             "Install it with:  python -m pip install cryptography\n"
             "then run cmake again.")

CA_DIR = os.path.join(os.path.expanduser("~"), ".camera-stream-ca")
CA_KEY = os.path.join(CA_DIR, "ca.key")
CA_CRT = os.path.join(CA_DIR, "ca.crt")
MARKER = "camera-stream https cert for "     # first line of the C file names the IP


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def load_or_make_ca():
    if os.path.exists(CA_KEY) and os.path.exists(CA_CRT):
        key = serialization.load_pem_private_key(open(CA_KEY, "rb").read(), None)
        crt = x509.load_pem_x509_certificate(open(CA_CRT, "rb").read())
        return key, crt, False
    os.makedirs(CA_DIR, exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "WIZnet camera-stream demo CA")])
    crt = (x509.CertificateBuilder()
           .subject_name(name).issuer_name(name)
           .public_key(key.public_key())
           .serial_number(x509.random_serial_number())
           .not_valid_before(now() - datetime.timedelta(minutes=5))
           .not_valid_after(now() + datetime.timedelta(days=3650))
           .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
           .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False),
                          critical=True)
           .sign(key, hashes.SHA256()))
    with open(CA_KEY, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.TraditionalOpenSSL,
                                  serialization.NoEncryption()))
    try:
        os.chmod(CA_KEY, 0o600)
    except OSError:
        pass
    with open(CA_CRT, "wb") as f:
        f.write(crt.public_bytes(serialization.Encoding.PEM))
    return key, crt, True


def make_device(ca_key, ca_crt, ip):
    key = ec.generate_private_key(ec.SECP256R1())
    crt = (x509.CertificateBuilder()
           .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, ip)]))
           .issuer_name(ca_crt.subject)
           .public_key(key.public_key())
           .serial_number(x509.random_serial_number())
           .not_valid_before(now() - datetime.timedelta(minutes=5))
           # Browsers refuse server certificates valid for more than ~398 days.
           .not_valid_after(now() + datetime.timedelta(days=397))
           .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=False)
           .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False),
                          critical=True)
           .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
           .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(ip))]),
                          critical=False)
           .sign(ca_key, hashes.SHA256()))
    return key, crt


def c_array(name, data):
    rows = [", ".join(f"0x{b:02x}" for b in data[i:i + 12]) for i in range(0, len(data), 12)]
    return (f"const unsigned char {name}[] = {{\n    " + ",\n    ".join(rows) +
            f"\n}};\nconst unsigned int {name}_len = {len(data)};\n")


def fingerprint(crt):
    d = hashlib.sha256(crt.public_bytes(serialization.Encoding.DER)).hexdigest().upper()
    return ":".join(d[i:i + 2] for i in range(0, len(d), 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ip", required=True, help="the camera's IPv4 address")
    ap.add_argument("--out", required=True, help="C file to write")
    a = ap.parse_args()
    ip = str(ipaddress.IPv4Address(a.ip))

    ca_key, ca_crt, created = load_or_make_ca()
    dev_key, dev_crt = make_device(ca_key, ca_crt, ip)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        f.write(f"/* {MARKER}{ip}\n"
                " * GENERATED by tools/make_https_cert.py - holds a private key, never commit.\n"
                f" * Signed by the CA in {CA_DIR}. */\n\n")
        f.write(c_array("https_dev_cert_der", dev_crt.public_bytes(serialization.Encoding.DER)) + "\n")
        f.write(c_array("https_ca_cert_der", ca_crt.public_bytes(serialization.Encoding.DER)) + "\n")
        f.write(c_array("https_dev_key_der", dev_key.private_bytes(
            serialization.Encoding.DER, serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption())))

    ca_path = CA_CRT
    print(f"[cert] {'created' if created else 'reusing'} CA      {ca_path}")
    print(f"[cert] camera certificate for https://{ip}/ -> {a.out}")
    print(f"[cert] camera SHA-256 fingerprint {fingerprint(dev_crt)}")
    print("[cert] To open the camera page without a browser warning, trust the CA once on")
    print("[cert] the viewing PC (only needed the first time):")
    print(f'[cert]   Windows : certutil -addstore -user Root "{ca_path}"')
    print(f'[cert]   macOS   : security add-trusted-cert -r trustRoot -k ~/Library/Keychains/login.keychain-db "{ca_path}"')
    print(f'[cert]   Linux   : certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n camera-stream-ca -i "{ca_path}"')
    print("[cert]   Firefox : Settings > Privacy & Security > Certificates > Import")


if __name__ == "__main__":
    main()
