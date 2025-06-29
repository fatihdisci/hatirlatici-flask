import os, json, uuid
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
from dilekce_service import create_insurance_docx, buyuk_harf_tr

from reminder import send_email, build_html

app = Flask(__name__)
TASKS_FILE = "tasks.json"

app = Flask(__name__, static_folder='static')

# ——— Türkiye Saat Dilimi ————————————————————————————
TZ = timezone("Europe/Istanbul")

# ——— APScheduler ————————————————————————————————
scheduler = BackgroundScheduler(timezone=TZ)
scheduler.start()

# ——— Yardımcı fonksiyonlar ——————————————————————————
def get_tasks():
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)

# ——— Job planlayıcı ————————————————————————————————
def send_scheduled_email(task, header):
    subject = f"⚠️ {header}: {task['title']}"
    html = (
        f"<h2>{header}</h2>"
        f"<p><b>{task['title']}</b>: {task['desc']}</p>"
        f"<p><b>Kategori:</b> {task.get('category','-').capitalize()}</p>"
        f"<p>Son Tarih: {task['deadline'].replace('T', ' ')}</p><hr>"
        f"{build_html(get_tasks())}"
    )
    send_email(subject, html)

def schedule_task(task):
    """
    Göreve benzersiz job ID’leri ekler,
    varsa eski job’ları yaratmaz.
    """
    # 1) benzersiz ID üret
    base_id = task.get("uid") or str(uuid.uuid4())
    task["uid"]       = base_id
    task["job_1day"]  = f"{base_id}_1d"
    task["job_due"]   = f"{base_id}_due"

    # 2) zaman hesapla
    dt = TZ.localize(datetime.fromisoformat(task["deadline"]))
    run1 = dt - timedelta(days=1)
    now  = datetime.now(TZ)

    # 3) 1 gün önce job
    if run1 > now and not scheduler.get_job(task["job_1day"]):
        scheduler.add_job(
            func=lambda t=task: send_scheduled_email(t, "1 Gün Kaldı"),
            trigger="date",
            run_date=run1,
            id=task["job_1day"]
        )

    # 4) tam vakitte job
    if dt > now and not scheduler.get_job(task["job_due"]):
        scheduler.add_job(
            func=lambda t=task: send_scheduled_email(t, "Süre Doldu"),
            trigger="date",
            run_date=dt,
            id=task["job_due"]
        )

# ——— Flask Routes ————————————————————————————————
@app.route("/")
def index():
    selected = request.args.get("kategori")
    tasks = get_tasks()
    if selected == "expired":
        # Sadece günü geçenler
        from pytz import timezone
        from datetime import datetime
        tz = timezone("Europe/Istanbul")
        today = datetime.now(tz).date()
        tasks = [t for t in tasks if tz.localize(datetime.strptime(t["deadline"], "%Y-%m-%dT%H:%M")).date() < today]
    elif selected and selected != "hepsi":
        tasks = [t for t in tasks if t.get("category") == selected]
    return render_template("index.html", tasks=tasks, selected=selected)

@app.route("/add", methods=["POST"])
def add_task():
    title    = request.form["title"].strip()
    desc     = request.form["desc"].strip()
    deadline = request.form["deadline"]      # "YYYY-MM-DDTHH:MM"
    category = request.form["category"]

    new_task = {
        "title": title,
        "desc": desc,
        "deadline": deadline,
        "category": category,
        "warned_1day": False,
        "warned_today": False
    }

    tasks = get_tasks()
    tasks.append(new_task)
    schedule_task(new_task)      # job ID’leri ekler ve planlar
    save_tasks(tasks)            # ID’lerle birlikte kaydet

    # Anında bilgi maili
    send_email(
        "🆕 Yeni Görev Eklendi",
        f"<h2>Yeni Görev</h2><p><b>{title}</b>: {desc}</p>"
        f"<p><b>Kategori:</b> {category.capitalize()}</p>"
        f"<p>Son Tarih: {deadline.replace('T',' ')}</p><hr>{build_html(tasks)}"
    )
    return redirect("/")

@app.route("/delete/<int:index>", methods=["POST"])
def delete_task(index):
    tasks = get_tasks()
    if 0 <= index < len(tasks):
        deleted = tasks.pop(index)
        # Planlanmış job’ları iptal et
        for key in ("job_1day", "job_due"):
            jid = deleted.get(key)
            if jid and scheduler.get_job(jid):
                scheduler.remove_job(jid)
        save_tasks(tasks)

        # Silme maili
        send_email(
            f"🗑️ Görev Silindi: {deleted['title']}",
            f"<h2>Görev Silindi</h2><p><b>{deleted['title']}</b>: {deleted['desc']}</p>"
            f"<p>Son Tarih: {deleted['deadline'].replace('T',' ')}</p>"
        )
    return redirect("/")

@app.route('/dilekce-olustur', methods=['GET', 'POST'])
def dilekce_olustur():
    if request.method == 'POST':
        # Gerekli field’ları topla
        fields = ['Sigorta Şirketi','Ad Soyad','TC No','Kaza Tarihi',
                  'Müvekkil Plaka','Karşı Plaka','Araç Modeli','Değer Kaybı (₺)',
                  'Bakiye Hasar (₺)','Toplam (₺)','email']
        data = { fld: request.form[fld] for fld in fields }

        output_file = f"tmp/{data['Ad Soyad'].replace(' ', '_')}_basvuru.docx"
        create_insurance_docx(data, output_file)

        send_email(
            "📄 Dilekçeniz",
            "Merhaba,\n\nTalep ettiğiniz dilekçe ekte yer almaktadır.\n\nİyi günler.",
            attachments=[output_file],
            to_override=[data['email']]
        )

        return render_template('dilekce_formu.html', mesaj="✅ Dilekçeniz e-posta ile gönderildi.", temizle=True)

    return render_template('dilekce_formu.html')


# ——— Uygulama Start-up ————————————————————————————
if __name__ == "__main__":
    # Var olan görevleri planla (ID yoksa ekle)
    tasks = get_tasks()
    changed = False
    for t in tasks:
        if "job_1day" not in t or "job_due" not in t:
            schedule_task(t)
            changed = True
    if changed:
        save_tasks(tasks)

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
