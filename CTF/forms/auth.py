from flask_babel import lazy_gettext as _l
from wtforms import EmailField, PasswordField, StringField
from wtforms.validators import InputRequired

from CTFd.forms import BaseForm
from CTFd.forms.fields import SubmitField
from CTFd.forms.users import (
    attach_custom_user_fields,
    attach_registration_code_field,
    attach_user_bracket_field,
    build_custom_user_fields,
    build_registration_code_field,
    build_user_bracket_field,
)
from CTFd.utils import get_config
from CTFd.utils.passwords import get_password_policy_min_length


def RegistrationForm(*args, **kwargs):
    password_min_length = get_password_policy_min_length(
        configured_min_length=int(get_config("password_min_length", default=0))
    )
    password_description = _l("Password used to log into your account")
    password_description += _l(
        f" (At least {password_min_length} characters, uppercase, lowercase, number, and special character)"
    )

    class _RegistrationForm(BaseForm):
        name = StringField(
            _l("User Name"),
            description="Your username on the site",
            validators=[InputRequired()],
            render_kw={"autofocus": True},
        )
        email = EmailField(
            _l("Email"),
            description="Never shown to the public",
            validators=[InputRequired()],
        )
        password = PasswordField(
            _l("Password"),
            description=password_description,
            validators=[InputRequired()],
        )
        submit = SubmitField(_l("Submit"))

        @property
        def extra(self):
            return (
                build_custom_user_fields(
                    self, include_entries=False, blacklisted_items=()
                )
                + build_registration_code_field(self)
                + build_user_bracket_field(self)
            )

    attach_custom_user_fields(_RegistrationForm)
    attach_registration_code_field(_RegistrationForm)
    attach_user_bracket_field(_RegistrationForm)

    return _RegistrationForm(*args, **kwargs)


class LoginForm(BaseForm):
    name = StringField(
        _l("User Name or Email"),
        validators=[InputRequired()],
        render_kw={"autofocus": True},
    )
    password = PasswordField(_l("Password"), validators=[InputRequired()])
    submit = SubmitField(_l("Submit"))


class ConfirmForm(BaseForm):
    submit = SubmitField(_l("Send Confirmation Email"))


class ResetPasswordRequestForm(BaseForm):
    email = EmailField(
        _l("Email"), validators=[InputRequired()], render_kw={"autofocus": True}
    )
    submit = SubmitField(_l("Submit"))


class ResetPasswordForm(BaseForm):
    password = PasswordField(
        _l("Password"),
        description=_l(
            "Use a strong password with uppercase, lowercase, number, and special character"
        ),
        validators=[InputRequired()],
        render_kw={"autofocus": True},
    )
    submit = SubmitField(_l("Submit"))
