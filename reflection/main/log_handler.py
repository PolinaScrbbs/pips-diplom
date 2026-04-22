"""
main/log_handler.py

DailyFolderFileHandler — кастомный обработчик логов.
Каждое сообщение пишется в файл вида:

    <base_dir>/YYYY-MM/DD.log

При смене суток файл закрывается и открывается новый — без явной ротации
и без перезаписи старых данных (новые просто добавляются в append).
"""
import logging
from datetime import datetime
from pathlib import Path


class DailyFolderFileHandler(logging.Handler):
    """
    Пишет каждую запись в файл, сгруппированный по месяцам и дням.

    Структура:
        media/logs/2026-04/22.log
        media/logs/2026-04/23.log
        media/logs/2026-05/01.log
    """

    def __init__(self, base_dir: str, encoding: str = "utf-8"):
        super().__init__()
        self.base_dir = Path(base_dir)
        self.encoding = encoding
        self._stream = None
        self._current_path: Path | None = None

    def _path_for(self, dt: datetime) -> Path:
        month_dir = dt.strftime("%Y-%m")
        day_name = dt.strftime("%d") + ".log"
        return self.base_dir / month_dir / day_name

    def emit(self, record: logging.LogRecord) -> None:
        try:
            now = datetime.fromtimestamp(record.created)
            target = self._path_for(now)

            if target != self._current_path:
                if self._stream is not None:
                    try:
                        self._stream.close()
                    except Exception:  # noqa: BLE001
                        pass
                target.parent.mkdir(parents=True, exist_ok=True)
                self._stream = target.open("a", encoding=self.encoding)
                self._current_path = target

            self._stream.write(self.format(record) + "\n")
            self._stream.flush()
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def close(self) -> None:
        try:
            if self._stream is not None:
                self._stream.close()
        finally:
            self._stream = None
            self._current_path = None
            super().close()
