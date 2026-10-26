import time
import threading
from typing import Dict, Any, Tuple, Optional

class TokenBucketRateLimiter:
    """
    Redis의 Token Bucket 알고리즘을 모사한 고속 인메모리 Throttling 어댑터
    - 특정 제휴사(Client ID)의 트래픽 폭주(DoS)를 차단하여 인증센터 시스템 보호
    """
    def __init__(self, capacity: int = 100, refill_rate_per_sec: float = 50.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self.buckets: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str, tokens_requested: int = 1) -> Tuple[bool, int]:
        """
        요청 허용 여부 판정 (Allow/Deny)
        반환: (허용여부, 잔여 토큰 수)
        """
        with self._lock:
            now = time.time()
            if client_id not in self.buckets:
                self.buckets[client_id] = {
                    "tokens": float(self.capacity),
                    "last_refill": now
                }

            bucket = self.buckets[client_id]
            # 시간 경과에 따른 토큰 충전
            elapsed = now - bucket["last_refill"]
            bucket["tokens"] = min(float(self.capacity), bucket["tokens"] + (elapsed * self.refill_rate))
            bucket["last_refill"] = now

            if bucket["tokens"] >= tokens_requested:
                bucket["tokens"] -= tokens_requested
                return True, int(bucket["tokens"])
            else:
                return False, int(bucket["tokens"])

class CircuitBreaker:
    """
    외부 통신사/연계기관 장애 시 시스템 전체 연쇄 파동(Cascade Failure)을 차단하는 서킷 브레이커
    - 상태: CLOSED (정상) -> OPEN (차단/Fallback) -> HALF_OPEN (복구 테스트)
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout_sec: float = 5.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_sec
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = 0.0
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        with self._lock:
            now = time.time()
            if self.state == "OPEN":
                # 복구 타임아웃 경과 시 HALF_OPEN으로 시도 허용
                if now - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    return True
                return False
            return True

    def record_success(self):
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"

# 싱글톤 부하 제어 인스턴스
rate_limiter = TokenBucketRateLimiter(capacity=100, refill_rate_per_sec=50.0)
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout_sec=3.0)
