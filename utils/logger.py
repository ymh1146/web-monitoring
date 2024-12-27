from datetime import datetime


def log_msg(msg):

    cur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{cur_time}] {msg}")
