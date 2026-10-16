"""Sending the sign-in code email, over any SMTP service (Gmail, Brevo, Resend, ...).

Set ALGOLENS_SMTP_HOST, ALGOLENS_SMTP_PORT (587, STARTTLS; or 465, TLS), ALGOLENS_SMTP_USER,
ALGOLENS_MAIL_FROM and SMTP_PASSWORD. Without them, email sign-in is off, unless
ALGOLENS_EMAIL_DEV_LOG=true, which writes codes to the API's log instead of sending them:
for trying it out on your own machine only.
"""

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

from algolens.config import Settings

log = logging.getLogger("algolens.mail")


class MailError(RuntimeError):
    pass


def _password(s: Settings) -> str:
    """Gmail shows app passwords in groups ("abcd efgh ijkl mnop"); they never contain spaces."""
    pw = os.environ.get("SMTP_PASSWORD", "")
    return pw.replace(" ", "") if s.smtp_host.endswith("gmail.com") else pw


def sends_mail(s: Settings) -> bool:
    """Real email is set up (rather than only the dev log)."""
    return bool(s.smtp_host and s.mail_from and os.environ.get("SMTP_PASSWORD"))


def configured(s: Settings) -> bool:
    return bool(s.smtp_host and s.mail_from and os.environ.get("SMTP_PASSWORD")) or s.email_dev_log


def code_message(to: str, code: str, sender: str, minutes: int) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"{code} is your AlgoLens sign-in code"
    msg["From"] = f"AlgoLens <{sender}>"
    msg["To"] = to
    msg.set_content(
        f"Your AlgoLens sign-in code is {code}\n\n"
        f"Type it on the sign-in page. It works once and expires in {minutes} minutes.\n\n"
        "If you didn't ask to sign in, ignore this email: nobody can sign in without the code."
    )
    msg.add_alternative(
        f"""<div style="font-family:system-ui,sans-serif;max-width:420px;color:#1f1c17">
<p>Your AlgoLens sign-in code is</p>
<p style="font-size:32px;font-weight:700;letter-spacing:6px;margin:8px 0 16px">{code}</p>
<p>Type it on the sign-in page. It works once and expires in {minutes} minutes.</p>
<p style="color:#5c564c;font-size:13px">If you didn't ask to sign in, ignore this email:
nobody can sign in without the code.</p></div>""",
        subtype="html",
    )
    return msg


def send_code(s: Settings, to: str, code: str, minutes: int) -> None:
    if not (s.smtp_host and s.mail_from and os.environ.get("SMTP_PASSWORD")):
        if s.email_dev_log:
            log.warning("DEV ONLY (ALGOLENS_EMAIL_DEV_LOG): sign-in code for %s is %s", to, code)
            return
        raise MailError("email isn't set up")
    msg = code_message(to, code, s.mail_from, minutes)
    context = ssl.create_default_context()
    try:
        if s.smtp_port == 465:
            with smtplib.SMTP_SSL(s.smtp_host, 465, context=context, timeout=20) as smtp:
                smtp.login(s.smtp_user or s.mail_from, _password(s))
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as smtp:
                smtp.starttls(context=context)
                smtp.login(s.smtp_user or s.mail_from, _password(s))
                smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        log.warning("couldn't send a sign-in code: %s", type(exc).__name__)
        raise MailError("couldn't send the email") from exc
