from rest_framework.permissions import SAFE_METHODS, BasePermission

class IsAdminOrReadOnly(BasePermission):
    """
    Разрешает безопасные (SAFE_METHODS) запросы всем,
    остальные (POST, PUT, DELETE и т.д.) — только администраторам.
    """
    def has_permission(self, request, view):
        """
        Проверяет метод:
        - если метод в SAFE_METHODS — True
        - иначе — пользователь is_staff.
        """
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)
