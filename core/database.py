import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from config.settings import DB_PATH, DATA_KEEP_DAYS
from utils.logger import log_msg


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        """CREATE TABLE IF NOT EXISTS db_ver
                 (ver INTEGER PRIMARY KEY)"""
    )

    c.execute("SELECT ver FROM db_ver")
    res = c.fetchone()
    cur_ver = res[0] if res else 0

    if cur_ver < 1:
        c.execute(
            """CREATE TABLE IF NOT EXISTS site_status
                     (ttmp DATETIME NOT NULL,
                      url TEXT NOT NULL,
                      status TEXT NOT NULL,
                      CONSTRAINT pk_site_status PRIMARY KEY (ttmp, url))"""
        )

        c.execute(
            """CREATE INDEX IF NOT EXISTS idx_site_status_ttmp 
                     ON site_status(ttmp)"""
        )
        c.execute(
            """CREATE INDEX IF NOT EXISTS idx_site_status_url 
                     ON site_status(url)"""
        )

        if cur_ver == 0:
            c.execute("INSERT INTO db_ver (ver) VALUES (1)")
        else:
            c.execute("UPDATE db_ver SET ver = 1")

    conn.commit()
    conn.close()
    log_msg("数据库初始化完成")


def save_status(url, status):
    """保存网站状态
    
    Args:
        url: 网站URL
        status: 状态字符串
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        ttmp = datetime.now()
        conn.execute(
            "INSERT INTO site_status (ttmp, url, status) VALUES (?, ?, ?)",
            (ttmp, url, status),
        )
        conn.commit()
    except Exception as e:
        log_msg(f"保存状态数据时出错: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


def get_status_data(hrs, url=None):
    """获取状态数据
    
    Args:
        hrs: 时间跨度（小时）
        url: 网站URL，如果为None则获取所有网站数据
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hrs)

        if url:
            # 如果传入的是网站配置字典，提取URL
            if isinstance(url, dict):
                url = url["url"]
                
            df = pd.read_sql_query(
                """
                SELECT ttmp, url, status
                FROM site_status
                WHERE ttmp >= ? AND url = ?
                ORDER BY ttmp
            """,
                conn,
                params=(start_time, url),
            )
        else:
            df = pd.read_sql_query(
                """
                SELECT ttmp, url, status
                FROM site_status
                WHERE ttmp >= ?
                ORDER BY ttmp
            """,
                conn,
                params=(start_time,),
            )

        df["ttmp"] = pd.to_datetime(df["ttmp"], format="ISO8601")
        return df
    except Exception as e:
        log_msg(f"获取状态数据时出错: {str(e)}")
        return pd.DataFrame(columns=["ttmp", "url", "status"])
    finally:
        conn.close()


def cleanup_old_data():
    """清理旧数据"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        threshold = datetime.now() - timedelta(days=DATA_KEEP_DAYS)
        with conn:
            res = conn.execute("DELETE FROM site_status WHERE ttmp < ?", (threshold,))
            del_cnt = res.rowcount
            log_msg(f"已清理{DATA_KEEP_DAYS}天前的历史数据，共删除{del_cnt}条记录")
    except Exception as e:
        log_msg(f"清理历史数据时出错: {str(e)}")
    finally:
        if conn:
            conn.close()


def clear_all_data():
    """清空所有数据"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        with conn:
            conn.execute("DELETE FROM site_status")
            log_msg("已清空所有监控数据")
    except Exception as e:
        log_msg(f"清空数据时出错: {str(e)}")
    finally:
        if conn:
            conn.close()
