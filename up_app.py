import os
import sqlite3
import shutil
from datetime import datetime
from werkzeug.security import generate_password_hash


DB_VER = "1.4"
DB_PATH = "data/mon.db"
BAK_PATH = "data"
LOCK_F = os.path.join(BAK_PATH, "upgrade.lock")


def chk_lock():

    if os.path.exists(LOCK_F):
        lock_t = os.path.getmtime(LOCK_F)
        if datetime.now().timestamp() - lock_t < 3600:
            return False
        os.remove(LOCK_F)
    return True


def create_lock():

    try:
        with open(LOCK_F, "w") as f:
            f.write(str(datetime.now().timestamp()))
        return True
    except:
        return False


def rm_lock():

    try:
        if os.path.exists(LOCK_F):
            os.remove(LOCK_F)
    except:
        pass


def get_db_ver():

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='system_config'"
        )
        if not c.fetchone():
            conn.close()
            return "1.0"

        c.execute("SELECT value FROM system_config WHERE key = 'db_version'")
        ver = c.fetchone()
        conn.close()

        return ver[0] if ver else "1.0"
    except Exception as e:
        print(f"获取数据库版本出错: {str(e)}")
        return None


def bak_db():

    try:
        bak_f = os.path.join(
            BAK_PATH, f"mon.db.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        shutil.copy2(DB_PATH, bak_f)
        print(f"已备份数据库到: {bak_f}")
        return True
    except Exception as e:
        print(f"备份数据库失败: {str(e)}")
        return False


def up_from_1_0():

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS new_sites (
                url TEXT PRIMARY KEY,
                note TEXT,
                req_hdrs TEXT,
                req_body TEXT,
                sort_order INTEGER DEFAULT 0,
                expire_date TEXT
            )
        """
        )

        c.execute("SELECT DISTINCT url FROM site_status")
        urls = c.fetchall()
        for i, (url,) in enumerate(urls, 1):
            c.execute(
                "INSERT INTO new_sites (url, note, req_hdrs, req_body, sort_order) VALUES (?, ?, ?, ?, ?)",
                (url, "", "{}", "", i),
            )

        c.execute("DROP TABLE IF EXISTS sites")
        c.execute("ALTER TABLE new_sites RENAME TO sites")

        c.execute(
            "INSERT INTO system_config (key, value) VALUES (?, ?)",
            ("db_version", DB_VER),
        )
        c.execute(
            "INSERT INTO system_config (key, value) VALUES (?, ?)",
            ("pwd_h", generate_password_hash("admin")),
        )
        c.execute(
            "INSERT INTO system_config (key, value) VALUES (?, ?)", ("req_pwd", "1")
        )

        conn.commit()
        conn.close()
        print("从1.0版本升级到1.4版本成功")
        return True

    except Exception as e:
        print(f"从1.0版本升级失败: {str(e)}")
        return False


def up_from_1_3():

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        try:
            c.execute("ALTER TABLE sites ADD COLUMN expire_date TEXT")
        except sqlite3.OperationalError:
            pass

        c.execute(
            "UPDATE system_config SET value = ? WHERE key = 'db_version'", (DB_VER,)
        )

        conn.commit()
        conn.close()
        print("从1.3版本升级到1.4版本成功")
        return True

    except Exception as e:
        print(f"从1.3版本升级失败: {str(e)}")
        return False


def up_db():

    if not os.path.exists(DB_PATH):
        print("未找到数据库文件")
        return False

    if not chk_lock():
        print("升级程序已被锁定")
        return False

    if not create_lock():
        print("无法创建升级锁，请检查文件权限")
        return False

    try:

        cur_ver = get_db_ver()
        if not cur_ver:
            print("无法确定数据库版本")
            rm_lock()
            return False

        print(f"当前数据库版本: {cur_ver}")

        if not bak_db():
            rm_lock()
            return False

        if cur_ver == "1.0":
            result = up_from_1_0()
        elif cur_ver == "1.3":
            result = up_from_1_3()
        elif cur_ver == "1.4":
            print("数据库已经是最新版本")
            result = True
        else:
            print(f"不支持的数据库版本: {cur_ver}")
            result = False

        if not result:
            rm_lock()

        return result

    except Exception as e:
        print(f"升级过程出现错误: {str(e)}")
        rm_lock()
        return False


if __name__ == "__main__":
    print("开始执行升级程序...")
    if up_db():
        print("\n升级成功完成！")
    else:
        print("\n升级失败！请检查错误信息")
