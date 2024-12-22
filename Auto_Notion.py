import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量中的 Notion Token 和数据库 ID

load_dotenv()
NOTION_API_KEY = "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"
DATABASE_ID = "15fcfba7bede8086b2ddd119bd3cbbd7" # 每日时间轴数据库 ID

# 设置 Notion API 请求头
headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"  # 确保使用正确的版本
}


# 1. 获取 Notion 数据库中的所有任务
def get_tasks():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=headers)
    if response.status_code != 200:
        print("获取任务失败:", response.text)
        return []
    return response.json().get("results", [])


# 2. 更新任务的状态
def update_task_status(page_id, new_status):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "状态": {
                "status": {
                    "name": "进行中"  # 确保和 Notion 数据库状态一致
                }
            }
        }
    }
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"成功更新任务状态为: {new_status}")
    else:
        print("更新任务失败:", response.text)


# 3. 判断当前日期与甘特时间周期的关系
def process_tasks():
    tasks = get_tasks()
    today = datetime.now().date()

    for task in tasks:
        properties = task["properties"]
        page_id = task["id"]

        # 获取甘特时间周期的开始和结束日期
        gantt_period = properties.get("甘特周期", {}).get("date", {})
        start_date = gantt_period.get("start")
        end_date = gantt_period.get("end")

        if not start_date or not end_date:
            print("任务无有效的甘特时间周期，跳过...")
            continue

        start_date = datetime.fromisoformat(start_date).date()
        end_date = datetime.fromisoformat(end_date).date()

        # 获取当前任务的状态
        current_status = properties.get("状态", {}).get("select", {}).get("name")

        # 判断日期范围并更新状态
        if start_date <= today <= end_date:
            if current_status != "进行中":
                print(f"任务 {task['id']} 处于进行中，正在更新状态...")
                update_task_status(page_id, "进行中")
        elif today > end_date:
            if current_status != "完成":
                print(f"任务 {task['id']} 已完成，正在更新状态...")
                update_task_status(page_id, "完成")
        else:
            print(f"任务 {task['id']} 未开始或无需更新状态。")


# 4. 主函数
def main():
    process_tasks()


if __name__ == "__main__":
    main()
