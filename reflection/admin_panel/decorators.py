"""
Обратная совместимость: сохраняем импорт `from admin_panel.decorators import admin_required`,
но используем централизованную реализацию из main.utils (рендерит кастомный 403).
"""
from main.utils import admin_required

__all__ = ["admin_required"]
