#!/usr/bin/env python
import os
import sys

def main():
    DJANGO_ENV = os.environ.get("DJANGO_ENV", "dev").lower()
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        f"project_core.settings.{DJANGO_ENV}"
    )

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc

    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
