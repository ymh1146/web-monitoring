import json
import plotly
import plotly.graph_objects as go
from datetime import datetime, timedelta
from jinja2 import Template, Environment, FileSystemLoader
import os
from config.settings import CHART_PERIODS, CHART_COLORS
from core.database import get_status_data
from utils.logger import log_msg
from config.website_manager import load_sites, norm_url


def gen_chart_data(url, period_hrs):

    df = get_status_data(period_hrs, url)

    if df.empty:
        cur_status = "未知"
        status_clr = CHART_COLORS["no_data"]
    else:
        latest_status = df.iloc[-1]["status"]
        is_cur_ok = latest_status == "OK"
        cur_status = "正常" if is_cur_ok else "异常"
        status_clr = CHART_COLORS["normal"] if is_cur_ok else CHART_COLORS["err"]

    disp_url = norm_url(url)

    vals = []
    clrs = []
    lbls = []
    txt = []
    txt_pos = []

    for hr in range(period_hrs):
        if period_hrs == 24:

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            hr_start = today + timedelta(hours=hr)
            hr_end = hr_start + timedelta(hours=1)
        else:

            hr_start = datetime.now() - timedelta(hours=period_hrs - hr - 1)
            hr_end = hr_start + timedelta(hours=1)

        hr_data = df[(df["ttmp"] >= hr_start) & (df["ttmp"] < hr_end)]

        if period_hrs <= 24:
            time_lbl = f'{hr_start.strftime("%H:00")}-{hr_end.strftime("%H:00")}'
        else:
            time_lbl = f'{hr_start.strftime("%m-%d %H:00")}-{hr_end.strftime("%H:00")}'

        if hr_start > datetime.now():
            clr = CHART_COLORS["no_data"]
            lbl = "无数据"
            hover_txt = f"{time_lbl} 无数据"
        elif not hr_data.empty:

            err_recs = hr_data[hr_data["status"] != "OK"]
            has_err = not err_recs.empty
            clr = CHART_COLORS["err"] if has_err else CHART_COLORS["normal"]

            if has_err:

                err_periods = []
                err_start = None
                last_err_time = None

                for _, err in err_recs.iterrows():
                    err_time = err["ttmp"]
                    if err_start is None:
                        err_start = err_time
                    elif (err_time - last_err_time).total_seconds() > 300:
                        err_periods.append(
                            f"{err_start.strftime('%H:%M')}-{last_err_time.strftime('%H:%M')}"
                        )
                        err_start = err_time
                    last_err_time = err_time

                if err_start is not None:
                    if last_err_time == err_recs.iloc[-1]["ttmp"]:

                        if not is_cur_ok:
                            last_err_time = datetime.now()
                    err_periods.append(
                        f"{err_start.strftime('%H:%M')}-{last_err_time.strftime('%H:%M')}"
                    )

                lbl = time_lbl + "<br>"
                for period in err_periods:
                    lbl += f"异常时段：{period}<br>"
                lbl = lbl.rstrip("<br>")
            else:
                lbl = time_lbl + "<br>正常"
            hover_txt = lbl
        else:
            clr = CHART_COLORS["no_data"]
            lbl = "无数据"
            hover_txt = f"{time_lbl} 无数据"

        vals.append(1)
        clrs.append(clr)
        lbls.append(hover_txt)

        if period_hrs == 24:  # 24小时
            txt.append(f"{hr:02d}")
            txt_pos.append("outside")
        elif period_hrs == 168:  # 7天
            if hr == 0 or (hr_start.hour == 0):
                txt.append(f"{hr_start.strftime('%m-%d')}")
                txt_pos.append("outside")
            else:
                txt.append("")
                txt_pos.append("none")
        elif period_hrs == 720:  # 30天
            days_from_start = hr // 24
            if hr == 0 or (days_from_start % 2 == 0 and hr_start.hour == 0):
                txt.append(f"{hr_start.strftime('%m-%d')}")
                txt_pos.append("outside")
            else:
                txt.append("")
                txt_pos.append("none")

    chart_data = {
        "data": go.Pie(
            values=vals,
            labels=lbls,
            hole=0.7,
            marker_colors=clrs,
            textinfo="text",
            text=txt,
            textposition=txt_pos,
            hoverinfo="label",
            hovertemplate="%{label}<extra></extra>",
            showlegend=False,
            direction="clockwise",
            sort=False,
            rotation=0,
            domain={"x": [0, 1], "y": [0, 1]},
            textfont=dict(size=12, color="var(--text-primary)"),
            title=dict(
                text=f"{disp_url}<br>当前状态: {cur_status}",
                font=dict(size=16, color=status_clr),
                position="middle center",
            ),
        ),
        "status": cur_status,
        "status_color": status_clr,
        "url": url,
    }

    return chart_data


def gen_all_charts():

    env = Environment(loader=FileSystemLoader("visualization/templates"))

    def mock_url(endpoint, **kwargs):
        if endpoint == "settings":
            return "/settings"
        elif endpoint == "status":
            return "/status"
        elif endpoint == "update_charts":
            return "/update_charts"
        return "/"

    env.globals["url_for"] = mock_url
    tpl = env.get_template("chart.html")

    sites = load_sites()

    periods = {f"{p}h": p for p in CHART_PERIODS}

    all_data = {}
    for period_name, hrs in periods.items():
        data = []
        layout = []
        charts_data = []

        if sites:
            for site in sites:
                chart_data = gen_chart_data(site, hrs)
                if chart_data:
                    data.append(chart_data["data"])
                    layout.append(
                        {
                            "showlegend": False,
                            "template": "plotly_white",
                            "paper_bgcolor": "rgba(0,0,0,0)",
                            "plot_bgcolor": "rgba(0,0,0,0)",
                            "margin": dict(t=50, b=30, l=30, r=30),
                            "height": None,
                        }
                    )
                    charts_data.append(
                        {
                            "status": chart_data["status"],
                            "status_color": chart_data["status_color"],
                            "url": chart_data["url"],
                        }
                    )

        all_data[period_name] = {
            "data": data,
            "layout": layout,
            "charts_data": charts_data,
        }

    plotly_encoder = plotly.utils.PlotlyJSONEncoder

    # 渲染模板，24h、168h、720h的图表数据
    html = tpl.render(
        data_24h=json.dumps(all_data["24h"]["data"], cls=plotly_encoder),
        layout_24h=json.dumps(all_data["24h"]["layout"], cls=plotly_encoder),
        charts_data_24h=json.dumps(all_data["24h"]["charts_data"], cls=plotly_encoder),
        data_168h=json.dumps(all_data["168h"]["data"], cls=plotly_encoder),
        layout_168h=json.dumps(all_data["168h"]["layout"], cls=plotly_encoder),
        charts_data_168h=json.dumps(
            all_data["168h"]["charts_data"], cls=plotly_encoder
        ),
        data_720h=json.dumps(all_data["720h"]["data"], cls=plotly_encoder),
        layout_720h=json.dumps(all_data["720h"]["layout"], cls=plotly_encoder),
        charts_data_720h=json.dumps(
            all_data["720h"]["charts_data"], cls=plotly_encoder
        ),
    )

    os.makedirs("static", exist_ok=True)
    with open(os.path.join("static", "status.html"), "w", encoding="utf-8") as f:
        f.write(html)
