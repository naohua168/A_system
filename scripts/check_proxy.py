#!/usr/bin/env python3
import os
for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy"]:
    print(f"{k}={os.environ.get(k, 'NOT SET')}")
