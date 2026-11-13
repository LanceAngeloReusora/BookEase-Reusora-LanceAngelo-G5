from django.contrib.auth.backends import AllowAllUsersModelBackend


class EmailBackend(AllowAllUsersModelBackend):
    """
    Email + password authentication.

    `authenticate()` also returns deactivated users so the login form can show a
    specific "account is deactivated" message (BR-04). `get_user()` refuses
    inactive users, so a deactivated account's existing session stops working
    immediately.
    """

    def get_user(self, user_id):
        user = super().get_user(user_id)
        if user is not None and not user.is_active:
            return None
        return user
