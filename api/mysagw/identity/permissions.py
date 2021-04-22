from rest_framework.permissions import BasePermission


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "is_admin", False)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "is_staff", False)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsOrgAdmin(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return obj in request.user.identity.authorized_for


class IsOwnOrAuthorized(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "identity") and (
            obj.identity == request.user.identity
            or obj.identity in request.user.identity.authorized_for
        )
