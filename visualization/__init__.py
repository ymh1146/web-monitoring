from visualization.chart_data import gen_chart
from visualization.chart_renderer import render
from core.database import get_st
from utils.logger import log


def gen_charts():
    sites = get_st()
    if not sites:
        return

    log("开始生成监控图表...")
    render(sites)
    log("监控图表生成完成")


__all__ = ["gen_charts"]
