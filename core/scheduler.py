import schedule
import time
from datetime import datetime
from core.monitor import record_status
from visualization.charts import gen_all_charts
from utils.logger import log_msg
from config.settings import MON_INTV, CHART_INTV


def create_sched(app):

    def run_ctx(func):

        def wrap(*args, **kwargs):
            with app.app_context():
                return func(*args, **kwargs)

        return wrap

    @run_ctx
    def mon_task():

        log_msg("执行监控任务...")
        record_status()

    @run_ctx
    def chart_tk():

        log_msg("更新监控图表...")
        gen_all_charts()

    def run_sched():

        while True:
            with app.app_context():
                schedule.run_pending()
            time.sleep(1)

    return mon_task, chart_tk, run_sched


def start_sched(app):

    mon_task, chart_tk, run_sched = create_sched(app)

    schedule.every(MON_INTV).minutes.do(mon_task)  # 监控间隔
    schedule.every(CHART_INTV).hours.do(chart_tk)  # 图表更新间隔

    return run_sched
