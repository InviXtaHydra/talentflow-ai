from html import escape

from app.core.config import get_settings
from app.integrations.email.sender import OutgoingEmail


def _wrap(title: str, paragraphs: list[str], button_label: str, url: str) -> str:
    app_name = escape(get_settings().app_name)
    body = "".join(f'<p style="margin:0 0 14px;line-height:1.55">{escape(p)}</p>' for p in paragraphs)
    return f"""<!doctype html><html><body style="margin:0;background:#f5f6f8;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#0f172a">
<div style="max-width:520px;margin:32px auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:32px">
<div style="font-weight:700;font-size:15px;color:#4338ca;margin-bottom:20px">{app_name}</div>
<h1 style="font-size:20px;margin:0 0 16px">{escape(title)}</h1>{body}
<a href="{escape(url)}" style="display:inline-block;background:#4338ca;color:#fff;text-decoration:none;padding:11px 18px;border-radius:8px;font-weight:600">{escape(button_label)}</a>
<p style="margin:24px 0 0;font-size:12px;color:#64748b">Werkt de knop niet? Kopieer deze link in je browser:<br>{escape(url)}</p>
</div></body></html>"""


def verification_email(to: str, name: str, token: str) -> OutgoingEmail:
    url = f"{get_settings().frontend_url}/verify-email?token={token}"
    lines = [f"Hallo {name},", "Bevestig je e-mailadres om je account volledig te activeren. De link is 48 uur geldig."]
    return OutgoingEmail(
        to=to,
        subject="Bevestig je e-mailadres",
        text="\n\n".join([*lines, url]),
        html=_wrap("Bevestig je e-mailadres", lines, "E-mailadres bevestigen", url),
    )


def password_reset_email(to: str, name: str, token: str) -> OutgoingEmail:
    url = f"{get_settings().frontend_url}/reset-password?token={token}"
    lines = [
        f"Hallo {name},",
        "Je vroeg een nieuw wachtwoord aan. Kies via de knop een nieuw wachtwoord; de link is 1 uur geldig.",
        "Heb je dit niet aangevraagd? Dan mag je deze e-mail negeren: je wachtwoord blijft ongewijzigd.",
    ]
    return OutgoingEmail(
        to=to,
        subject="Nieuw wachtwoord instellen",
        text="\n\n".join([*lines, url]),
        html=_wrap("Nieuw wachtwoord instellen", lines, "Wachtwoord instellen", url),
    )
