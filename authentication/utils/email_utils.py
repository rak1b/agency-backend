from __future__ import annotations

import logging
import threading

from django.conf import settings as django_settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from utils.email_send_utils import send_agencio_mail

from ..ms_email_utils import send_email as mail_send

logger = logging.getLogger(__name__)


class StudentPortalCredentialsEmailThread(threading.Thread):
    """
    Sends student welcome/credentials email off the request thread so student-file
    API saves return quickly; SMTP runs in a daemon thread.
    """

    def __init__(self, **send_kwargs: object) -> None:
        super().__init__(daemon=True)
        self._send_kwargs = send_kwargs

    def run(self) -> None:
        from django.db import close_old_connections

        close_old_connections()
        try:
            _send_student_portal_credentials_sync(**self._send_kwargs)
        except Exception:
            logger.exception("Background student portal email failed")
        finally:
            close_old_connections()


class EmailThread(threading.Thread):
    def __init__(self, msg):
        self.msg = msg
        threading.Thread.__init__(self)

    def run(self):
        self.msg.send()


def send_email(subject, to, data, template="email/auth/supervisor_pin_change.html"):
    # template="email/auth/index.html"
    html_content = render_to_string(template, {'data': data})
    text_content = strip_tags(html_content)
    from_email = 'mdradwanhossain21@gmail.com'
    # print(html_content)
    mail_send(subject,html_content,from_email)
    # msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    # msg.attach_alternative(html_content, "text/html")
    # EmailThread(msg).start()


def send_ambassador_approved_email(email, data):
    send_email(_("Your Account is Registered"), email, data, "email/auth/ambassador_approved.html")


def send_forget_password_email(email, data):
    # send_email(_("Forgot Password?"), email, data, "email/auth/forget_password.html")
    send_email("Forgot Password?", "mdradwanhossain21@gmail.com", "mis", "email/auth/forget_password.html")
    send_email(subject="Forgot Password?",to="mdradwanhossain21@gmail.com",data="Account has been created",template="email/auth/forget_password.html")


def send_account_verify_email(email, data):
    send_email(_("Please Verify Your Account"), email, data, "email/auth/verify_your_account.html")


def send_account_deactivation_email(email, data):
    send_email(_("Your Account has been deactivated"), email, data, "email/auth/account_deactivated.html")


def send_pending_approval_email(email, data):
    send_email(_("Pending for Admin Approval"), email, data, "email/auth/pending_approval.html")


def send_university_approved_email(email, data):
    send_email(_("Your Account is approved"), email, data, "email/auth/university_approved.html")


def _send_student_portal_credentials_sync(
    *,
    normalized_recipient_email: str,
    display_name: str,
    display_file_id: str,
    email_subject: str,
    portal_login_url: str | None,
    agency_name: str | None,
    include_credentials: bool,
    student_login_id: str,
    temporary_password: str,
    branding_logo_url: str | None,
) -> None:
    """Render template and send via SMTP (runs on main or worker thread)."""
    context = {
        "student_name": display_name,
        "student_file_id": display_file_id,
        "agency_name": agency_name,
        "include_credentials": include_credentials,
        "student_login_id": student_login_id,
        "temporary_password": temporary_password,
        "portal_login_url": portal_login_url,
        "branding_logo_url": branding_logo_url,
    }
    html_message = render_to_string("email/agencio/student_file_created.html", context)
    send_agencio_mail(
        subject=email_subject,
        message="",
        recipient_list=[normalized_recipient_email],
        html_message=html_message,
        fail_silently=False,
    )


def send_student_portal_credentials_email(
    recipient_email,
    student_login_id,
    temporary_password,
    student_name=None,
    *,
    student_file_id=None,
    agency_name=None,
    include_credentials=True,
):
    """
    Queue student file registration / portal credentials email on a background thread
    (Django SMTP + templates under ``templates/email/agencio/``). The HTTP handler returns
    immediately; delivery status is not reflected in the API (check logs on failure).

    Returns:
        tuple[bool, str]: (queued_ok, message) — ``True, "queued"`` when the worker thread was started.
    """
    normalized_recipient_email = (recipient_email or "").strip()
    if not normalized_recipient_email:
        return False, "Student email is missing."

    display_name = (student_name or "Student").strip() or "Student"
    display_file_id = (student_file_id or student_login_id or "").strip() or "—"
    email_subject = "Your student file has been created — Agencio"

    portal_login_raw = (getattr(django_settings, "AGENCIO_PORTAL_LOGIN_URL", "") or "").strip()
    logo_raw = (getattr(django_settings, "AGENCIO_EMAIL_LOGO_URL", "") or "").strip()

    agency_clean = (agency_name or "").strip() or None
    inc_cred = bool(include_credentials and temporary_password)

    StudentPortalCredentialsEmailThread(
        normalized_recipient_email=normalized_recipient_email,
        display_name=display_name,
        display_file_id=display_file_id,
        email_subject=email_subject,
        portal_login_url=portal_login_raw or None,
        agency_name=agency_clean,
        include_credentials=inc_cred,
        student_login_id=(student_login_id or "").strip(),
        temporary_password=(temporary_password or "").strip(),
        branding_logo_url=logo_raw or None,
    ).start()

    return True, "queued"
