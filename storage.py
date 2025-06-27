import json

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
