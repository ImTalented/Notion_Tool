import requests
from datetime import datetime, timedelta

NOTION_API_KEY = "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"  # 替换成你的 Notion API Token
SOURCE_DATABASE_ID = "15fcfba7bede8086b2ddd119bd3cbbd7"  # 每日时间轴数据库 ID
TARGET_DATABASE_ID = "15fcfba7bede802aa85cecd688f60ad2"  # 单日规划数据库 ID

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}


def fetch_in_progress_tasks():
    """
    从每日时间轴数据库中获取 '状态' 为 '进行中' 的任务和时间段。
    """
    url = f"https://api.notion.com/v1/databases/{SOURCE_DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "状态",
            "status": {
                "equals": "进行中"
            }
        }
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        raise Exception(f"获取任务失败: {response.json()}")

    results = response.json()["results"]
    tasks = []
    for result in results:
        task_name = result["properties"]["任务"]["title"][0]["plain_text"]
        time_slots = result["properties"]["多选"]["multi_select"]
        time_slots = [slot["name"] for slot in time_slots]  # 提取时间段
        tasks.append({"id": result["id"], "name": task_name, "time_slots": time_slots})
    return tasks


def merge_time_slots(time_slots):
    """
    合并连续的时间段。
    """
    if not time_slots:
        return []

    # 排序时间段
    time_slots.sort(key=lambda x: datetime.strptime(x.split('-')[0], "%H:%M"))

    merged_slots = []
    current_start, current_end = time_slots[0].split('-')
    for slot in time_slots[1:]:
        start, end = slot.split('-')
        if current_end == start:  # 时间段连续
            current_end = end
        else:
            merged_slots.append(f"{current_start}-{current_end}")
            current_start, current_end = start, end
    merged_slots.append(f"{current_start}-{current_end}")
    return merged_slots


def add_task_to_daily_plan(task_name, date, start_time, end_time):
    """
    向单日规划数据库添加新任务。
    """
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": TARGET_DATABASE_ID},
        "properties": {
            "任务": {"title": [{"text": {"content": task_name}}]},
            "日期": {
                "date": {
                    "start": f"{date}T{start_time}:00.000+08:00",
                    "end": f"{date}T{end_time}:00.000+08:00"
                }
            }
        }
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print(f"任务 {task_name} 添加失败: {response.json()}")
    else:
        print(f"任务 {task_name} 插入成功，时间段：{date}T{start_time} - {date}T{end_time}")


def main():
    print("正在获取每日时间轴数据库中的任务...")
    tasks = fetch_in_progress_tasks()

    today = datetime.now().date()
    occupied_slots = set()  # 记录已占用的时间段，避免冲突
    conflict_tasks = []

    for task in tasks:
        task_name = task["name"]
        time_slots = merge_time_slots(task["time_slots"])

        for slot in time_slots:
            start, end = slot.split('-')
            start_time = datetime.strptime(start, "%H:%M").strftime("%H:%M")
            end_time = datetime.strptime(end, "%H:%M").strftime("%H:%M")

            # 检查时间冲突
            time_key = f"{start_time}-{end_time}"
            if time_key in occupied_slots:
                conflict_tasks.append((task_name, time_key))
                continue

            # 向数据库添加任务
            add_task_to_daily_plan(task_name, today, start_time, end_time)
            occupied_slots.add(time_key)

    print("所有任务已处理。")
    if conflict_tasks:
        print("以下任务因时间冲突未被插入：")
        for task_name, time_key in conflict_tasks:
            print(f"任务: {task_name}, 时间段: {time_key}")


if __name__ == "__main__":
    main()

