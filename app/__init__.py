# encoding: utf-8
import os
import platform
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config
from config import config_log
from .util import global_variable  # 初始化文件地址
from sqlalchemy import MetaData
from flask_apscheduler import APScheduler
import atexit
import fcntl

login_manager = LoginManager()
# login_manager.session_protection = 'None'
# login_manager.login_view = '.login'


# 由于数据库迁移的时候，不兼容约束关系的迁移，下面是百度出的解决方案
naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention), use_native_unicode='utf8')

# db = SQLAlchemy()

scheduler = APScheduler()
basedir = os.path.abspath(os.path.dirname(__file__))


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.logger.addHandler(config_log())  # 初始化日志
    config[config_name].init_app(app)

    # https://blog.csdn.net/yannanxiu/article/details/53426359 关于定时任务访问数据库时报错
    # 坑在这2个的区别 db = SQLAlchemy() db = SQLAlchemy(app)
    db.init_app(app)
    db.app = app
    db.create_all()

    login_manager.init_app(app)
    # 启动定时任务
    scheduler_init(app)
    #cheduler.init_app(app)
    #scheduler.start()  # 定时任务启动

    from .api_1_0 import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')

    # from .api_1_0.model import api_1_0 as api_blueprint
    # app.register_blueprint(api_blueprint, url_prefix='/api_1_0')
    return app

def scheduler_init(app):
    """
    保证系统只启动一次定时任务
    :param app:
    :return:
    """
    if platform.system() != 'Windows':
        fcntl = __import__("fcntl")
        f = open('scheduler.lock', 'wb')
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            scheduler.init_app(app)
            scheduler.start()
            app.logger.debug('Scheduler Started,---------------')
        except:
            pass

        def unlock():
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

        atexit.register(unlock)
    else:
        msvcrt = __import__('msvcrt')
        f = open('scheduler.lock', 'wb')
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            scheduler.init_app(app)
            scheduler.start()
            app.logger.debug('Scheduler Started,----------------')
        except:
            pass

        def _unlock_file():
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except:
                pass

        atexit.register(_unlock_file)
