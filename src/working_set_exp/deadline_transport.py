"""Absolute deadline for the owned loopback HTTP completion transport.

Socket inactivity timeouts alone do not bound a trickling response. A timer
shuts down this request's socket; no worker or model process is left running by
this adapter. The caller must still close its owned runtime after loop closure.
"""
from __future__ import annotations

import http.client
import ipaddress
import socket
import threading
import time
from urllib.parse import urlsplit

from .contribution_limits import SpendingStop


class TransportFailure(RuntimeError):
    def __init__(self, message, data=b"", status=None):
        super().__init__(message)
        self.data, self.status = data, status


def post(base, route, raw, timeout, *, max_bytes=32 * 1024 * 1024):
    target = urlsplit(base)
    if (target.scheme != "http" or target.username or target.password or target.query
            or target.fragment or target.path not in ("", "/")
            or not ipaddress.ip_address(target.hostname).is_loopback):
        raise ValueError("deadline transport requires an explicit loopback HTTP origin")
    if timeout <= 0:
        raise SpendingStop("request_deadline")
    connection = http.client.HTTPConnection(target.hostname, target.port, timeout=timeout)
    expired = threading.Event()
    connected_socket = []
    chunks, status, response = [], None, None
    deadline = time.monotonic() + timeout

    def expire():
        expired.set()
        if connected_socket:
            try:
                connected_socket[0].shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    timer = threading.Timer(timeout, expire)
    timer.daemon = True
    timer.start()
    try:
        connection.connect()
        connected_socket.append(connection.sock)
        if expired.is_set():
            raise SpendingStop("request_deadline")
        connection.request("POST", route, body=raw, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        status = response.status
        size = 0
        while size <= max_bytes and not expired.is_set():
            chunk = response.read1(min(65536, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if expired.is_set() or time.monotonic() >= deadline:
            raise SpendingStop("request_deadline", data=b"".join(chunks), status=status)
        if size > max_bytes:
            raise TransportFailure("response capture allowance exceeded", b"".join(chunks), status)
        if not 200 <= status < 300:
            raise TransportFailure("HTTP response error", b"".join(chunks), status)
        return b"".join(chunks)
    except (OSError, http.client.HTTPException) as error:
        if expired.is_set() or time.monotonic() >= deadline:
            raise SpendingStop("request_deadline", data=b"".join(chunks), status=status) from error
        raise TransportFailure(type(error).__name__, b"".join(chunks), status) from error
    finally:
        timer.cancel()
        if response is not None:
            response.close()
        connection.close()
        timer.join()
