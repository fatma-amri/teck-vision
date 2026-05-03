def get_password_policy_min_length(configured_min_length=None):
    """Return the enforced minimum length for strong passwords."""
    baseline_min_length = 8

    if configured_min_length is None:
        from CTFd.utils import get_config

        configured_min_length = int(get_config("password_min_length", default=0))

    return max(int(configured_min_length or 0), baseline_min_length)


def validate_password_strength(password, configured_min_length=None):
    """Return a list of validation errors for a password policy."""
    password = password or ""
    errors = []

    if len(password) == 0:
        errors.append("Pick a longer password")
        return errors

    if len(password) > 128:
        errors.append("Pick a shorter password")
        return errors

    min_length = get_password_policy_min_length(
        configured_min_length=configured_min_length
    )
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters")

    if not any(char.isupper() for char in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(char.islower() for char in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(char.isdigit() for char in password):
        errors.append("Password must contain at least one number")

    if not any(not char.isalnum() for char in password):
        errors.append("Password must contain at least one special character")

    return errors
