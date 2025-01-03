import logging
import os
from datetime import datetime


if not os.path.exists("logs"):
    os.makedirs("logs")


log_f = os.path.join("logs", f'monitor_{datetime.now().strftime("%Y%m%d")}.log')


logger = logging.getLogger("monitor")
logger.setLevel(logging.INFO)


f_hdl = logging.FileHandler(log_f, encoding="utf-8")
f_hdl.setLevel(logging.INFO)


c_hdl = logging.StreamHandler()
c_hdl.setLevel(logging.INFO)


fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
f_hdl.setFormatter(fmt)
c_hdl.setFormatter(fmt)


logger.addHandler(f_hdl)
logger.addHandler(c_hdl)


def log(msg, log_lvl="INFO", save_f=False):

    level = getattr(logging, log_lvl.upper())

    if not save_f:

        logger.removeHandler(f_hdl)

    logger.log(level, msg)

    if not save_f:
        logger.addHandler(f_hdl)


def log_err(msg):

    log(msg, log_lvl="ERROR", save_f=True)


def log_mon(url, st_code, err_msg=None):

    if st_code != 200:
        message = f"监控异常 - {url} - 状态码: {st_code}"
        if err_msg:
            message += f" - 错误: {err_msg}"
        log(message, log_lvl="WARNING" if st_code != -1 else "ERROR", save_f=True)


def log_start():

    log("监控服务已启动，开始第一次检测...", save_f=True)


def log_chart_upd():

    log("开始生成监控图表...", save_f=True)


def log_chart_done():

    log("监控图表生成完成", save_f=True)
