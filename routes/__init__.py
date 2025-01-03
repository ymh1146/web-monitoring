import os
from core.database import init_db
from routes.auth import auth_bp
from routes.monitor import mon_bp
from routes.settings import set_bp
from routes.push import push_bp


def init_routes(app):

    app.static_folder = "static"
    app.template_folder = os.path.join("visualization", "templates")

    app.secret_key = os.urandom(24)

    app.register_blueprint(auth_bp)  # 认证路由
    app.register_blueprint(mon_bp)  # 监控路由
    app.register_blueprint(set_bp)  # 设置路由
    app.register_blueprint(push_bp)  # 推送路由

    init_db()
