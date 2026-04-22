"""
Thread-safe кольцевой буфер последних SQL-запросов.
Заполняется из `QueryLogMiddleware` для каждого запроса админа.
Хранится в памяти процесса — при рестарте обнуляется.
"""
import threading
from collections import deque
from datetime import datetime
from typing import Optional


class QueryLog:
    """Bounded in-memory журнал SQL-запросов. Concurrency-safe."""

    MAX_SIZE = 500

    def __init__(self) -> None:
        self._buffer: deque = deque(maxlen=self.MAX_SIZE)
        self._lock = threading.Lock()
        self._seq = 0

    def record(
        self,
        sql: str,
        duration_ms: float,
        *,
        path: str = "",
        method: str = "",
        user: str = "",
        status: Optional[int] = None,
    ) -> None:
        with self._lock:
            self._seq += 1
            self._buffer.append({
                "id": self._seq,
                "sql": sql,
                "duration_ms": round(duration_ms, 3),
                "ts": datetime.now().isoformat(timespec="milliseconds"),
                "path": path,
                "method": method,
                "user": user,
                "status": status,
                "op": _sql_op(sql),
            })

    def recent(self, since_id: Optional[int] = None, limit: int = 200):
        with self._lock:
            items = list(self._buffer)
        if since_id is not None:
            items = [x for x in items if x["id"] > since_id]
        if limit and len(items) > limit:
            items = items[-limit:]
        return items

    def stats(self):
        with self._lock:
            items = list(self._buffer)
            total_seq = self._seq
        if not items:
            return {
                "buffer_size": 0,
                "total_seen": total_seq,
                "avg_ms": 0,
                "max_ms": 0,
                "min_ms": 0,
                "slow_count": 0,
            }
        durations = [x["duration_ms"] for x in items]
        slow = sum(1 for d in durations if d >= 50)
        return {
            "buffer_size": len(items),
            "total_seen": total_seq,
            "avg_ms": round(sum(durations) / len(durations), 2),
            "max_ms": round(max(durations), 2),
            "min_ms": round(min(durations), 2),
            "slow_count": slow,
        }

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
            self._seq = 0


def _sql_op(sql: str) -> str:
    """Грубо извлекает тип оператора (SELECT/INSERT/UPDATE/DELETE/OTHER)."""
    head = (sql or "").lstrip().split(" ", 1)[0].upper()
    if head in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        return head
    return "OTHER"


# singleton
query_log = QueryLog()
