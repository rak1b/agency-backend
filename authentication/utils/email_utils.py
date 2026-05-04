import logging
import threading

from decouple import config
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from utils.email_send_utils import send_agencio_mail

from ..ms_email_utils import send_email as mail_send

logger = logging.getLogger(__name__)


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
    Send student file registration / portal credentials using Django SMTP (``send_agencio_mail``)
    and HTML templates under ``templates/email/agencio/``.

    Returns:
        tuple[bool, str]: (email_sent_successfully, provider_response_message)
    """
    normalized_recipient_email = (recipient_email or "").strip()
    if not normalized_recipient_email:
        return False, "Student email is missing."

    display_name = (student_name or "Student").strip() or "Student"
    display_file_id = (student_file_id or student_login_id or "").strip() or "—"
    email_subject = "Your student file has been created — Agencio"

    context = {
        "student_name": display_name,
        "student_file_id": display_file_id,
        "agency_name": (agency_name or "").strip() or None,
        "include_credentials": bool(include_credentials and temporary_password),
        "student_login_id": (student_login_id or "").strip(),
        "temporary_password": (temporary_password or "").strip(),
    }

    try:
        html_message = render_to_string("email/agencio/student_file_created.html", context)
        send_agencio_mail(
            subject=email_subject,
            message="",
            recipient_list=[normalized_recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as error:
        logger.exception("send_student_portal_credentials_email failed for %s", normalized_recipient_email)
        return False, str(error)

    return True, "sent_via_smtp"
