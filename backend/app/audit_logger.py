import hashlib
import json
import datetime
import threading
from typing import List, Dict, Any, Optional

class HashChainAuditLogger:
    """
    전자금융거래법 및 본인확인/전자서명 심사 대응용
    블록체인형 Hash-Chain 위·변조 방지 감사 로그 엔진
    - Thread-safe Lock을 내장하여 고동시성 멀티스레드 환경에서도 해시 체인 파손(Forking) 방지
    """
    def __init__(self):
        self.chain: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis_log = {
            "index": 0,
            "timestamp": "2026-10-26T00:00:00Z",
            "action": "GENESIS_AUDIT_LOG_INITIALIZED",
            "client_id": "SYSTEM",
            "tx_id": "TX_GENESIS",
            "payload_summary": {"description": "KakaoBank Auth Center Audit Chain Started"},
            "prev_hash": "0" * 64,
            "hash": ""
        }
        genesis_log["hash"] = self._calculate_hash(genesis_log)
        self.chain.append(genesis_log)

    def _calculate_hash(self, record: Dict[str, Any]) -> str:
        data_to_hash = f"{record['index']}:{record['timestamp']}:{record['action']}:{record['client_id']}:{record['tx_id']}:{json.dumps(record['payload_summary'], sort_keys=True)}:{record['prev_hash']}"
        return hashlib.sha256(data_to_hash.encode("utf-8")).hexdigest()

    def log(self, action: str, client_id: str, tx_id: str, payload_summary: Dict[str, Any]) -> Dict[str, Any]:
        """새 감사 로그 레코드 체인에 추가 (동시성 락 적용)"""
        with self._lock:
            prev_block = self.chain[-1]
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            record = {
                "index": len(self.chain),
                "timestamp": now_str,
                "action": action,
                "client_id": client_id,
                "tx_id": tx_id,
                "payload_summary": payload_summary,
                "prev_hash": prev_block["hash"],
                "hash": ""
            }
            record["hash"] = self._calculate_hash(record)
            self.chain.append(record)
            return record

    def verify_integrity(self) -> Dict[str, Any]:
        """전체 감사 체인의 수학적 무결성 전수 검증 (심사 증적 추출용)"""
        with self._lock:
            for i in range(1, len(self.chain)):
                current = self.chain[i]
                previous = self.chain[i - 1]

                # 1. 이전 블록 해시 링크 확인
                if current["prev_hash"] != previous["hash"]:
                    return {
                        "is_valid": False,
                        "broken_index": i,
                        "reason": f"해시 링크 불일치 (인덱스 {i}의 prev_hash != 인덱스 {i-1}의 hash)"
                    }

                # 2. 현재 블록 해시 재계산 검증
                recalculated = self._calculate_hash(current)
                if current["hash"] != recalculated:
                    return {
                        "is_valid": False,
                        "broken_index": i,
                        "reason": f"레코드 조작 감지 (인덱스 {i}의 데이터 변조)"
                    }

            return {
                "is_valid": True,
                "total_records": len(self.chain),
                "latest_hash": self.chain[-1]["hash"],
                "message": "감사 로그 전수 검사 완료: 단 1건의 위·변조 없음 (100% 무결성 확인)"
            }

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self.chain[-limit:]))

audit_logger = HashChainAuditLogger()
