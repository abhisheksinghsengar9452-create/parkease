"""Small dependency-free security controls for local deployment."""
from __future__ import annotations
from collections import defaultdict, deque
from time import monotonic


class SlidingWindowRateLimiter:
    def __init__(self, limit: int = 5, period_seconds: int = 300) -> None:
        self.limit, self.period, self.calls = limit, period_seconds, defaultdict(deque)

    def allowed(self, key: str) -> bool:
        now, window = monotonic(), self.calls[key]
        while window and now - window[0] > self.period: window.popleft()
        if len(window) >= self.limit: return False
        window.append(now); return True

    def reset(self, key: str) -> None:
        self.calls.pop(key, None)


def apply_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
    return response
