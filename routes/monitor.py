from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    make_response,
    jsonify,
    flash,
    request,
)
from routes.auth import is_auth, login_req
from core.database import get_st_data, get_st
from core.monitor import rec_all_st, rec_st
from visualization import gen_charts
import os
from utils.logger import log
from config.settings import VERSION
import time

mon_bp = Blueprint("monitor", __name__)


@mon_bp.route("/")
@login_req(req_login=False)
def index():
    sites = get_st()
    if not sites:
        return render_template("chart.html", version=VERSION)

    charts = []
    for site in sites:
        charts.append(gen_chart(site, 24))

    return render_template(
        "chart.html",
        version=VERSION,
        data_24h=charts,
        layout_24h=charts,
        charts_data_24h=charts,
        data_168h=charts,
        layout_168h=charts,
        charts_data_168h=charts,
        data_720h=charts,
        layout_720h=charts,
        charts_data_720h=charts,
    )


@mon_bp.route("/status")
@login_req(req_login=False)
def st_page():
    # 检查status.html
    st_file = os.path.join("static", "status.html")
    if not os.path.exists(st_file):
        flash("未检测到状态页面，请先设置监控网站再，进行生成图表！")
        return redirect(url_for("settings.set_page"))

    with open(st_file, "r", encoding="utf-8") as f:
        return f.read()


@mon_bp.route("/check_status")
@login_req(req_login=False)
def chk_st():
    try:
        sites = get_st()
        if not sites:
            return jsonify({"success": False, "message": "请先添加监控网站"})

        rec_all_st()
        return jsonify({"success": True})

    except Exception as e:
        log(f"执行状态检查时出错: {str(e)}")
        return jsonify({"success": False, "message": str(e)})


@mon_bp.route("/update_charts", methods=["POST"])
@login_req(req_login=False)
def upd_charts():
    try:
        sites = get_st()
        if not sites:
            return jsonify({"code": 1, "msg": "请先添加监控网站"})

        for site in sites:
            try:
                rec_st(site)
            except Exception as e:
                log(f"检查网站 {site['url']} 状态时出错: {str(e)}")

        log("完成一次状态检查")

        time.sleep(2)
        gen_charts()
        return jsonify({"code": 0})

    except Exception as e:
        log(f"更新图表时出错: {str(e)}")
        return jsonify({"code": 1, "msg": str(e)})
