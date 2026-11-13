from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from .models import User


class StyledFormMixin:
    """Adds the CSS class used by the templates to every widget."""

    def _style_fields(self):
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} form-control".strip()


class RegistrationForm(StyledFormMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 8 characters. Avoid common or all-numeric passwords.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["full_name", "business_name", "email"]
        labels = {"full_name": "Full name", "business_name": "Business name (optional)"}
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "business_name": forms.TextInput(attrs={"autocomplete": "organization"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].required = True
        self.fields["business_name"].required = False
        self._style_fields()

    def clean_full_name(self):
        name = self.cleaned_data["full_name"].strip()
        if not name:
            raise forms.ValidationError("Please enter your full name.")
        return name

    def clean_business_name(self):
        return (self.cleaned_data.get("business_name") or "").strip() or None

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", "The two password fields do not match.")
            else:
                try:
                    password_validation.validate_password(password2, self.instance)
                except forms.ValidationError as error:
                    self.add_error("password2", error)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.Role.OWNER  # public registration only creates business owners
        user.set_password(self.cleaned_data["password1"])  # hashed, never plain text
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(StyledFormMixin, AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        "invalid_login": "Invalid email or password. Please try again.",
        "inactive": "This account has been deactivated. Please contact an administrator.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "business_name", "email"]
        labels = {"full_name": "Full name", "business_name": "Business name"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].required = True
        self.fields["business_name"].required = False
        self._style_fields()

    def clean_full_name(self):
        name = self.cleaned_data["full_name"].strip()
        if not name:
            raise forms.ValidationError("Please enter your full name.")
        return name

    def clean_business_name(self):
        return (self.cleaned_data.get("business_name") or "").strip() or None

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        taken = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
