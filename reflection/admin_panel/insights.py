import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class InsightsResult:
    mode: str  # "heuristic" | "llm" (reserved)
    input_digest: str
    generated_at: str  # ISO datetime
    insights: Dict[str, Any]
    llm_error: Optional[str] = None


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _digest(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def sanitize_stats_data(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Готовим payload для генерации инсайтов.

    Важно: этот payload может пойти в LLM (в будущем), поэтому:
    - оставляем только агрегаты;
    - удаляем любые персональные идентификаторы.
    """
    days = int(stats.get("days") or 30)
    kpi = dict(stats.get("kpi") or {})
    series = dict(stats.get("series") or {})

    # top_clients содержит username → для инсайтов исключаем имена.
    top_clients = stats.get("top_clients") or []
    top_clients_counts = [int(x.get("c") or 0) for x in top_clients if isinstance(x, dict)]

    top_services = stats.get("top_services") or []
    safe_top_services = []
    for row in top_services:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")[:80]
        c = int(row.get("c") or 0)
        safe_top_services.append({"name": name, "c": c})

    rating_counts = list(stats.get("rating_counts") or [0, 0, 0, 0, 0])[:5]
    weekday_counts = list(stats.get("weekday_counts") or [0] * 7)[:7]
    hour_counts = list(stats.get("hour_counts") or [0] * 24)[:24]

    labels = list(series.get("labels") or [])
    signups = list(series.get("signups") or [])
    bookings = list(series.get("bookings") or [])
    revenue = list(series.get("revenue") or [])

    # NOTE: по запросу для дипломной демонстрации отправляем весь ряд без усечения.

    safe = {
        "days": days,
        "kpi": {
            "total_users": int(kpi.get("total_users") or 0),
            "users_by_role": dict(kpi.get("users_by_role") or {}),
            "active_services": int(kpi.get("active_services") or 0),
            "total_services": int(kpi.get("total_services") or 0),
            "total_bookings": int(kpi.get("total_bookings") or 0),
            "bookings_in_period": int(kpi.get("bookings_in_period") or 0),
            "avg_rating": kpi.get("avg_rating"),
            "total_reviews": int(kpi.get("total_reviews") or 0),
            "total_revenue": float(kpi.get("total_revenue") or 0),
        },
        "series": {
            "labels": labels,
            "signups": [float(x or 0) for x in signups],
            "bookings": [float(x or 0) for x in bookings],
            "revenue": [float(x or 0) for x in revenue],
        },
        "top_services": safe_top_services[:8],
        "rating_counts": [int(x or 0) for x in rating_counts],
        "weekday_counts": [int(x or 0) for x in weekday_counts],
        "hour_counts": [int(x or 0) for x in hour_counts],
        "top_clients_counts": top_clients_counts[:5],
    }
    return safe


_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_URL_RE = re.compile(r"\bhttps?://[^\s]+", re.IGNORECASE)
_SECRETISH_RE = re.compile(r"\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*([^\s]+)", re.IGNORECASE)


def mask_text(text: str, *, max_len: int = 500) -> str:
    """
    Минимальная маскировка PII/секретов для текстовых полей (логи/отзывы).
    Не пытается быть идеальной, но закрывает типичные случаи.
    """
    s = str(text or "")
    s = _EMAIL_RE.sub("[email]", s)
    s = _URL_RE.sub("[url]", s)
    s = _SECRETISH_RE.sub(lambda m: f"{m.group(1)}=[redacted]", s)
    s = _PHONE_RE.sub("[phone]", s)
    s = re.sub(r"\s+", " ", s).strip()
    if max_len and len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    return s


def limit_items(items: List[Any], *, max_items: int) -> List[Any]:
    if max_items <= 0:
        return []
    if len(items) <= max_items:
        return items
    return items[:max_items]


def normalize_sql(sql: str, *, max_len: int = 400) -> str:
    """
    Нормализуем SQL для безопасной отправки:
    - убираем строковые литералы и числа → placeholders
    - схлопываем пробелы
    """
    s = str(sql or "")
    s = re.sub(r"'.*?'", "?", s)
    s = re.sub(r"\\b\\d+\\b", "?", s)
    s = re.sub(r"\\s+", " ", s).strip()
    if max_len and len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    return s


def _ollama_base_url() -> str:
    """
    Base URL для Ollama.

    В Docker 127.0.0.1 указывает на контейнер, поэтому адрес нужно уметь
    настраивать, например: http://ollama:11434.
    """
    try:
        import os

        base = (os.getenv("REFLECTION_OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
        if base.endswith("/api"):
            base = base[: -len("/api")]
        return base
    except Exception:
        return "http://127.0.0.1:11434"


def _ollama_generate_json(*, model: str, prompt: str, timeout_s: float) -> Dict[str, Any]:
    """
    Вызов локальной LLM через Ollama (бесплатно, офлайн).
    Ожидаем JSON-ответ в поле `response`.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        # Просим Ollama вернуть валидный JSON (если поддерживается runtime'ом).
        "format": "json",
        # Держим модель прогретой, чтобы повторные запросы были быстрее.
        "keep_alive": "10m",
        # Делаем вывод более детерминированным и JSON-дружелюбным.
        "options": {
            "temperature": 0.2,
            # Убираем ограничение генерации — пусть модель сама решает,
            # но промпт просит короткий результат.
        },
    }
    def _read_json(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        req = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)

    try:
        data = _read_json(f"{_ollama_base_url()}/api/generate", payload)
        text = (data.get("response") or "").strip()
    except urllib.error.HTTPError as e:
        # Если /api/generate недоступен (404), пробуем /api/chat.
        if getattr(e, "code", None) != 404:
            raise
        try:
            data = _read_json(
                f"{_ollama_base_url()}/api/chat",
                {
                    "model": model,
                    "stream": False,
                    "format": "json",
                    "keep_alive": "10m",
                    "options": {"temperature": 0.2},
                    "messages": [
                        {"role": "system", "content": "Возвращай строго JSON по контракту, без Markdown."},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            msg = (data.get("message") or {}) if isinstance(data, dict) else {}
            text = (msg.get("content") or "").strip()
        except urllib.error.HTTPError as e2:
            if getattr(e2, "code", None) != 404:
                raise
            # OpenAI-совместимый fallback
            data = _read_json(
                f"{_ollama_base_url()}/v1/chat/completions",
                {
                    "model": model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": "Возвращай строго JSON по контракту, без Markdown."},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            choices = data.get("choices") or []
            first = choices[0] if choices else {}
            msg = first.get("message") or {}
            text = (msg.get("content") or "").strip()
    # Попытка распарсить как JSON. Если модель обернула в текст — вырежем блок {...}.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise
        return json.loads(m.group(0))


def ollama_stream_response(*, model: str, prompt: str, timeout_s: float):
    """
    Потоковая генерация Ollama (stream=true).
    Возвращает итератор словарей: каждый элемент — JSON-объект из одной строки стрима.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "format": "json",
        "keep_alive": "10m",
        "options": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        f"{_ollama_base_url()}/api/generate",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=timeout_s)
    for raw_line in resp:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        yield json.loads(line)


def _llm_prompt_stats(*, compact: Dict[str, Any]) -> str:
    """
    Промпт под JSON-контракт, который уже ожидает UI.
    """
    contract = {
        "summary": "string",
        "changes": [
            {"text": "string", "metric": "string", "new": "number", "old": "number", "pct": "number|null", "unit": "string"}
        ],
        "anomalies": ["string"],
        "recommendations": ["string"],
        "numbers_used": {
            "signups_7d": "number",
            "signups_prev_7d": "number",
            "bookings_7d": "number",
            "bookings_prev_7d": "number",
            "revenue_7d": "number",
            "revenue_prev_7d": "number",
        },
        "input_days": "number",
    }
    return (
        "Ты аналитик админ-дашборда. Сгенерируй инсайты по агрегированным метрикам.\n"
        "ВАЖНО:\n"
        "- Верни СТРОГО валидный JSON без Markdown и без пояснений.\n"
        "- Не выдумывай числа: используй ТОЛЬКО входные.\n"
        "- Не упоминай персональные данные (их во входе нет).\n"
        "- recommendations: 3–5 пунктов, коротко и по делу.\n"
        f"\nКонтракт JSON (пример типов):\n{json.dumps(contract, ensure_ascii=False)}\n"
        f"\nВходные данные (компактные агрегаты):\n{json.dumps(compact, ensure_ascii=False)}\n"
    )


def generate_stats_insights(stats_data: Dict[str, Any], *, prefer_llm: bool = True) -> InsightsResult:
    """
    Генератор инсайтов:
    - если доступна локальная LLM (Ollama) и prefer_llm=True → mode='llm'
    - иначе → fallback на детерминированные эвристики mode='heuristic'
    """
    safe = sanitize_stats_data(stats_data)
    digest = _digest(safe)

    if prefer_llm:
        model = "qwen2.5:7b-instruct"
        try:
            import os

            model = os.getenv("REFLECTION_LLM_MODEL") or model
        except Exception:
            pass
        timeout_s = 180.0
        try:
            import os

            timeout_s = float(os.getenv("REFLECTION_LLM_TIMEOUT_S") or timeout_s)
        except Exception:
            pass
        try:
            # По запросу: отправляем ВСЕ агрегированные данные (без PII), включая полный ряд.
            series = safe.get("series") or {}
            labels = list(series.get("labels") or [])
            signups = list(series.get("signups") or [])
            bookings = list(series.get("bookings") or [])
            revenue = list(series.get("revenue") or [])

            window = 7
            numbers_used = {
                "signups_7d": _sum_last_n(signups, window, offset_from_end=0),
                "signups_prev_7d": _sum_last_n(signups, window, offset_from_end=window),
                "bookings_7d": _sum_last_n(bookings, window, offset_from_end=0),
                "bookings_prev_7d": _sum_last_n(bookings, window, offset_from_end=window),
                "revenue_7d": _sum_last_n(revenue, window, offset_from_end=0),
                "revenue_prev_7d": _sum_last_n(revenue, window, offset_from_end=window),
            }

            full_payload = dict(safe)
            full_payload["numbers_used"] = numbers_used
            out = _ollama_generate_json(
                model=model,
                prompt=_llm_prompt_stats(compact=full_payload),
                timeout_s=timeout_s,
            )
            # Минимальная валидация под UI-контракт.
            if isinstance(out, dict) and "summary" in out and "recommendations" in out:
                out["input_days"] = out.get("input_days") or safe.get("days")
                out["numbers_used"] = out.get("numbers_used") or numbers_used
                return InsightsResult(
                    mode="llm",
                    input_digest=digest,
                    generated_at=_iso_now(),
                    insights=out,
                    llm_error=None,
                )
        except (urllib.error.URLError, TimeoutError) as e:
            return _generate_stats_insights_heuristic(safe=safe, digest=digest, llm_error=f"ollama_unreachable_or_timeout: {type(e).__name__}")
        except json.JSONDecodeError:
            return _generate_stats_insights_heuristic(safe=safe, digest=digest, llm_error="ollama_invalid_json")

    # Fallback на эвристики (старое поведение).
    return _generate_stats_insights_heuristic(safe=safe, digest=digest, llm_error=None)


def _generate_stats_insights_heuristic(*, safe: Dict[str, Any], digest: str, llm_error: Optional[str]) -> InsightsResult:
    labels = safe["series"]["labels"]
    signups = safe["series"]["signups"]
    bookings = safe["series"]["bookings"]
    revenue = safe["series"]["revenue"]

    # Сравнение последних 7 дней с предыдущими 7 днями (если хватает точек).
    window = 7
    new_signups = _sum_last_n(signups, window, offset_from_end=0)
    old_signups = _sum_last_n(signups, window, offset_from_end=window)
    new_bookings = _sum_last_n(bookings, window, offset_from_end=0)
    old_bookings = _sum_last_n(bookings, window, offset_from_end=window)
    new_revenue = _sum_last_n(revenue, window, offset_from_end=0)
    old_revenue = _sum_last_n(revenue, window, offset_from_end=window)

    changes: List[Dict[str, Any]] = []
    line, meta = _trend_line("Регистрации (7д)", new_signups, old_signups)
    changes.append({"text": line, **meta})
    line, meta = _trend_line("Записи (7д)", new_bookings, old_bookings)
    changes.append({"text": line, **meta})
    line, meta = _trend_line("Оборот (7д)", new_revenue, old_revenue, unit=" ₽")
    changes.append({"text": line, **meta})

    # Аномалии: простая проверка на “пики” в последних точках.
    anomalies: List[str] = []
    if len(bookings) >= 14:
        last = bookings[-1]
        prev_avg = sum(bookings[-14:-1]) / 13.0 if sum(bookings[-14:-1]) > 0 else 0.0
        if prev_avg > 0 and last >= prev_avg * 2.2:
            anomalies.append(
                f"Пик записей в последний день: {last:.0f} при среднем {prev_avg:.1f} за предыдущие 13 дней."
            )
        if prev_avg > 0 and last <= prev_avg * 0.35:
            anomalies.append(
                f"Провал записей в последний день: {last:.0f} при среднем {prev_avg:.1f} за предыдущие 13 дней."
            )

    # Рекомендации: на основе тенденций + распределений.
    recommendations: List[str] = []
    pct_b = _pct_change(new_bookings, old_bookings)
    pct_r = _pct_change(new_revenue, old_revenue)
    if pct_b is not None and pct_b < -15:
        recommendations.append("Падение записей за неделю: проверьте источники трафика и доступность слотов; запустите промо на топ-услуги.")
    if pct_r is not None and pct_r < -15:
        recommendations.append("Падение оборота: посмотрите структуру записей по услугам и средний чек; возможно, чаще выбирают дешёвые услуги.")
    if not recommendations:
        recommendations.append("Стабильная динамика: сфокусируйтесь на росте — продвигайте топ-услуги и стимулируйте отзывы после визита.")

    top_services = safe.get("top_services") or []
    if top_services:
        recommendations.append(
            "Топ-услуги по записям: " + ", ".join(f"{s['name']} ({s['c']})" for s in top_services[:3])
        )

    summary_bits: List[str] = []
    if labels:
        summary_bits.append(f"Период: последние {safe.get('days')} дней (для сравнений — окно 7 дней).")
    avg_rating = safe["kpi"].get("avg_rating")
    if avg_rating is not None:
        summary_bits.append(f"Средняя оценка: {avg_rating}/5.")
    summary = " ".join(summary_bits).strip()

    payload = {
        "summary": summary,
        "changes": changes,
        "anomalies": anomalies,
        "recommendations": recommendations[:5],
        "numbers_used": {
            "signups_7d": new_signups,
            "signups_prev_7d": old_signups,
            "bookings_7d": new_bookings,
            "bookings_prev_7d": old_bookings,
            "revenue_7d": new_revenue,
            "revenue_prev_7d": old_revenue,
        },
        "input_days": safe.get("days"),
    }
    return InsightsResult(
        mode="heuristic",
        input_digest=digest,
        generated_at=_iso_now(),
        insights=payload,
        llm_error=llm_error,
    )


def _sum_last_n(values: List[float], n: int, *, offset_from_end: int = 0) -> float:
    if n <= 0 or not values:
        return 0.0
    end = len(values) - offset_from_end
    start = max(0, end - n)
    chunk = values[start:end]
    return float(sum(float(x or 0) for x in chunk))


def _pct_change(new: float, old: float) -> Optional[float]:
    if old == 0:
        return None
    return (new - old) / old * 100.0


def _trend_line(name: str, new: float, old: float, unit: str = "") -> Tuple[str, Dict[str, Any]]:
    pct = _pct_change(new, old)
    meta = {"metric": name, "new": new, "old": old, "pct": pct, "unit": unit}
    if pct is None:
        return f"{name}: {new:.0f}{unit} (нет базы для сравнения)", meta
    arrow = "рост" if pct > 0 else "падение" if pct < 0 else "без изменений"
    return f"{name}: {new:.0f}{unit} vs {old:.0f}{unit} ({arrow} {abs(pct):.1f}%)", meta


def generate_stats_insights_compat(stats_data: Dict[str, Any]) -> InsightsResult:
    """
    Backward-compat wrapper for older imports.
    Prefer calling `generate_stats_insights(..., prefer_llm=...)` directly.
    """
    return generate_stats_insights(stats_data, prefer_llm=True)
