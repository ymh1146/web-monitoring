from flask import Flask
from routes import init_routes
from core.scheduler import start_sch
import threading
import signal
import os
from utils.logger import log


def handle_exit(signum, frame):
    log("正在停止监控服务...")
    os._exit(0)


app = Flask(__name__)
init_routes(app)

if __name__ == "__main__":

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    sched_thd = threading.Thread(target=start_sch)
    sched_thd.daemon = True
    sched_thd.start()

    app.run(host="0.0.0.0", port=5000, debug=False)
