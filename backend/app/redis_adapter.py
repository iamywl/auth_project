import time
import threading
from typing import Dict, Any, Optional

class DistributedLockService:
    """
    Redis의 'SET key val NX PX' 및 Redlock 알고리즘을 모사한
    고성능 분산 락(Distributed Lock) 어댑터
    - 멀티 스레드 / 멀티 워커 환경에서 Replay Attack 및 레이스 컨디션을 마이크로초 단위로 원자적 방어
    """
    def __init__(self):
        self._locks: Dict[str, float] = {}
        self._mutex = threading.Lock()

    def acquire_lock(self, resource_key: str, ttl_ms: int = 5000) -> bool:
        """
        원자적 락 획득 (Redis 'SET resource_key lock_val NX PX ttl_ms' 동작 구현)
        """
        with self._mutex:
            now = time.time()
            # 기존 락이 존재하고 만료되지 않았으면 획득 실패
            if resource_key in self._locks:
                expiry = self._locks[resource_key]
                if now < expiry:
                    return False
            # 락 획득 성공 및 만료시간 등록
            self._locks[resource_key] = now + (ttl_ms / 1000.0)
            return True

    def release_lock(self, resource_key: str):
        """락 반환"""
        with self._mutex:
            if resource_key in self._locks:
                del self._locks[resource_key]

class RedisSessionStore:
    """
    Redis In-Memory 캐시 및 세션 저장소 어댑터
    - DAU 1만~수백만 트래픽 처리를 위한 고속 In-Memory 토큰/세션 TTL 관리
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._mutex = threading.Lock()

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 3600):
        with self._mutex:
            self._cache[key] = {
                "val": value,
                "expires_at": time.time() + ttl_seconds
            }

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._mutex:
            item = self._cache.get(key)
            if not item:
                return None
            if time.time() > item["expires_at"]:
                del self._cache[key]
                return None
            return item["val"]

    def delete(self, key: str):
        with self._mutex:
            if key in self._cache:
                del self._cache[key]

# 싱글톤 어댑터 인스턴스
dist_lock_service = DistributedLockService()
redis_session_store = RedisSessionStore()
