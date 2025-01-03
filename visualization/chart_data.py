import json
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config.settings import CLR_CODE, ST_TEXT, ST_CODE
from core.database import get_st_data
from core.utils import norm_url

# chart系列函数用于生成图表数据，没必要别乱改，会显示异常


def get_st_clr(st_code):

    if st_code == 200:
        return CLR_CODE["N"]
    elif st_code == -1:
        return CLR_CODE["E"]
    else:
        return CLR_CODE["G"]


def get_st_txt(st_code):

    if st_code == 200:
        return ST_TEXT["N"]
    elif st_code == -1:
        return ST_TEXT["E"]
    else:
        return ST_TEXT["X"]


def gen_chart(site, prd_hrs):

    url = site["url"]
    disp_url = norm_url(url)
    url_data = get_st_data(prd_hrs).get(url, {})

    expire_days = ""
    expire_color = CLR_CODE["N"]  
    if site.get("expire_date"):
        try:
            expire_date = datetime.strptime(site["expire_date"], "%Y-%m-%d")
            days_left = (expire_date - datetime.now()).days
            if days_left <= 30:
                expire_color = CLR_CODE["E"]  
            expire_days = f"{days_left}天"
        except:
            pass

    if url_data and url_data.get("st_codes"):
        cur_st = url_data["st_codes"][-1]
        st_clr = get_st_clr(cur_st)
        st_dtl = url_data["err_msgs"][-1] if url_data["err_msgs"][-1] else get_st_txt(cur_st)
        is_ok = cur_st == 200
    else:
        cur_st = -1
        st_clr = CLR_CODE["G"]
        st_dtl = ST_TEXT["X"]
        is_ok = False

    title_text = []
    if disp_url:
        title_text.append(f"<b>{disp_url}</b>")
    if st_dtl:
        title_text.append(f"{st_dtl}")
    title_text.append(f"当前状态: {cur_st}")

    fav_path = url_data.get("fav_path")

    if not url_data or not url_data.get("st_codes"):
        st_clr = CLR_CODE["G"]
        st_dtl = ST_TEXT["X"]
        is_ok = False
        cur_st = ST_TEXT["X"]
    else:
        last_st = url_data["st_codes"][-1]
        last_err = url_data["err_msgs"][-1]
        is_ok = last_st == 200
        st_clr = CLR_CODE["N"] if is_ok else CLR_CODE["E"]
        st_dtl = last_err if not is_ok else ""
        cur_st = ST_TEXT["N"] if is_ok else ST_TEXT["E"]

    # 设置布局
    if fav_path:
        layout = {
            "showlegend": False,
            "template": "plotly_white",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "margin": dict(t=80, b=30, l=30, r=30),
            "height": None,
            "images": [
                {
                    "source": f"/static/{fav_path}",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.7,
                    "sizex": 0.15,
                    "sizey": 0.15,
                    "xanchor": "center",
                    "yanchor": "middle",
                    "sizing": "contain",
                }
            ],
            "annotations": [
                {
                    "text": "<br>".join(title_text),
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 16, "color": st_clr},
                    "xanchor": "center",
                    "yanchor": "middle",
                }
            ] + ([{
                "text": f'<span style="color: {expire_color}">剩余{expire_days}</span>',
                "x": 0.5,
                "y": 0.3,
                "showarrow": False,
                "font": {"size": 14},
                "xanchor": "center",
                "yanchor": "middle",
            }] if expire_days else [])
        }
    else:
        layout = {
            "showlegend": False,
            "template": "plotly_white",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "margin": dict(t=80, b=30, l=30, r=30),
            "height": None,
            "annotations": [
                {
                    "text": "<br>".join(title_text),
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 16, "color": st_clr},
                    "xanchor": "center",
                    "yanchor": "middle",
                }
            ] + ([{
                "text": f'<span style="color: {expire_color}">剩余{expire_days}</span>',
                "x": 0.5,
                "y": 0.3,
                "showarrow": False,
                "font": {"size": 14},
                "xanchor": "center",
                "yanchor": "middle",
            }] if expire_days else [])
        }

    vals = []
    clrs = []
    lbls = []
    txt = []
    txt_pos = []

    if prd_hrs == 720:
        for day in range(30):
            day_start = datetime.now() - timedelta(days=30 - day - 1)
            day_start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            day_ts = []
            day_st = []
            day_err = []

            if url_data and url_data.get("timestamps"):
                for i, ts_str in enumerate(url_data["timestamps"]):
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    if day_start <= ts < day_end:
                        day_ts.append(ts)
                        day_st.append(url_data["st_codes"][i])
                        day_err.append(url_data["err_msgs"][i])

            time_lbl = day_start.strftime("%m-%d")

            if day_start > datetime.now():
                clr = CLR_CODE["G"]
                lbl = ST_TEXT["X"]
                hover_txt = f"{time_lbl} {ST_TEXT['X']}"
            elif day_ts:
                has_err = any(status != 200 for status in day_st)
                clr = CLR_CODE["E"] if has_err else CLR_CODE["N"]
                if has_err:
                    err_prd = []
                    err_dtl = []
                    err_start = None
                    last_err_t = None
                    last_err_st = None

                    for ts, st_code, err_msg in zip(day_ts, day_st, day_err):
                        if st_code != 200:
                            err_status = err_msg if err_msg else f"HTTP {st_code}"
                            if (
                                err_start is None
                                or (ts - last_err_t).total_seconds() > 300
                                or err_status != last_err_st
                            ):
                                if err_start is not None:
                                    err_prd.append(
                                        f"{err_start.strftime('%H:%M')}-{last_err_t.strftime('%H:%M')}"
                                    )
                                    err_dtl.append(last_err_st)
                                err_start = ts
                            last_err_t = ts
                            last_err_st = err_status

                    if err_start is not None:
                        err_prd.append(
                            f"{err_start.strftime('%H:%M')}-{last_err_t.strftime('%H:%M')}"
                        )
                        err_dtl.append(last_err_st)

                    lbl = f"{time_lbl} 异常\n" + "\n".join(
                        f"{period}: {detail}"
                        for period, detail in zip(err_prd, err_dtl)
                    )
                    hover_txt = lbl
                else:
                    lbl = f"{time_lbl} 正常"
                    hover_txt = lbl
            else:
                clr = CLR_CODE["G"]
                lbl = f"{time_lbl} {ST_TEXT['X']}"
                hover_txt = lbl

            vals.append(1)
            clrs.append(clr)
            lbls.append(lbl)
            txt.append(time_lbl)
            txt_pos.append("outside")
    else:
        total_hrs = prd_hrs

        if prd_hrs <= 24:
            # 24小时视图从当天0点开始,如果图表显示不正常，优先检查服务器本地时区，程序默认服务时间绘制图表
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            for hour in range(24):
                hr_start = today + timedelta(hours=hour)
                hr_end = hr_start + timedelta(hours=1)

                hr_ts = []
                hr_st = []
                hr_err = []

                if url_data and url_data.get("timestamps"):
                    for i, ts_str in enumerate(url_data["timestamps"]):
                        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        if hr_start <= ts < hr_end:
                            hr_ts.append(ts)
                            hr_st.append(url_data["st_codes"][i])
                            hr_err.append(url_data["err_msgs"][i])

                time_lbl = f"{hour:02d}"

                if hr_start >= tomorrow:
                    clr = CLR_CODE["G"]
                    lbl = ST_TEXT["X"]
                    hover_txt = f"{hr_start.strftime('%m-%d %H:00')} {ST_TEXT['X']}"
                elif hr_ts:
                    has_err = any(status != 200 for status in hr_st)
                    clr = CLR_CODE["E"] if has_err else CLR_CODE["N"]
                    if has_err:
                        err_prd = []
                        err_dtl = []
                        err_start = None
                        last_err_t = None
                        last_err_st = None

                        for ts, st_code, err_msg in zip(hr_ts, hr_st, hr_err):
                            if st_code != 200:
                                err_status = err_msg if err_msg else f"HTTP {st_code}"
                                if (
                                    err_start is None
                                    or (ts - last_err_t).total_seconds() > 300
                                    or err_status != last_err_st
                                ):
                                    if err_start is not None:
                                        err_prd.append(
                                            f"{err_start.strftime('%H:%M')}-{last_err_t.strftime('%H:%M')}"
                                        )
                                        err_dtl.append(last_err_st)
                                    err_start = ts
                                last_err_t = ts
                                last_err_st = err_status

                        if err_start is not None:
                            err_prd.append(
                                f"{err_start.strftime('%H:%M')}-{last_err_t.strftime('%H:%M')}"
                            )
                            err_dtl.append(last_err_st)

                        lbl = f"{hr_start.strftime('%m-%d %H:00')} 异常\n" + "\n".join(
                            f"{period}: {detail}"
                            for period, detail in zip(err_prd, err_dtl)
                        )
                        hover_txt = lbl
                    else:
                        lbl = f"{hr_start.strftime('%m-%d %H:00')} 正常"
                        hover_txt = lbl
                else:
                    clr = CLR_CODE["G"]
                    lbl = f"{hr_start.strftime('%m-%d %H:00')} {ST_TEXT['X']}"
                    hover_txt = lbl

                vals.append(1)
                clrs.append(clr)
                lbls.append(lbl)
                txt.append(time_lbl)
                txt_pos.append("outside")
        else:

            for hour in range(total_hrs):
                hr_start = datetime.now() - timedelta(hours=total_hrs - hour - 1)
                hr_start = hr_start.replace(minute=0, second=0, microsecond=0)
                hr_end = hr_start + timedelta(hours=1)

                hr_ts = []
                hr_st = []
                hr_err = []

                if url_data and url_data.get("timestamps"):
                    for i, ts_str in enumerate(url_data["timestamps"]):
                        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        if hr_start <= ts < hr_end:
                            hr_ts.append(ts)
                            hr_st.append(url_data["st_codes"][i])
                            hr_err.append(url_data["err_msgs"][i])

                if hr_start.hour == 12:
                    time_lbl = hr_start.strftime("%m-%d")
                else:
                    time_lbl = ""

                if hr_start > datetime.now():
                    clr = CLR_CODE["G"]
                    lbl = ST_TEXT["X"]
                    hover_txt = f"{hr_start.strftime('%m-%d %H:00')} {ST_TEXT['X']}"
                elif hr_ts:
                    has_err = any(status != 200 for status in hr_st)
                    clr = CLR_CODE["E"] if has_err else CLR_CODE["N"]
                    if has_err:
                        err_prd = []
                        err_dtl = []
                        err_start = None
                        last_err_t = None
                        last_err_st = None

                        for ts, st_code, err_msg in zip(hr_ts, hr_st, hr_err):
                            if st_code != 200:
                                err_status = err_msg if err_msg else f"HTTP {st_code}"
                                if (
                                    err_start is None
                                    or (ts - last_err_t).total_seconds() > 300
                                    or err_status != last_err_st
                                ):
                                    if err_start is not None:
                                        err_prd.append(
                                            f"{err_start.strftime('%H:%M')}-{last_err_t.strftime('%H:%M')}"
                                        )
                                        err_dtl.append(last_err_st)
                                    err_start = ts
                                last_err_t = ts
                                last_err_st = err_status

                        if err_start is not None:
                            err_prd.append(
                                f"{err_start.strftime('%H:%M')}-{last_err_t.strftime('%H:%M')}"
                            )
                            err_dtl.append(last_err_st)

                        lbl = f"{hr_start.strftime('%m-%d %H:00')} 异常\n" + "\n".join(
                            f"{period}: {detail}"
                            for period, detail in zip(err_prd, err_dtl)
                        )
                        hover_txt = lbl
                    else:
                        lbl = f"{hr_start.strftime('%m-%d %H:00')} 正常"
                        hover_txt = lbl
                else:
                    clr = CLR_CODE["G"]
                    lbl = f"{hr_start.strftime('%m-%d %H:00')} {ST_TEXT['X']}"
                    hover_txt = lbl

                vals.append(1)
                clrs.append(clr)
                lbls.append(lbl)
                txt.append(time_lbl)
                txt_pos.append("outside")

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
        ),
        "layout": layout,
        "url": url,
        "cur_st": cur_st,
        "st_clr": st_clr,
        "st_dtl": st_dtl,
        "is_ok": is_ok,
        "disp_url": disp_url,
    }

    return chart_data
