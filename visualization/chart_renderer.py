import os
import json
import plotly
from jinja2 import Template
from visualization.chart_data import gen_chart
from utils.logger import log
from config.settings import VERSION


def mock_url(endpoint, **kwargs):

    if endpoint == "static":
        filename = kwargs.get("filename", "")
        return f"/static/{filename}"
    elif endpoint == "settings.set_page":
        return "/settings"
    elif endpoint == "monitor.status":
        return "/status"
    elif endpoint == "charts.update_charts":
        return "/update_charts"
    return "/"


def render(sites):

    tpl_file = os.path.join("visualization", "templates", "chart.html")
    with open(tpl_file, "r", encoding="utf-8") as f:
        tpl = Template(f.read())

    tpl.globals["url_for"] = mock_url

    # 生成24小时数据
    data_24 = []
    layout_24 = []
    chart_24 = []
    for site in sites:
        chart_data = gen_chart(site, 24)
        data_24.append(chart_data["data"])
        layout_24.append(chart_data["layout"])
        chart_24.append(chart_data)

    # 生成7天数据
    data_168 = []
    layout_168 = []
    chart_168 = []
    for site in sites:
        chart_data = gen_chart(site, 168)
        data_168.append(chart_data["data"])
        layout_168.append(chart_data["layout"])
        chart_168.append(chart_data)

    # 生成30天数据
    data_720 = []
    layout_720 = []
    chart_720 = []
    for site in sites:
        chart_data = gen_chart(site, 720)
        data_720.append(chart_data["data"])
        layout_720.append(chart_data["layout"])
        chart_720.append(chart_data)

    plt_enc = plotly.utils.PlotlyJSONEncoder

    # 渲染模板
    html = tpl.render(
        data_24h=json.dumps(data_24, cls=plt_enc),
        layout_24h=json.dumps(layout_24, cls=plt_enc),
        charts_data_24h=json.dumps(chart_24, cls=plt_enc),
        data_168h=json.dumps(data_168, cls=plt_enc),
        layout_168h=json.dumps(layout_168, cls=plt_enc),
        charts_data_168h=json.dumps(chart_168, cls=plt_enc),
        data_720h=json.dumps(data_720, cls=plt_enc),
        layout_720h=json.dumps(layout_720, cls=plt_enc),
        charts_data_720h=json.dumps(chart_720, cls=plt_enc),
        version=VERSION,
    )

    # 生成status.html文件
    out_file = os.path.join("static", "status.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)


__all__ = ["render"]
