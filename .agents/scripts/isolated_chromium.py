#!/usr/bin/env python3
"""Launch Chromium without browser-owned network access. Playwright uses its pipe."""

import os
import sys
import socket
from browser_isolation import restrict_network


def main():
    binary = os.environ.get('SEO_KIT_ISOLATED_CHROMIUM_BINARY')
    unshare = os.environ.get('SEO_KIT_UNSHARE_BINARY')
    backend = os.environ.get('SEO_KIT_ISOLATION_BACKEND')
    if not binary or backend not in ('seccomp', 'namespace'):
        raise SystemExit('isolated Chromium requires the live auditor launch contract')
    # Playwright owns the protocol pipes on fd 3/4. No inherited socket may
    # survive into a browser that cannot create network sockets of its own.
    for fd in os.listdir('/proc/self/fd'):
        if int(fd) > 4:
            try:
                os.close(int(fd))
            except OSError:
                pass
        else:
            try:
                if os.readlink('/proc/self/fd/' + fd).startswith('socket:'):
                    channel = socket.socket(fileno=int(fd))
                    try:
                        if channel.family != socket.AF_UNIX:
                            raise SystemExit('browser launch rejected an inherited network socket')
                    finally:
                        channel.detach()
            except FileNotFoundError:
                pass
    if backend == 'seccomp':
        restrict_network()
        os.execv(binary, [binary, *sys.argv[1:]])
    if not unshare:
        raise SystemExit('namespace backend requires unshare')
    os.execv(unshare, [unshare, '--user', '--map-root-user', '--net', '--', binary, *sys.argv[1:]])


if __name__ == '__main__':
    main()
