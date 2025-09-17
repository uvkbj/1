from flask import Flask
from .db import get_db_connection

def create_app():
    app = Flask(__name__)
    app.config.from_object('config')  # ���������ļ�
    @app.template_filter('zip')
    def zip_filter(*iterables):
        return zip(*iterables)
    # ע����ͼ
    from .routes.auth import auth
    app.register_blueprint(auth)
    from .routes.admin import admin
    app.register_blueprint(admin)
    from .routes.member import member
    app.register_blueprint(member)


    return app
