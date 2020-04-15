#! /usr/bin/env python3
import time
import signal
import tornado.web
import tornado.ioloop
import tornado.httpserver
import tornado.wsgi
from tornado.options import options, define
import os,sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"../")))

import dal.models as models
from urls import handlers

define("debug", default=0, help="debug mode: 1 to open, 0 to close")
define("port", default=9887, help="port, defualt: 9887")

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "iamfromoutspaceyoukonwicametoearthawdx",
    "xsrf_cookies": False
}

class Application(tornado.web.Application):
    def __init__(self):
        settings["debug"] = bool(options.debug)
        super().__init__(handlers, **settings)


def sig_handler(sig, frame):
    print('\nReceived interrupt signal: %s' % sig)
    tornado.ioloop.IOLoop.instance().add_callback(shutdown)


def shutdown():
    print('Stopping http server, please wait...')
    # 停止接受Client连接
    application.stop()

    io_loop = tornado.ioloop.IOLoop.instance()
    # 设置最长等待强制结束时间
    deadline = time.time() + 5

    def stop_loop():
        now = time.time()
        if now < deadline:
            io_loop.add_timeout(now + 1, stop_loop)
        else:
            io_loop.stop()
    stop_loop()

if __name__ == "__main__":
    # 等待supervisor发送进程结束信号
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    models.init_db_data()
    tornado.options.parse_command_line()
    app = Application()
    application = tornado.httpserver.HTTPServer(app, xheaders=True)
    application.listen(options.port)
    if options.debug:
        debug_str = "in debug mode"
    else:
        debug_str = "in production mode"
    print("running hongjing.cc {0} @ {1}...".format(debug_str,options.port))
    tornado.ioloop.IOLoop.instance().start()
