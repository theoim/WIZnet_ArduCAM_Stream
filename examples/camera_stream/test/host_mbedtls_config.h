/*
 * Copyright (c) 2026 WIZnet Co., Ltd.
 * SPDX-License-Identifier: Apache-2.0
 */

/* mbedTLS for the host tests: only what auth.c uses (PBKDF2-HMAC-SHA256). */
#ifndef HOST_MBEDTLS_CONFIG_H
#define HOST_MBEDTLS_CONFIG_H

#define MBEDTLS_MD_C
#define MBEDTLS_SHA256_C
#define MBEDTLS_PKCS5_C
#define MBEDTLS_PLATFORM_C       /* required by check_config on Windows */

#endif
