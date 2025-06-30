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

    # ekler
for path in attachments or []:
    try:
        with open(path, "rb") as f:
            data = f.read()
        filename = Path(path).name

        # MIMEApplication, .docx gibi ikili ekler için doğru sınıf
        part = MIMEApplication(
            data,
            _subtype="vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
         # Hem filename hem filename* ile gönder
        part.add_header(
            "Content-Disposition",
            f"attachment; filename=\"{filename}\"; filename*=utf-8''{encoded_filename}"
        )        
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
            # Kategoriye göre renkli rozet için stil belirle
            category = task.get('category', '-').capitalize()
            category_colors = {
                'Sigorta':   '#4fc3f7',
                'Hukuk':     '#81c784',
                'Ceza':      '#ffb74d',
                'İcra':      '#e57373',
                'Diğer':     '#ba68c8',
                '-':         '#b0bec5'
            }
            badge_color = category_colors.get(category, '#b0bec5')
            category_badge = (f'<span style="display:inline-block;padding:2px 14px;border-radius:14px;'
                              f'background:{badge_color};color:#222;font-weight:600;font-size:14px;letter-spacing:0.5px;">'
                              f'{category}</span>')
            html = f'''
            <div style="background:#f6f8fa;padding:0;margin:0;font-family:Segoe UI,Arial,sans-serif;">
              <div style="max-width:520px;margin:30px auto 0 auto;background:#fff;border-radius:12px;box-shadow:0 2px 12px #0002;padding:24px 18px 12px 18px;">
                <h2 style="color:#23272f;font-size:1.1rem;margin:0 0 10px 0;">{header}: <span style="color:#4fc3f7;">{task['title']}</span></h2>
                <div style="margin-bottom:10px;">{category_badge}</div>
                <table style="width:100%;border-collapse:collapse;margin-bottom:14px;">
                  <tr style="background:#e3eafc;"><td style="padding:8px 6px;font-weight:600;width:120px;">Açıklama</td><td style="padding:8px 6px;">{task['desc']}</td></tr>
                  <tr style="background:#f3f7fa;"><td style="padding:8px 6px;font-weight:600;">Kategori</td><td style="padding:8px 6px;">{category}</td></tr>
                  <tr style="background:#e3eafc;"><td style="padding:8px 6px;font-weight:600;">Son Tarih</td><td style="padding:8px 6px;">{task['deadline'].replace('T',' ')}</td></tr>
                </table>
                <div style="margin-bottom:8px;text-align:center;">
                  <img src="https://img.icons8.com/fluency/96/task-completed.png" width="64" height="64" alt="Görev Görseli" style="margin-bottom:8px;">
                </div>
                <div style="margin-bottom:8px;">{build_html(get_tasks())}</div>
                <div style="border-top:1px solid #e0e0e0;margin-top:12px;padding-top:8px;font-size:0.93rem;color:#888;text-align:center;">
                  <span style="font-weight:600;color:#4fc3f7;">Hatırlatıcı Sistemi</span> | <span style="color:#888;">Tüm hakları saklıdır.</span>
                </div>
              </div>
            </div>
            '''
            send_email("Görev Hatırlatma", html)   # eski kullanım değişmedi

        time.sleep(60)


# ---------------------------------------------------------------------------
# Başlatıcı
# ---------------------------------------------------------------------------
def start_checker():
    threading.Thread(target=checker_loop, daemon=True).start()
