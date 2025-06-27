# reminder.py  (tam içerik)

from pytz import timezone
from datetime import datetime, timedelta
import time, threading, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from storage import get_tasks, update_task

# ——— Mail ayarları ———————————————————————————————
SMTP_USER   = "evtvdisci@gmail.com"
SMTP_PASS   = "juhmtaxepfxvcbqr"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 465
TO_EMAILS   = ["fatihdisci@outlook.com"]   # hatırlatma için varsayılan alıcı(lar)
# —————————————————————————————————————————————————————


# ---------------------------------------------------------------------------
# Geliştirilmiş send_email()
#  • Eski hatırlatma kullanımını değiştirmez: send_email(subject, html_body)
#  • Dilekçe vb. ekli mail için:          send_email(subject, html_body,
#                                          attachments=[path], to_override=[addr])
# ---------------------------------------------------------------------------
def send_email(subject, html_body, *, attachments=None, to_override=None):
    """
    Varsayılan (eski) çağrı:
        send_email("Görev Hatırlatma", html_body)

    Yeni çağrı (dilekçe):
        send_email("Dilekçeniz", html_body,
                   attachments=["tmp/basvuru.docx"],
                   to_override=["kullanici@mail.com"])
    """
    recipients = to_override or TO_EMAILS

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = SMTP_USER
    msg["To"]      = ", ".join(recipients)

    # HTML içerik
    msg_alt = MIMEMultipart("alternative")
    msg_alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(msg_alt)

    # Ekler
    for path in attachments or []:
        try:
            with open(path, "rb") as f:
                data = f.read()
            part = MIMEBase("application", "octet-stream")
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition",
                            f'attachment; filename=\"{Path(path).name}\"')
            msg.attach(part)
        except Exception as e:
            print(f"Eklenti eklenemedi ({path}):", e)

    # Gönderim
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    except Exception as e:
        print("Mail gönderilemedi:", e)


# ---------------------------------------------------------------------------
# HTML özet bloğu – değişmedi
# ---------------------------------------------------------------------------
def build_html(task_list):
    tz    = timezone("Europe/Istanbul")
    today = datetime.now(tz).date()
    up5   = today + timedelta(days=5)
    html  = "<h2>Önümüzdeki 5 gün içinde son günü olan görevler:</h2><ul>"
    for t in task_list:
        dt = tz.localize(datetime.strptime(t["deadline"], "%Y-%m-%dT%H:%M"))
        if today <= dt.date() <= up5:
            html += (f"<li><b>{t['title']}</b>: {t['desc']} "
                     f"({dt.strftime('%d.%m.%Y %H:%M')})</li>")
    html += "</ul>"
    return html


# ---------------------------------------------------------------------------
# 60-saniyelik döngü – değişmedi
# ---------------------------------------------------------------------------
def checker_loop():
    tz = timezone("Europe/Istanbul")
    while True:
        now   = datetime.now(tz).replace(second=0, microsecond=0)
        tasks = get_tasks()
        to_mail = []

        for i, t in enumerate(tasks):
            dt       = tz.localize(datetime.strptime(t["deadline"], "%Y-%m-%dT%H:%M"))
            diff_sec = (dt - now).total_seconds()

            # 1 gün önce (±60 sn)
            if 86340 <= diff_sec <= 86460 and not t.get("warned_1day"):
                t["warned_1day"] = True
                to_mail.append(("⏰ 1 Gün Kaldı", t))

            # tam vakit (±60 sn)
            if -60 <= diff_sec <= 60 and not t.get("warned_today"):
                t["warned_today"] = True
                to_mail.append(("⌛ Süre Doldu", t))

            if t.get("warned_today") or t.get("warned_1day"):
                update_task(i, t)

        for header, task in to_mail:
            html = (f"<h2>{header}: {task['title']}</h2>"
                    f"<p>{task['desc']}</p>"
                    f"<p>Son Tarih: {task['deadline'].replace('T',' ')}</p><hr>"
                    f"{build_html(get_tasks())}")
            send_email("Görev Hatırlatma", html)   # eski kullanım değişmedi

        time.sleep(60)


# ---------------------------------------------------------------------------
# Başlatıcı
# ---------------------------------------------------------------------------
def start_checker():
    threading.Thread(target=checker_loop, daemon=True).start()
