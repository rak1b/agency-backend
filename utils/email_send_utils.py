"""
Django SMTP mail helpers for Agencio (Zoho or any configured ``EMAIL_*`` settings).

Use :func:`send_agencio_mail` for plain text and optional HTML. Credentials and
``DEFAULT_FROM_EMAIL`` come from environment / ``Config.settings`` — not from code.
"""

from __future__ import annotations

import logging
import smtplib
import socket
import ssl
from dataclasses import dataclass
from typing import Sequence

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def get_default_from_email() -> str:
    """Resolve sender: explicit ``DEFAULT_FROM_EMAIL``, else ``EMAIL_HOST_USER``."""
    explicit = getattr(settings, "DEFAULT_FROM_EMAIL", "") or ""
    if explicit.strip():
        return explicit.strip()
    user = getattr(settings, "EMAIL_HOST_USER", "") or ""
    return user.strip()


def _password_debug_hint() -> str:
    """Length-only hint so logs can confirm .env is loaded (never log the secret)."""
    raw = getattr(settings, "EMAIL_HOST_PASSWORD", None)
    if raw is None or raw == "":
        return "(empty — SMTP login will fail until EMAIL_HOST_PASSWORD is set)"
    return f"(loaded, {len(str(raw))} characters)"


def smtp_settings_debug_text() -> str:
    """
    Printable SMTP-related settings for troubleshooting (no passwords).

    Use from management commands or temporary debugging; remove from production paths.
    """
    lines = [
        f"EMAIL_BACKEND={getattr(settings, 'EMAIL_BACKEND', '')}",
        f"EMAIL_HOST={getattr(settings, 'EMAIL_HOST', '')}",
        f"EMAIL_PORT={getattr(settings, 'EMAIL_PORT', '')}",
        f"EMAIL_USE_TLS={getattr(settings, 'EMAIL_USE_TLS', '')}",
        f"EMAIL_USE_SSL={getattr(settings, 'EMAIL_USE_SSL', '')}",
        f"EMAIL_TIMEOUT={getattr(settings, 'EMAIL_TIMEOUT', 'not set')}",
        f"EMAIL_HOST_USER={getattr(settings, 'EMAIL_HOST_USER', '')}",
        f"EMAIL_HOST_PASSWORD {_password_debug_hint()}",
        f"DEFAULT_FROM_EMAIL={getattr(settings, 'DEFAULT_FROM_EMAIL', '')}",
        f"SERVER_EMAIL={getattr(settings, 'SERVER_EMAIL', '')}",
        f"resolved_from_for_send={get_default_from_email()!r}",
    ]
    return "\n".join(lines)


def send_agencio_mail(
    subject: str,
    message: str,
    recipient_list: Sequence[str],
    *,
    from_email: str | None = None,
    html_message: str | None = None,
    fail_silently: bool = False,
    reply_to: Sequence[str] | None = None,
) -> int:
    """
    Send one email using the active Django mail backend (SMTP when configured).

    Parameters
    ----------
    subject:
        Email subject line.
    message:
        Plain-text body. If ``html_message`` is set and ``message`` is empty,
        plain text is derived by stripping HTML tags from ``html_message``.
    recipient_list:
        To-addresses (each must be a valid mailbox string).
    from_email:
        Overrides ``DEFAULT_FROM_EMAIL`` / ``EMAIL_HOST_USER``. Use for branded
        ``From`` such as ``Agencio <info@agencio.xyz>``.
    html_message:
        Optional HTML body; sent as multipart/alternative alongside plain text.
    fail_silently:
        Passed through to Django mail APIs (swallow SMTP errors when True).
    reply_to:
        Optional ``Reply-To`` header list.

    Returns
    -------
    int
        Number of successfully queued/sent messages (same contract as ``send_mail``).

    Raises
    ------
    ValueError
        If no sender address can be resolved or ``recipient_list`` is empty.
    """
    recipients = [addr.strip() for addr in recipient_list if addr and str(addr).strip()]
    if not recipients:
        raise ValueError("recipient_list must contain at least one non-empty address.")

    sender = (from_email or "").strip() or get_default_from_email()
    if not sender:
        raise ValueError(
            "No From address: set DEFAULT_FROM_EMAIL or EMAIL_HOST_USER in settings/env, "
            "or pass from_email= explicitly."
        )

    plain = message.strip() if message else ""
    if html_message and not plain:
        plain = strip_tags(html_message).strip() or "(no plain-text body)"

    if html_message:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain,
            from_email=sender,
            to=list(recipients),
        )
        msg.attach_alternative(html_message, "text/html")
        if reply_to:
            msg.reply_to = list(reply_to)
        try:
            return msg.send(fail_silently=fail_silently)
        except Exception as exc:
            logger.error("send_agencio_mail: multipart send failed subject=%r: %s", subject, exc)
            raise

    try:
        return send_mail(
            subject,
            plain,
            sender,
            list(recipients),
            fail_silently=fail_silently,
        )
    except Exception as exc:
        logger.error("send_agencio_mail: plain send failed subject=%r: %s", subject, exc)
        raise


@dataclass(frozen=True)
class SmtpProbeResult:
    host: str
    port: int
    mode: str
    ok: bool
    detail: str


def probe_smtp_logins(
    user: str,
    password: str,
    *,
    timeout: int = 20,
) -> list[SmtpProbeResult]:
    """
    Try several Zoho regional / product SMTP endpoints with the same credentials.

    Use this when you get 535 on one host: copy a **green** row into ``.env`` as
    ``EMAIL_HOST`` / ``EMAIL_PORT`` and set ``EMAIL_USE_SSL`` / ``EMAIL_USE_TLS``
    to match (TLS + 587 vs SSL + 465).
    """
    targets: list[tuple[str, int, str]] = [
        ("smtp.zoho.com", 587, "starttls"),
        ("smtp.zoho.com", 465, "ssl"),
        ("smtppro.zoho.com", 587, "starttls"),
        ("smtppro.zoho.com", 465, "ssl"),
        ("smtp.zoho.in", 587, "starttls"),
        ("smtp.zoho.eu", 587, "starttls"),
    ]
    results: list[SmtpProbeResult] = []
    for host, port, mode in targets:
        server = None
        try:
            if mode == "ssl":
                server = smtplib.SMTP_SSL(host, port, timeout=timeout)
            else:
                server = smtplib.SMTP(host, port, timeout=timeout)
                server.ehlo()
                if mode == "starttls":
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
            server.login(user, password)
            server.quit()
            results.append(SmtpProbeResult(host, port, mode, True, "AUTH OK"))
        except (OSError, socket.timeout, smtplib.SMTPException) as exc:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    try:
                        server.close()
                    except Exception:
                        pass
            results.append(SmtpProbeResult(host, port, mode, False, str(exc)))
        except Exception as exc:
            results.append(SmtpProbeResult(host, port, mode, False, str(exc)))
    return results


def format_smtp_probe_results(results: Sequence[SmtpProbeResult]) -> str:
    lines = []
    for row in results:
        status = "OK " if row.ok else "FAIL"
        lines.append(f"{status}  {row.host}:{row.port}  ({row.mode})  {row.detail}")
    winners = [r for r in results if r.ok]
    if winners:
        w = winners[0]
        tls = w.mode == "starttls"
        ssl = w.mode == "ssl"
        lines.append("")
        lines.append(
            f"Suggested .env (first working endpoint): EMAIL_HOST={w.host}  EMAIL_PORT={w.port}  "
            f"EMAIL_USE_TLS={'True' if tls else 'False'}  EMAIL_USE_SSL={'True' if ssl else 'False'}"
        )
    else:
        lines.append("")
        lines.append(
            "All endpoints failed: Zoho is rejecting the username/password pair. "
            "Regenerate an **application-specific password** for mailbox matching EMAIL_HOST_USER, "
            "paste it into EMAIL_HOST_PASSWORD (no spaces), and confirm SMTP access for that account."
        )
    return "\n".join(lines)


def send_agencio_mail_zoho_test(recipient: str) -> int:
    """
    Convenience wrapper for a quick SMTP connectivity check (same as a manual ``send_mail`` test).

    Example .env::

        EMAIL_HOST=smtp.zoho.com
        EMAIL_PORT=587
        EMAIL_USE_TLS=True
        EMAIL_HOST_USER=info@agencio.xyz
        EMAIL_HOST_PASSWORD=<application-specific password>
        DEFAULT_FROM_EMAIL=Agencio <info@agencio.xyz>
    """
    body = "Zoho SMTP is working with Django (AgencioBackendAPP mail utils)."
    return send_agencio_mail(
        subject="Test Email from Agencio",
        message=body,
        recipient_list=[recipient],
        from_email=None,
    )
