import os
import time
import threading
from core.monitor import rec_all_st
from core.push import check_domain_expire
from visualization import gen_charts
from utils.logger import log
from config.settings import MON_INTV
from flask import current_app

# 任务锁
_tsk_lock = threading.Lock()


def with_log(func):
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log(f"执行任务出错: {str(e)}")
            return None

    return wrap


@with_log
def mon_tsk():
    with _tsk_lock:
        rec_all_st()
        check_domain_expire()
        gen_charts()


def sched_loop():
    while True:
        try:
            mon_tsk()
            time.sleep(MON_INTV * 60)
        except Exception as e:
            log(f"调度器运行出错: {str(e)}")
            time.sleep(60)


def start_sch():

    log("监控服务已启动，开始第一次检测...")
    mon_tsk()

    sched_thd = threading.Thread(target=sched_loop)
    sched_thd.daemon = True
    sched_thd.start()
