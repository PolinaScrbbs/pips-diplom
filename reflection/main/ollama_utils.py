"""
Общие утилиты для вызова локального Ollama из Django.

Поддерживается цепочка URL: сначала основной (часто Docker `ollama:11434`),
при необходимости — fallback на Ollama на хосте (`host.docker.internal`).

При отсутствии модели Ollama часто отвечает HTTP 404 с телом {"error": "..."} —
это отличается от «не тот сервер / не те эндпоинты».
"""

from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlparse


def normalize_ollama_base_url(raw: str) -> str:
    base = (raw or "").strip().rstrip("/")
    if base.endswith("/api"):
        base = base[: -len("/api")]
    return base


def _auto_host_fallback_url() -> str:
    return normalize_ollama_base_url(
        os.getenv("REFLECTION_OLLAMA_AUTO_FALLBACK_URL") or "http://host.docker.internal:11434"
    )


def ollama_endpoint_chain() -> List[Tuple[str, str]]:
    """
    Упорядоченный список (метка, base_url) для перебора.

    1) REFLECTION_OLLAMA_BASE_URL (по умолчанию http://127.0.0.1:11434)
    2) REFLECTION_OLLAMA_FALLBACK_BASE_URL — если задан явно
    3) Авто-fallback на хост Mac/Windows Docker: если основной хост — `ollama`
       (типичный сервис в compose), добавляем host.docker.internal (можно отключить).

    Отключить пункт 3: REFLECTION_OLLAMA_AUTO_HOST_FALLBACK=0
    """
    primary = normalize_ollama_base_url(os.getenv("REFLECTION_OLLAMA_BASE_URL") or "http://127.0.0.1:11434")
    out: List[Tuple[str, str]] = [("docker_or_primary", primary)]
    seen = {primary}

    fb_env = (os.getenv("REFLECTION_OLLAMA_FALLBACK_BASE_URL") or "").strip()
    if fb_env:
        u = normalize_ollama_base_url(fb_env)
        if u not in seen:
            out.append(("fallback_env", u))
            seen.add(u)

    auto_on = (os.getenv("REFLECTION_OLLAMA_AUTO_HOST_FALLBACK", "1") or "1").lower() in (
        "1",
        "true",
        "yes",
        "y",
        "on",
    )
    if auto_on:
        host = (urlparse(primary).hostname or "").lower()
        if host == "ollama":
            u = _auto_host_fallback_url()
            if u not in seen:
                out.append(("host_mac_windows", u))
                seen.add(u)

    return out


def ollama_base_url() -> str:
    """Первый URL цепочки (совместимость со старым кодом)."""
    chain = ollama_endpoint_chain()
    return chain[0][1]


def read_http_error_body(exc: BaseException) -> str:
    """Прочитать тело urllib.error.HTTPError (один раз)."""
    if isinstance(exc, urllib.error.HTTPError):
        try:
            raw = exc.read()
            return raw.decode("utf-8", errors="replace") if raw else ""
        except Exception:
            return ""
    return ""


def short_ollama_error_detail(body: str, *, max_len: int = 220) -> str:
    """Короткая строка для сообщений пользователю/логам."""
    try:
        data = json.loads(body)
        err = str(data.get("error") or "").strip()
        if err:
            return err[:max_len]
    except json.JSONDecodeError:
        pass
    b = (body or "").strip().replace("\n", " ")
    return b[:max_len]


def ollama_response_indicates_missing_model(http_code: int, body: str) -> bool:
    """
    True, если ответ похож на стандартную ошибку Ollama «модель не найдена».

    Не используем один только код 404: nginx может отдать 404 без JSON.
    """
    if http_code != 404:
        return False
    text = (body or "").strip()
    if not text:
        return False
    try:
        data = json.loads(text)
        err = str(data.get("error") or "")
    except json.JSONDecodeError:
        low = text.lower()
        return bool(
            re.search(r"model\s+['\"]?[^'\"]+['\"]?\s+not\s+found", low, flags=re.I)
            or ("model" in low and "not found" in low)
        )
    el = err.lower()
    if "model" in el and ("not found" in el or "does not exist" in el or "unknown model" in el):
        return True
    return False


@dataclass(frozen=True)
class OllamaAttempt:
    label: str
    base_url: str
    reason_code: str
    detail: str


class OllamaTryNext(Exception):
    """Перейти к следующему base URL в цепочке."""

    def __init__(self, *, reason_code: str, detail: str = "", label: str = ""):
        self.reason_code = reason_code
        self.detail = detail
        self.label = label
        super().__init__(detail or reason_code)


def _reason_title_ru(code: str) -> str:
    return {
        "model_not_on_server": "модель на этом узле не найдена",
        "unreachable": "сервер недоступен (сеть / хост не отвечает)",
        "timeout": "таймаут ответа",
        "ollama_api_missing": "на узле нет ожидаемого API Ollama (не те эндпоинты)",
        "http_other": "ошибка HTTP",
        "unknown": "ошибка",
    }.get(code, code)


def format_chain_failure_summary(model: str, attempts: List[OllamaAttempt]) -> str:
    """Итоговое сообщение после неудачи всех узлов цепочки."""
    if not attempts:
        return f"Не удалось обратиться к Ollama для модели {model!r}."

    only_model = all(a.reason_code == "model_not_on_server" for a in attempts)
    if only_model:
        lines = [
            f"Модель {model!r} не найдена ни на одном из перебранных узлов Ollama.",
            "Проверьте `ollama list` на Mac и при необходимости выполните "
            f"`docker compose exec ollama ollama pull {model}` для контейнера.",
        ]
        for a in attempts:
            lines.append(f"— [{a.label}] {a.base_url}: {short_ollama_error_detail(a.detail)}")
        return " ".join(lines)

    lines = [
        f"Не удалось выполнить запрос к Ollama (модель {model!r}) ни через Docker, ни через запасной узел.",
    ]
    for a in attempts:
        lines.append(
            f"— [{a.label}] {a.base_url}: {_reason_title_ru(a.reason_code)} — {short_ollama_error_detail(a.detail)}"
        )
    return " ".join(lines)


def _map_urlerror_to_try_next(exc: urllib.error.URLError, *, label: str) -> OllamaTryNext:
    reason = getattr(exc, "reason", None)
    if isinstance(reason, socket.timeout) or isinstance(exc, TimeoutError):
        return OllamaTryNext(reason_code="timeout", detail=str(exc), label=label)
    if isinstance(reason, ConnectionRefusedError):
        return OllamaTryNext(reason_code="unreachable", detail="connection refused", label=label)
    estr = str(exc).lower()
    if "timed out" in estr or "timeout" in estr:
        return OllamaTryNext(reason_code="timeout", detail=str(exc), label=label)
    return OllamaTryNext(reason_code="unreachable", detail=str(exc), label=label)


def _try_next_for_fatal_http(
    e: urllib.error.HTTPError,
    *,
    body: str,
    label: str,
) -> Optional[OllamaTryNext]:
    """
    После неудачи цепочки эндпоинтов на одном узле: перейти к следующему узлу Ollama,
    если ошибка похожа на временную/узловую (модель не здесь, 5xx, часть 4xx).
    """
    if ollama_response_indicates_missing_model(getattr(e, "code", 0), body):
        return OllamaTryNext(reason_code="model_not_on_server", detail=body, label=label)
    code = getattr(e, "code", None)
    if code and code >= 500:
        return OllamaTryNext(
            reason_code="http_other",
            detail=f"HTTP {code}: {short_ollama_error_detail(body)}",
            label=label,
        )
    # Иные 4xx (кроме «нет маршрута» 404 без модели): пробуем запасной узел (например Docker vs Mac).
    if code and 400 <= code < 500 and code != 404:
        return OllamaTryNext(
            reason_code="http_other",
            detail=f"HTTP {code}: {short_ollama_error_detail(body)}",
            label=label,
        )
    return None


def _post_json(url: str, body: Dict[str, Any], timeout_s: float) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def ollama_keyword_text_at_base(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_s: float,
    label: str,
) -> str:
    """
    Один узел: /api/generate → /api/chat → /v1/chat/completions.
    Успех — текст ответа; при необходимости — OllamaTryNext (перейти к следующему узлу).
    """
    payload_generate = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        data = _post_json(f"{base_url}/api/generate", payload_generate, timeout_s)
        return (data.get("response") or "").strip()
    except urllib.error.HTTPError as e:
        body = read_http_error_body(e)
        if ollama_response_indicates_missing_model(getattr(e, "code", 0), body):
            raise OllamaTryNext(reason_code="model_not_on_server", detail=body, label=label) from e
        if getattr(e, "code", None) != 404:
            nxt = _try_next_for_fatal_http(e, body=body, label=label)
            if nxt:
                raise nxt from e
            raise
        payload_chat = {
            "model": model,
            "stream": False,
            "options": {"temperature": 0.2},
            "messages": [
                {"role": "system", "content": "Ты помощник. Отвечай кратко и по делу."},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            data = _post_json(f"{base_url}/api/chat", payload_chat, timeout_s)
            msg = (data.get("message") or {}) if isinstance(data, dict) else {}
            return (msg.get("content") or "").strip()
        except urllib.error.HTTPError as e2:
            body2 = read_http_error_body(e2)
            if ollama_response_indicates_missing_model(getattr(e2, "code", 0), body2):
                raise OllamaTryNext(reason_code="model_not_on_server", detail=body2, label=label) from e2
            if getattr(e2, "code", None) != 404:
                nxt = _try_next_for_fatal_http(e2, body=body2, label=label)
                if nxt:
                    raise nxt from e2
                raise
            payload_v1 = {
                "model": model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": "Ты помощник. Отвечай кратко и по делу."},
                    {"role": "user", "content": prompt},
                ],
            }
            try:
                data = _post_json(f"{base_url}/v1/chat/completions", payload_v1, timeout_s)
            except urllib.error.HTTPError as e3:
                body3 = read_http_error_body(e3)
                if ollama_response_indicates_missing_model(getattr(e3, "code", 0), body3):
                    raise OllamaTryNext(reason_code="model_not_on_server", detail=body3, label=label) from e3
                tags_status = None
                try:
                    with urllib.request.urlopen(f"{base_url}/api/tags", timeout=min(timeout_s, 15.0)) as resp:
                        tags_status = getattr(resp, "status", None) or 200
                except Exception:
                    tags_status = None
                nxt = _try_next_for_fatal_http(e3, body=body3, label=label)
                if nxt:
                    raise nxt from e3
                raise OllamaTryNext(
                    reason_code="ollama_api_missing",
                    detail=(
                        f"ollama_endpoints_unavailable: generate=404 chat=404 v1={getattr(e3, 'code', None)} "
                        f"tags_status={tags_status}"
                    ),
                    label=label,
                ) from e3
            choices = data.get("choices") or []
            first = choices[0] if choices else {}
            msg = first.get("message") or {}
            return (msg.get("content") or "").strip()
    except urllib.error.URLError as e:
        raise _map_urlerror_to_try_next(e, label=label) from e
    except TimeoutError as e:
        raise OllamaTryNext(reason_code="timeout", detail=str(e), label=label) from e
    except socket.timeout as e:
        raise OllamaTryNext(reason_code="timeout", detail=str(e), label=label) from e


def ollama_keyword_text_with_fallback(*, model: str, prompt: str, timeout_s: float) -> str:
    attempts: List[OllamaAttempt] = []
    for label, base_url in ollama_endpoint_chain():
        try:
            text = ollama_keyword_text_at_base(
                base_url=base_url,
                model=model,
                prompt=prompt,
                timeout_s=timeout_s,
                label=label,
            )
            return re.sub(r"^```\w*\s*|```$", "", text).strip()
        except OllamaTryNext as e:
            attempts.append(
                OllamaAttempt(
                    label=label,
                    base_url=base_url,
                    reason_code=e.reason_code,
                    detail=e.detail,
                )
            )
            continue
    raise RuntimeError(format_chain_failure_summary(model, attempts))


def ollama_insights_json_at_base(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_s: float,
    label: str,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": "10m",
        "options": {"temperature": 0.2},
    }

    def parse_text_to_json(text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", text)
            if not m:
                raise
            return json.loads(m.group(0))

    try:
        data = _post_json(f"{base_url}/api/generate", payload, timeout_s)
        text = (data.get("response") or "").strip()
        return parse_text_to_json(text)
    except urllib.error.HTTPError as e:
        body = read_http_error_body(e)
        if ollama_response_indicates_missing_model(getattr(e, "code", 0), body):
            raise OllamaTryNext(reason_code="model_not_on_server", detail=body, label=label) from e
        if getattr(e, "code", None) != 404:
            nxt = _try_next_for_fatal_http(e, body=body, label=label)
            if nxt:
                raise nxt from e
            raise
        try:
            data = _post_json(
                f"{base_url}/api/chat",
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
                timeout_s,
            )
            msg = (data.get("message") or {}) if isinstance(data, dict) else {}
            text = (msg.get("content") or "").strip()
            return parse_text_to_json(text)
        except urllib.error.HTTPError as e2:
            body2 = read_http_error_body(e2)
            if ollama_response_indicates_missing_model(getattr(e2, "code", 0), body2):
                raise OllamaTryNext(reason_code="model_not_on_server", detail=body2, label=label) from e2
            if getattr(e2, "code", None) != 404:
                nxt = _try_next_for_fatal_http(e2, body=body2, label=label)
                if nxt:
                    raise nxt from e2
                raise
            try:
                data = _post_json(
                    f"{base_url}/v1/chat/completions",
                    {
                        "model": model,
                        "temperature": 0.2,
                        "messages": [
                            {"role": "system", "content": "Возвращай строго JSON по контракту, без Markdown."},
                            {"role": "user", "content": prompt},
                        ],
                    },
                    timeout_s,
                )
            except urllib.error.HTTPError as e3:
                body3 = read_http_error_body(e3)
                if ollama_response_indicates_missing_model(getattr(e3, "code", 0), body3):
                    raise OllamaTryNext(reason_code="model_not_on_server", detail=body3, label=label) from e3
                nxt = _try_next_for_fatal_http(e3, body=body3, label=label)
                if nxt:
                    raise nxt from e3
                raise
            choices = data.get("choices") or []
            first = choices[0] if choices else {}
            msg = first.get("message") or {}
            text = (msg.get("content") or "").strip()
            return parse_text_to_json(text)
    except urllib.error.URLError as e:
        raise _map_urlerror_to_try_next(e, label=label) from e
    except TimeoutError as e:
        raise OllamaTryNext(reason_code="timeout", detail=str(e), label=label) from e
    except socket.timeout as e:
        raise OllamaTryNext(reason_code="timeout", detail=str(e), label=label) from e


def ollama_insights_json_with_fallback(*, model: str, prompt: str, timeout_s: float) -> Dict[str, Any]:
    attempts: List[OllamaAttempt] = []
    for label, base_url in ollama_endpoint_chain():
        try:
            return ollama_insights_json_at_base(
                base_url=base_url,
                model=model,
                prompt=prompt,
                timeout_s=timeout_s,
                label=label,
            )
        except OllamaTryNext as e:
            attempts.append(
                OllamaAttempt(
                    label=label,
                    base_url=base_url,
                    reason_code=e.reason_code,
                    detail=e.detail,
                )
            )
            continue
    raise urllib.error.URLError(format_chain_failure_summary(model, attempts))


def ollama_stream_generate_lines_at_base(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_s: float,
    label: str,
) -> Iterator[Dict[str, Any]]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "format": "json",
        "keep_alive": "10m",
        "options": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout_s)
    except urllib.error.HTTPError as e:
        body = read_http_error_body(e)
        if ollama_response_indicates_missing_model(getattr(e, "code", 0), body):
            raise OllamaTryNext(reason_code="model_not_on_server", detail=body, label=label) from e
        nxt = _try_next_for_fatal_http(e, body=body, label=label)
        if nxt:
            raise nxt from e
        raise
    except urllib.error.URLError as e:
        raise _map_urlerror_to_try_next(e, label=label) from e
    except TimeoutError as e:
        raise OllamaTryNext(reason_code="timeout", detail=str(e), label=label) from e

    try:
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            yield json.loads(line)
    finally:
        try:
            resp.close()
        except Exception:
            pass


def ollama_stream_generate_lines_with_fallback(
    *,
    model: str,
    prompt: str,
    timeout_s: float,
) -> Iterator[Dict[str, Any]]:
    attempts: List[OllamaAttempt] = []
    chain = ollama_endpoint_chain()
    last: Optional[Exception] = None
    for label, base_url in chain:
        try:
            yield from ollama_stream_generate_lines_at_base(
                base_url=base_url,
                model=model,
                prompt=prompt,
                timeout_s=timeout_s,
                label=label,
            )
            return
        except OllamaTryNext as e:
            attempts.append(
                OllamaAttempt(
                    label=label,
                    base_url=base_url,
                    reason_code=e.reason_code,
                    detail=e.detail,
                )
            )
            last = e
            continue
    raise urllib.error.URLError(format_chain_failure_summary(model, attempts)) from last


# --- Совместимость со старыми именами в insights.py ---
def format_model_missing_hint(model: str, *, server_detail: str = "") -> str:
    detail = (server_detail or "").strip()
    if detail:
        detail = f" ({detail})"
    return (
        f"Модель Ollama не найдена на этом узле: {model!r}{detail}. "
        "При Docker сначала проверьте образ `ollama`, затем запасной узел на хосте."
    )
