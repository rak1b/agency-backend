import threading

from decouple import config
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from ..ms_email_utils import send_email as mail_send


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
):
    """
    Send initial student portal credentials using Microsoft Graph helper.

    Returns:
        tuple[bool, str]: (email_sent_successfully, provider_response_message)
    """
    normalized_recipient_email = (recipient_email or "").strip()
    if not normalized_recipient_email:
        return False, "Student email is missing."

    safe_student_name = escape(student_name or "Student")
    safe_student_login_id = escape(student_login_id or "")
    safe_temporary_password = escape(temporary_password or "")
    email_subject = "Student Portal Login Credentials"
    email_body = f"""
    <p>Hello {safe_student_name},</p>
    <p>Your student portal account has been created.</p>
    <p><strong>Student ID:</strong> {safe_student_login_id}</p>
    <p><strong>Temporary Password:</strong> {safe_temporary_password}</p>
    <p>Please keep these credentials secure.</p>
    """
    try:
        status_code, provider_response = mail_send(
            email_subject,
            email_body,
            normalized_recipient_email,
        )
    except Exception as error:
        return False, str(error)

    return 200 <= status_code < 300, provider_response
