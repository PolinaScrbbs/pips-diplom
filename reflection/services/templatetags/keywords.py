import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe


register = template.Library()

_KW_RE = re.compile(r"(?i)ключевые\s+слова?\s*[:—-]\s*(?P<list>.+)$")


def _extract_keywords_from_text(text: str) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    for line in str(text).splitlines():
        m = _KW_RE.search(line)
        if not m:
            continue
        raw = m.group("list")
        parts = re.split(r"[,;•·]|\\s{2,}", raw)
        for p in parts:
            w = p.strip().strip(".").strip().lower()
            if not w:
                continue
            w = re.sub(r"\\s+", " ", w)
            if len(w) > 60:
                w = w[:60].rstrip()
            out.append(w)
    seen = set()
    uniq = []
    for w in out:
        if w in seen:
            continue
        seen.add(w)
        uniq.append(w)
    return uniq[:24]


def _wrap_keywords(html: str, words: list[str]) -> str:
    """
    Very simple highlighter: wraps keyword occurrences in a span.
    Assumes input already HTML (e.g. from linebreaks) and escapes keywords.
    """
    out = html
    for w in sorted({(x or "").strip() for x in words if x}, key=len, reverse=True):
        if len(w) < 2:
            continue

        def token_bases(token: str) -> list[str]:
            t = (token or "").strip().lower()
            if len(t) < 4:
                return [t]

            bases = {t}
            # Частые русские окончания/суффиксы — делаем “стем” для склонений.
            if t.endswith("ь"):
                bases.add(t[:-1])
            if t.endswith("ость") and len(t) > 6:
                bases.add(t[:-4])
            if t.endswith("ция") and len(t) > 6:
                bases.add(t[:-3])
            if t.endswith(("ия", "ья")) and len(t) > 5:
                bases.add(t[:-2])

            # Прилагательные/причастия: сенсорная -> сенсорн-
            if t.endswith(("ая", "яя", "ое", "ее", "ые", "ие", "ой", "ый", "ий", "ую", "юю")) and len(t) > 5:
                bases.add(t[:-2])
            # Общий fallback: отрезаем 1 символ, чтобы покрыть ь/а/я
            bases.add(t[:-1])
            # Уберём слишком короткие основы
            cleaned = [b for b in bases if len(b) >= 3]
            return sorted(cleaned, key=len, reverse=True)

        def token_pattern(token: str) -> str:
            # Либо точная форма, либо основа + окончание.
            bases = token_bases(token)
            # Более длинные основы — первыми, чтобы не подсвечивать слишком широко.
            alts = "|".join(re.escape(b) for b in bases if b)
            if not alts:
                return re.escape(token)
            return rf"(?:{alts})[а-яё]{{0,8}}"

        # Подсветка с учётом склонений:
        # - для каждого токена используем основу + окончания
        # - для фраз ("сенсорная интеграция") применяем правило к каждому слову
        tokens = [t for t in re.split(r"\s+", w) if t]
        token_patterns = []
        for t in tokens:
            token_patterns.append(token_pattern(t))
        phrase = r"\s+".join(token_patterns)

        # Case-insensitive, word boundaries for кириллица/латиница/цифры.
        pattern = re.compile(rf"(?i)(?<![\\wа-яё])({phrase})(?![\\wа-яё])")
        out = pattern.sub(
            lambda m: (
                f'<span class="kw" data-kw="{escape(w)}" tabindex="0">{escape(m.group(1))}</span>'
            ),
            out,
        )
    return out


@register.filter
def render_description_with_keywords(text: str) -> str:
    """
    Usage:
      {{ service.description|render_description_with_keywords }}
    """
    raw = str(text or "")
    words = _extract_keywords_from_text(raw)
    # Вырезаем строку "Ключевые слова: ..." из вывода (но используем её для парсинга).
    lines = []
    for ln in raw.splitlines():
        if _KW_RE.search(ln):
            continue
        lines.append(ln)
    raw_for_render = "\n".join(lines).strip()

    # Упрощённый linebreaks (без подключения built-in фильтра внутри):
    escaped = escape(raw_for_render)
    html = escaped.replace("\n\n", "</p><p>").replace("\n", "<br>")
    html = f"<p>{html}</p>"
    return mark_safe(_wrap_keywords(html, words))

