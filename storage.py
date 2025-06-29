import json
from pytz import timezone
from datetime import datetime, timedelta

TASK_FILE = "tasks.json"

def get_tasks():
    try:
        with open(TASK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def update_task(index, task):
    tasks = get_tasks()
    tasks[index] = task
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def build_html(task_list):
    tz = timezone("Europe/Istanbul")
    today = datetime.now(tz).date()
    up5 = today + timedelta(days=5)
    # Son günü geçenler
    expired = []
    # Önümüzdeki 5 gün
    upcoming = []
    # Tüm görevler
    all_tasks = []
    for t in task_list:
        dt = tz.localize(datetime.strptime(t["deadline"], "%Y-%m-%dT%H:%M"))
        all_tasks.append(f"<li><b>{t['title']}</b>: {t['desc']} ({dt.strftime('%d.%m.%Y %H:%M')})</li>")
        if dt.date() < today:
            expired.append(f"<li><b>{t['title']}</b>: {t['desc']} ({dt.strftime('%d.%m.%Y %H:%M')})</li>")
        elif today <= dt.date() <= up5:
            upcoming.append(f"<li><b>{t['title']}</b>: {t['desc']} ({dt.strftime('%d.%m.%Y %H:%M')})</li>")
    html = """
    <h2>Önümüzdeki 5 gün içinde son günü olan görevler:</h2><ul>{}</ul>
    <h2>Son günü geçenler:</h2><ul>{}</ul>
    <h2>Tüm görevler:</h2><ul>{}</ul>
    """.format(''.join(upcoming), ''.join(expired), ''.join(all_tasks))
    return html
