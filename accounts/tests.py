from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import ActivityLog, User

PASSWORD = "Str0ng-Pass-123"


def make_owner(email="owner@example.com", **kwargs):
    kwargs.setdefault("full_name", "Olive Owner")
    return User.objects.create_user(email=email, password=PASSWORD, **kwargs)


def make_admin(email="admin@example.com", **kwargs):
    kwargs.setdefault("full_name", "Adam Admin")
    return User.objects.create_superuser(email=email, password=PASSWORD, **kwargs)


class RegistrationTests(TestCase):
    url = reverse("accounts:register")

    def data(self, **overrides):
        data = {
            "full_name": "Juan Dela Cruz",
            "business_name": "Juan's Store",
            "email": "juan@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return data

    def test_page_loads(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_successful_registration(self):
        response = self.client.post(self.url, self.data(), follow=True)
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertContains(response, "Account created successfully")
        user = User.objects.get(email="juan@example.com")
        self.assertEqual(user.role, User.Role.OWNER)
        self.assertTrue(user.is_active)
        self.assertTrue(
            ActivityLog.objects.filter(user=user, action=ActivityLog.Action.REGISTER).exists()
        )

    def test_password_is_hashed(self):
        self.client.post(self.url, self.data())
        user = User.objects.get(email="juan@example.com")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertTrue(user.check_password(PASSWORD))

    def test_required_fields(self):
        response = self.client.post(self.url, {})
        self.assertEqual(User.objects.count(), 0)
        for field in ("full_name", "email", "password1", "password2"):
            self.assertIn(field, response.context["form"].errors)
        self.assertContains(response, "Registration failed")

    def test_invalid_email(self):
        response = self.client.post(self.url, self.data(email="not-an-email"))
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_email(self):
        make_owner("juan@example.com")
        response = self.client.post(self.url, self.data())
        self.assertContains(response, "already exists")
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_email_is_case_insensitive(self):
        make_owner("juan@example.com")
        response = self.client.post(self.url, self.data(email="JUAN@Example.com"))
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch(self):
        response = self.client.post(self.url, self.data(password2="Different-Pass-999"))
        self.assertIn("password2", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_password_too_short(self):
        response = self.client.post(self.url, self.data(password1="Ab1!xyz", password2="Ab1!xyz"))
        self.assertIn("password2", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_cannot_self_register_as_admin(self):
        self.client.post(self.url, self.data(role="ADMIN"))
        self.assertEqual(User.objects.get(email="juan@example.com").role, User.Role.OWNER)

    def test_logged_in_user_is_redirected_away(self):
        self.client.force_login(make_owner())
        self.assertRedirects(
            self.client.get(self.url),
            reverse("accounts:dashboard"),
            fetch_redirect_response=False,
        )


class LoginLogoutTests(TestCase):
    login_url = reverse("accounts:login")

    def test_owner_login_goes_to_owner_dashboard(self):
        make_owner()
        response = self.client.post(
            self.login_url, {"username": "owner@example.com", "password": PASSWORD}, follow=True
        )
        self.assertRedirects(response, reverse("accounts:owner_dashboard"))
        self.assertContains(response, "Welcome back")

    def test_admin_login_goes_to_admin_dashboard(self):
        make_admin()
        response = self.client.post(
            self.login_url, {"username": "admin@example.com", "password": PASSWORD}, follow=True
        )
        self.assertRedirects(response, reverse("accounts:admin_dashboard"))

    def test_login_email_is_case_insensitive(self):
        make_owner()
        response = self.client.post(
            self.login_url, {"username": "OWNER@Example.com", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 302)

    def test_invalid_credentials(self):
        make_owner()
        response = self.client.post(
            self.login_url, {"username": "owner@example.com", "password": "wrong-password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_email(self):
        response = self.client.post(
            self.login_url, {"username": "nobody@example.com", "password": PASSWORD}
        )
        self.assertContains(response, "Invalid email or password")

    def test_deactivated_account_cannot_login(self):
        make_owner(is_active=False)
        response = self.client.post(
            self.login_url, {"username": "owner@example.com", "password": PASSWORD}
        )
        self.assertContains(response, "deactivated")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_ends_session(self):
        self.client.force_login(make_owner())
        response = self.client.post(reverse("accounts:logout"), follow=True)
        self.assertRedirects(response, self.login_url)
        self.assertContains(response, "logged out")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        self.client.force_login(make_owner())
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)

    def test_login_and_logout_are_logged(self):
        user = make_owner()
        self.client.post(self.login_url, {"username": user.email, "password": PASSWORD})
        self.client.post(reverse("accounts:logout"))
        actions = set(user.activity_logs.values_list("action", flat=True))
        self.assertIn("LOGIN", actions)
        self.assertIn("LOGOUT", actions)


class AccessControlTests(TestCase):
    protected = [
        "accounts:dashboard",
        "accounts:owner_dashboard",
        "accounts:admin_dashboard",
        "accounts:admin_users",
        "accounts:admin_activity",
        "accounts:profile",
        "accounts:profile_edit",
        "accounts:password_change",
    ]

    def test_logged_out_users_are_sent_to_login(self):
        for name in self.protected:
            with self.subTest(page=name):
                url = reverse(name)
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('accounts:login')}?next={url}",
                    fetch_redirect_response=False,
                )

    def test_owner_cannot_open_admin_pages(self):
        self.client.force_login(make_owner())
        for name in ("accounts:admin_dashboard", "accounts:admin_users", "accounts:admin_activity"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_admin_cannot_open_owner_dashboard(self):
        self.client.force_login(make_admin())
        self.assertEqual(self.client.get(reverse("accounts:owner_dashboard")).status_code, 403)

    def test_dashboard_router_by_role(self):
        self.client.force_login(make_owner())
        self.assertRedirects(
            self.client.get(reverse("accounts:dashboard")),
            reverse("accounts:owner_dashboard"),
            fetch_redirect_response=False,
        )
        self.client.force_login(make_admin())
        self.assertRedirects(
            self.client.get(reverse("accounts:dashboard")),
            reverse("accounts:admin_dashboard"),
            fetch_redirect_response=False,
        )

    def test_dashboards_show_role_content(self):
        self.client.force_login(make_owner())
        self.assertContains(self.client.get(reverse("accounts:owner_dashboard")), "Business Owner dashboard")
        self.client.force_login(make_admin())
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertContains(response, "Administrator dashboard")
        self.assertContains(response, "Manage users")

    def test_owner_nav_has_no_admin_links(self):
        self.client.force_login(make_owner())
        response = self.client.get(reverse("accounts:owner_dashboard"))
        self.assertNotContains(response, reverse("accounts:admin_users"))

    def test_deactivated_users_session_stops_working(self):
        user = make_owner()
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:owner_dashboard")).status_code, 200)
        User.objects.filter(pk=user.pk).update(is_active=False)
        self.assertEqual(self.client.get(reverse("accounts:owner_dashboard")).status_code, 302)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_owner(business_name="Olive's Shop")
        self.other = make_owner("other@example.com", full_name="Other Person")
        self.client.force_login(self.user)

    def test_view_own_profile(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "Olive Owner")
        self.assertContains(response, "owner@example.com")
        self.assertNotContains(response, "other@example.com")

    def test_update_profile(self):
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {"full_name": "Olive R. Owner", "business_name": "New Shop", "email": "New@Example.com"},
            follow=True,
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertContains(response, "updated successfully")
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Olive R. Owner")
        self.assertEqual(self.user.business_name, "New Shop")
        self.assertEqual(self.user.email, "new@example.com")
        self.assertTrue(self.user.activity_logs.filter(action="UPDATE").exists())

    def test_cannot_take_another_users_email(self):
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {"full_name": "Olive", "business_name": "", "email": "OTHER@example.com"},
        )
        self.assertIn("email", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "owner@example.com")

    def test_keeping_own_email_is_allowed(self):
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {"full_name": "Olive", "business_name": "", "email": "owner@example.com"},
        )
        self.assertEqual(response.status_code, 302)

    def test_role_cannot_be_changed_via_profile(self):
        self.client.post(
            reverse("accounts:profile_edit"),
            {"full_name": "Olive", "business_name": "", "email": "owner@example.com", "role": "ADMIN"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.OWNER)

    def test_profile_edit_only_touches_own_record(self):
        self.client.post(
            reverse("accounts:profile_edit"),
            {"full_name": "Changed", "business_name": "", "email": "owner@example.com"},
        )
        self.other.refresh_from_db()
        self.assertEqual(self.other.full_name, "Other Person")

    def test_change_password(self):
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": "Another-Str0ng-Pass",
                "new_password2": "Another-Str0ng-Pass",
            },
            follow=True,
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Another-Str0ng-Pass"))
        # Still logged in afterwards.
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)

    def test_change_password_wrong_old_password(self):
        response = self.client.post(
            reverse("accounts:password_change"),
            {"old_password": "nope", "new_password1": "Another-Str0ng-Pass", "new_password2": "Another-Str0ng-Pass"},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))


class AdminUserManagementTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.owner = make_owner()
        self.client.force_login(self.admin)

    def toggle(self, user):
        return self.client.post(reverse("accounts:admin_user_toggle", args=[user.pk]))

    def test_admin_can_deactivate_and_reactivate(self):
        self.toggle(self.owner)
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.is_active)
        self.assertTrue(self.admin.activity_logs.filter(action="UPDATE", entity_id=self.owner.pk).exists())
        self.toggle(self.owner)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.is_active)

    def test_admin_cannot_deactivate_self(self):
        self.toggle(self.admin)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_owner_cannot_deactivate_anyone(self):
        other = make_owner("other@example.com")
        self.client.force_login(self.owner)
        self.assertEqual(self.toggle(other).status_code, 403)
        other.refresh_from_db()
        self.assertTrue(other.is_active)

    def test_toggle_rejects_get(self):
        self.assertEqual(
            self.client.get(reverse("accounts:admin_user_toggle", args=[self.owner.pk])).status_code, 405
        )

    def test_open_redirect_is_blocked(self):
        response = self.client.post(
            reverse("accounts:admin_user_toggle", args=[self.owner.pk]), {"next": "https://evil.example.com/"}
        )
        self.assertRedirects(response, reverse("accounts:admin_users"), fetch_redirect_response=False)

    def test_user_search(self):
        make_owner("findme@example.com", full_name="Zed Zebra")
        response = self.client.get(reverse("accounts:admin_users"), {"q": "zebra"})
        self.assertContains(response, "findme@example.com")
        self.assertNotContains(response, "owner@example.com")

    def test_admin_activity_log_view(self):
        self.client.post(reverse("accounts:logout"))
        self.client.post(
            reverse("accounts:login"), {"username": self.admin.email, "password": PASSWORD}
        )
        response = self.client.get(reverse("accounts:admin_activity"), {"action": "LOGIN"})
        self.assertContains(response, "admin@example.com")


class DatabaseConstraintTests(TestCase):
    """The SDD rules that are enforced by PostgreSQL itself."""

    def test_unique_email_br01(self):
        make_owner("dup@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email="dup@example.com", full_name="X", password="x")

    def test_unique_email_ignores_case(self):
        make_owner("dup@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email="DUP@example.com", full_name="X", password="x")

    def test_role_check_br02(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email="r@example.com", full_name="X", password="x", role="HACKER")

    def test_activity_action_check_br22(self):
        user = make_owner()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ActivityLog.objects.create(user=user, action="EXPLODE")

    def test_user_with_logs_cannot_be_deleted_br04(self):
        user = make_owner()
        ActivityLog.objects.create(user=user, action="LOGIN")
        from django.db.models import RestrictedError

        with self.assertRaises(RestrictedError):
            user.delete()

    def test_database_is_postgresql(self):
        from django.db import connection

        self.assertEqual(connection.vendor, "postgresql")

    def test_table_and_column_names_match_sdd(self):
        from django.db import connection

        with connection.cursor() as cursor:
            cols = {
                c.name
                for c in connection.introspection.get_table_description(cursor, "users")
            }
            log_cols = {
                c.name
                for c in connection.introspection.get_table_description(cursor, "activity_logs")
            }
        for expected in (
            "user_id", "email", "password_hash", "full_name",
            "business_name", "role", "is_active", "created_at",
        ):
            self.assertIn(expected, cols)
        for expected in ("log_id", "user_id", "action", "entity_name", "entity_id", "details", "created_at"):
            self.assertIn(expected, log_cols)
