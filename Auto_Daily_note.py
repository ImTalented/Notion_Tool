#
# # 配置
# NOTION_API_KEY = "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"
# SOURCE_DATABASE_ID = "162cfba7bede80a4b25ff38630c39967"
# TARGET_DATABASE_ID = "162cfba7bede80249775c3b43620519e"
# HEADERS = {
#     "Authorization": f"Bearer {NOTION_API_KEY}",
#     "Content-Type": "application/json",
#     "Notion-Version": "2022-06-28",
# }
import datetime
import pytz
from notion_client import Client
from datetime import datetime, timedelta

# 初始化 Notion 客户端
notion = Client(auth="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")
SOURCE_DATABASE_ID = "162cfba7bede80a4b25ff38630c39967"
TARGET_DATABASE_ID = "162cfba7bede80249775c3b43620519e"
today = datetime.now(pytz.timezone("Asia/Shanghai")).date()

def get_memo_data():
    """从 '备忘录数据' 数据库获取任务数据"""
    database_id = SOURCE_DATABASE_ID  # 备忘录数据数据库ID
    memo_data = []

    # 从数据库获取所有数据
    query = notion.databases.query(database_id=database_id)
    for result in query['results']:
        task_name = result['properties']['待完成事件']['title'][0]['text']['content']
        task_date = result['properties'].get('日期', {}).get('date', None)
        task_create_date = result['properties'].get('创建时间', {}).get('created_time', None)
        # 如果任务有日期，获取日期；如果没有日期，则为 None
        memo_data.append({
            '待完成事件': task_name,
            '日期': task_date,
            '创建时间': task_create_date
        })

    return memo_data


def get_existing_tasks():
    """获取数据库中已有的任务（根据任务名称和日期）  只获取月和日，没有时"""
    existing_tasks = {}
    query = notion.databases.query(database_id=TARGET_DATABASE_ID)
    for result in query['results']:
        task_name = result['properties']['待完成事件']['title'][0]['text']['content']
        date = result['properties']['日期']['date']['start'][:10]  # 提取日期部分
        existing_tasks[(task_name, date)] = True
    return existing_tasks




def get_latest_time_slot():
    """获取数据库中时间段最新的结束时间，返回下一个可用的开始时间"""
    query = notion.databases.query(database_id=TARGET_DATABASE_ID)
    latest_time = datetime.datetime(2024, 1, 1, 2, 0, tzinfo=pytz.timezone("Asia/Shanghai"))  # 默认最早时间2:00，带时区
    for result in query['results']:
        if '日期' in result['properties'] and result['properties']['日期']['date']:
            end_time = result['properties']['日期']['date']['end']
            end_time = datetime.datetime.fromisoformat(end_time)  # 转换为 datetime 对象
            end_time = end_time.astimezone(pytz.timezone("Asia/Shanghai"))  # 确保 end_time 是带时区的
            if end_time > latest_time:
                latest_time = end_time
    return latest_time


def format_time(time_obj):
    """格式化时间为 'HH:MM'"""
    return time_obj.strftime('%H:%M')


def fill_task_with_date(task_name, task_date):
    """填充有日期的任务"""


    # 提取 task_date 中的 start 和 end 日期时间信息
    start_datetime = task_date.get('start')  # 例如 '2024-12-20T20:00:00.000+08:00'
    end_datetime = task_date.get('end')  # 例如 '2024-12-20T21:00:00.000+08:00'

    # 确保 start_datetime 和 end_datetime 都存在，并且格式正确
    if not start_datetime or not end_datetime:
        raise ValueError("task_date 字典缺少 start 或 end 字段")

    payload = {
        "parent": {"database_id": TARGET_DATABASE_ID},
        "properties": {
            "待完成事件": {"title": [{"text": {"content": task_name}}]},
            "日期": {
                "date": {
                    "start": start_datetime,  # 直接使用 task_date 中的 start
                    "end": end_datetime  # 直接使用 task_date 中的 end
                }
            }
        }
    }
    print(f"任务 '{task_name}' 已填充时间段 {start_datetime} - {end_datetime}")
    # 向 Notion API 发送请求
    notion.pages.create(**payload)


def get_existing_time_slots(database_id):
    """从数据库获取已存在的时间段"""
    existing_slots = []
    results = notion.databases.query(database_id=database_id)  # 查询目标数据库

    # 获取所有已填充的时间段
    for page in results.get('results', []):
        task_date = page['properties'].get('日期', {}).get('date', {})
        start_time = task_date.get('start')
        end_time = task_date.get('end')

        if start_time and end_time:
            existing_slots.append((start_time, end_time))

    return existing_slots


def get_next_available_time(existing_slots, start_time="02:00", end_time="06:00"):
    """计算下一个可用的时间段"""
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = datetime.strptime(end_time, "%H:%M")
    slot_duration = timedelta(minutes=20)

    # 将现有时间段转换为 datetime 格式进行排序
    occupied_times = []
    for start, end in existing_slots:
        start_dt_occupied = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S.%f+08:00")
        end_dt_occupied = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S.%f+08:00")
        occupied_times.append((start_dt_occupied, end_dt_occupied))

    # 按照结束时间从早到晚排序
    occupied_times.sort(key=lambda x: x[1])

    # 查找空闲时间段
    current_time = start_dt
    for occupied_start, occupied_end in occupied_times:
        if occupied_start > current_time:
            # 找到第一个空闲时间段
            return current_time.strftime("%H:%M"), (current_time + slot_duration).strftime("%H:%M")
        current_time = occupied_end

    # 如果没有占用，返回最早的时间段
    if current_time < end_dt:
        return current_time.strftime("%H:%M"), (current_time + slot_duration).strftime("%H:%M")

    return None  # 如果 2:00-6:00 时间段已完全占用


def get_existing_tasks2():
    """获取数据库中已有的任务（根据任务名称和日期）"""
    existing_tasks = []
    query = notion.databases.query(database_id=TARGET_DATABASE_ID)
    for result in query['results']:
        task_name = result['properties']['待完成事件']['title'][0]['text']['content']
        date_str = result['properties']['日期']['date']['end'] # 提取日期部分
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        # 将 datetime 对象格式化为所需的字符串格式
        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        # print("date_str",formatted_date)
        existing_tasks.append((task_name, formatted_date))
    return existing_tasks

def get_latest_time():
    """获取数据库中当天2:00 AM - 6:00 AM之间的最新时间"""
    # 获取当天日期
    today = datetime.now(pytz.timezone("Asia/Shanghai")).date()
    latest_time = None

    # 获取数据库中所有任务的时间段
    existing_tasks = get_existing_tasks2()  # 获取所有任务
    for task in existing_tasks:
        task_name, task_date = task  # 拆分任务名称和日期
        # print("task_date,today", task_date,today)
        # 如果任务日期是今天
        task_date = datetime.strptime(task_date, "%Y-%m-%d %H:%M:%S")
        if task_date.date() == today:
            # 假设没有时间的任务默认设置为 2:00 AM
            task_start_time = task_date
            # 只选择当天2:00 AM - 6:00 AM区间内的任务
            if datetime.strptime('02:00', "%H:%M").time() <= task_start_time.time() <= datetime.strptime('06:00',"%H:%M").time():
                # print("latest_time，task_start_time",latest_time,task_start_time)

                # 选择时间较晚的任务
                if latest_time is None or task_start_time > latest_time:
                    latest_time = task_start_time

    return latest_time
def fill_task_without_date(task_name):
    """填充没有日期的任务"""
    # 获取数据库中最新的时间段
    latest_time = get_latest_time()
    # 若没有任务，则从 2:00 开始
    if latest_time is None:
        start_time = datetime.strptime("02:00", "%H:%M")
    else:
        start_time = latest_time
    end_time = start_time + timedelta(minutes=30)  # 每个任务30分钟

    # 格式化时间为 Notion API 所需的格式
    start_time_str = start_time.strftime("%H:%M")
    end_time_str = end_time.strftime("%H:%M")

    payload = {
        "parent": {"database_id": TARGET_DATABASE_ID},
        "properties": {
            "待完成事件": {"title": [{"text": {"content": task_name}}]},
            "日期": {
                "date": {
                    "start": f"{today}T{start_time_str}:00.000+08:00",
                    "end": f"{today}T{end_time_str}:00.000+08:00"
                }
            }
        }
    }
    notion.pages.create(**payload)
    print(f"任务 '{task_name}' 已填充时间段 {start_time} - {end_time}")

def date_form(date_temp):
    task_date_day = datetime.strptime(date_temp, "%Y-%m-%dT%H:%M:%S.%f%z")
    return task_date_day.date()

def main():
    existing_tasks = get_existing_tasks()

    # 获取 "备忘录数据" 中的任务
    memo_data = get_memo_data()  # 假设你有一个函数从备忘录数据库获取任务数据

    for task in memo_data:
        task_name = task['待完成事件']
        task_date = task.get('日期', None)
        task_create_date = task.get('创建时间', None)

        # 如果有日期，填充到数据库
        if task_date:
            task_date_day = date_form(task_date["start"])
            # 检查是否已经填充过
            if task_date_day != today:
                print(task_name,"跳过")
            else:
                if (task_name, str(today)) not in existing_tasks:
                    fill_task_with_date(task_name, task_date)
                    existing_tasks[(task_name, str(today))] = True  # 添加到已填充任务中
        else:
            task_date_day = date_form(task_create_date)
            # 没有日期，分配一个时间段
            if task_date_day != today:
                print(task_name,"跳过")
            else:
                if (task_name, str(today)) not in existing_tasks:
                    fill_task_without_date(task_name)
                    existing_tasks[(task_name, str(today))] = True  # 添加到已填充任务中


if __name__ == "__main__":
    main()
