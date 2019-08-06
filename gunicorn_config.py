import gevent.monkey
import multiprocessing

"""
gunicorn的配置文件
"""
# gevent的猴子魔法 变成非阻塞
gevent.monkey.patch_all()

bind = '127.0.0.1:8080'

# 启动的进程数
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 1

# 指定每个工作者的线程数
threads = 1
worker_class = 'gunicorn.workers.ggevent.GeventWorker'

# 代码发生变化是否自动重启
reload = True

timeout = 180
