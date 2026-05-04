"""
Send a test message via configured SMTP and print non-secret settings for debugging.

Example::

    python manage.py testmail
    python manage.py testmail other@example.com
"""

from smtplib import SMTPAuthenticationError, SMTPDataError

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Print SMTP-related settings (no password), then send one test email."

    def add_arguments(self, parser):
        parser.add_argument(
            "to",
            nargs="?",
            default="rakib.devsstream@gmail.com",
            help="Recipient email address.",
        )
        parser.add_argument(
            "--smtp-probe",
            action="store_true",
            help="Only test SMTP AUTH against several Zoho hosts/ports (no email sent).",
        )

    def handle(self, *args, **options):
        from django.conf import settings as dj_settings

        from utils.email_send_utils import (
            format_smtp_probe_results,
            probe_smtp_logins,
            send_agencio_mail,
            smtp_settings_debug_text,
        )

        if options["smtp_probe"]:
            self.stdout.write(self.style.NOTICE("--- SMTP config (from Django settings / .env) ---"))
            self.stdout.write(smtp_settings_debug_text())
            self.stdout.write("")
            self.stdout.write(self.style.NOTICE("--- Probing SMTP LOGIN (Zoho endpoints) ---"))
            results = probe_smtp_logins(
                dj_settings.EMAIL_HOST_USER,
                dj_settings.EMAIL_HOST_PASSWORD,
            )
            self.stdout.write(format_smtp_probe_results(results))
            self.stdout.flush()
            return

        recipient = (options["to"] or "").strip()
        self.stdout.write(self.style.NOTICE("--- SMTP config (from Django settings / .env) ---"))
        self.stdout.write(smtp_settings_debug_text())
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("--- Attempting send ---"))
        self.stdout.write(f"subject=Test Email")
        self.stdout.write(f"to={recipient!r}")
        self.stdout.write("")
        self.stdout.flush()

        try:
            sent = send_agencio_mail(
                subject="Test Email",
                message="This is a test email from manage.py testmail.",
                recipient_list=[recipient],
            )
            self.stdout.write(self.style.SUCCESS(f"OK — mail backend reported sent count: {sent}"))
        except SMTPAuthenticationError as exc:
            self.stderr.write(self.style.ERROR(f"SMTPAuthenticationError: {exc}"))
            self.stderr.write(
                "535 usually means: wrong password, or username must be the full mailbox email "
                "(e.g. info@agencio.xyz), or use a Zoho *application-specific* password, not the "
                "account login password. Port 587 + TLS must match Zoho SMTP docs."
            )
            raise CommandError("SMTP authentication failed; see messages above.") from exc
        except SMTPDataError as exc:
            self.stderr.write(self.style.ERROR(f"SMTPDataError: {exc}"))
            self.stderr.write(
                "553 often means: the From address is not allowed for this SMTP login — "
                "set DEFAULT_FROM_EMAIL to the same mailbox as EMAIL_HOST_USER (or a verified "
                "Zoho alias), e.g. \"Agencio <info@yourdomain.com>\". Confirm SMTP host matches "
                "your Zoho product (personal vs org: smtp.zoho.com vs smtppro.zoho.com)."
            )
            raise CommandError("SMTP rejected the message (relay / sender policy); see messages above.") from exc
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Send failed: {exc!r}"))
            raise
