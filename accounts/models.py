from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, email):
        # Emails are matched case-insensitively at login.
        return self.get(email__iexact=email)

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)  # always hashed (BR-03)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.OWNER)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["role"] = User.Role.ADMIN
        extra_fields["is_superuser"] = True
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """The SDD `users` table: business owners and administrators."""

    class Role(models.TextChoices):
        OWNER = "OWNER", "Business Owner"
        ADMIN = "ADMIN", "Administrator"

    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=100, unique=True)
    # Stored as a hash only; column named per the SDD data dictionary.
    password = models.CharField("password", max_length=255, db_column="password_hash")
    full_name = models.CharField(max_length=100)
    business_name = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.OWNER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        constraints = [
            # BR-02
            models.CheckConstraint(
                condition=Q(role__in=["OWNER", "ADMIN"]), name="users_role_check"
            ),
            # BR-01 (case-insensitive uniqueness on top of UNIQUE(email))
            models.UniqueConstraint(Lower("email"), name="users_email_lower_uniq"),
        ]

    def __str__(self):
        return self.email

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_staff(self):
        # Lets administrators sign in to Django's built-in admin site.
        return self.is_admin

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email


class ActivityLog(models.Model):
    """The SDD `activity_logs` table (BR-22, BR-23)."""

    class Action(models.TextChoices):
        REGISTER = "REGISTER", "Register"
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        UPLOAD = "UPLOAD", "Upload"

    log_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="activity_logs", db_column="user_id"
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    entity_name = models.CharField(max_length=30, blank=True, null=True)
    entity_id = models.IntegerField(blank=True, null=True)
    details = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_logs"
        ordering = ["-created_at", "-log_id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    action__in=[
                        "REGISTER", "LOGIN", "LOGOUT", "CREATE", "UPDATE", "DELETE", "UPLOAD"
                    ]
                ),
                name="activity_logs_action_check",
            ),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.user_id} {self.action}"
