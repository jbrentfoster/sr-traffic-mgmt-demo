"""

Copyright (c) 2025 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.

"""
import argparse
from datetime import datetime
import json
import os
import traceback
import threading
from logging import Logger
import tornado.web
import tornado.websocket
import tornado.escape
import tornado.ioloop
import tornado.locks
from tornado.web import url
from python import methods, telemetry
import logging
from distutils.dir_util import remove_tree
from distutils.dir_util import mkpath
import asyncio
import signal
import sys
import socket

# global variables...
logging_level = 'INFO'
initial_url = "https://jsonplaceholder.typicode.com/posts"
# open_websockets = []
open_websockets = set()  # Use a set instead of a list to prevent duplicates
# application = tornado.web.Application
KAFKA_TOPIC = 'telegraf'
KAFKA_BOOTSTRAP_SERVER = '10.135.7.105:9092'
telemetry_thread = None
telemetry_encoding_path = "Cisco-IOS-XR-pfi-im-cmd-oper:interfaces/interface-xr/interface"
thread = None
stop_event = threading.Event()  # Global event to signal thread shutdown


class IndexHandler(tornado.web.RequestHandler):
    async def get(self):
        await self.render("templates/index.html", port=args.port)

class InterfaceHandler(tornado.web.RequestHandler):
    async def get(self):
        await self.render("templates/interfaces.html", port=args.port)


class AjaxHandler(tornado.web.RequestHandler):
    async def post(self):
        global initial_url

        request_body = self.request.body.decode("utf-8")
        # request = tornado.escape.recursive_unicode(self.request.arguments)
        logging.info("Received AJAX request..")
        logging.info(request_body)
        request = json.loads(request_body)
        try:
            action = request['action']
        except Exception as err:
            logging.warning("Invalid AJAX request")
            logging.warning(err)
            response = {'status': 'failed', 'error': err}
            logging.info(response)
            self.write(json.dumps(response))
            return

        if action == 'send-request':
            initial_url = request['url']
            clean_files()
            response = await methods.send_async_request(initial_url, "foo", "bar")
            # response = {'action': 'collect', 'status': 'completed', 'body': str(response_body)}
            self.write(json.dumps(response))
        else:
            logging.warning("Received request for unknown operation!")
            response = {'status': 'unknown', 'error': "unknown request"}
            logging.info(response)
            self.write(json.dumps(response))


class WebSocket(tornado.websocket.WebSocketHandler):

    def open(self):
        logging.info("WebSocket opened")
        open_websockets.add(self)  # Add WebSocket instance to the set

    def send_message(self, message):
        if self.ws_connection and self.ws_connection.stream and not self.ws_connection.stream.closed():
            self.write_message(message)
        else:
            logging.warning("Attempted to send a message to a closed WebSocket")

    def on_message(self, message):
        """Evaluates the function pointed to by json-rpc."""
        json_rpc = json.loads(message)
        logging.info("WebSocket received message: " + json.dumps(json_rpc))

        try:
            result = getattr(methods, json_rpc["method"])(**json_rpc["params"])
            error = None
        except Exception as err:
            result = traceback.format_exc()
            error = 1

        json_rpc_response = json.dumps({"response": result, "error": error}, separators=(",", ":"))
        logging.info("WebSocket replied with message: " + json_rpc_response)

        self.send_message(json_rpc_response)  # Use the safer send_message method

    def on_close(self):
        if self in open_websockets:
            open_websockets.remove(self)  # Ensure the WebSocket is removed properly
        self.close()
        logging.info("WebSocket closed!")

    def check_origin(self, origin):
        """Allow connections from any origin (if necessary)."""
        return True


def main():
    # global application
    # Set up logging
    try:
        os.remove('logs/collection.log')
    except Exception as err:
        logging.info("No log file to delete...")

    log_formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
    root_logger: Logger = logging.getLogger()
    root_logger.level = eval('logging.{}'.format(logging_level))

    file_handler = logging.FileHandler(filename='logs/collection.log')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    logging.info("Starting webserver...")
    current_time = str(datetime.now().strftime('%Y-%m-%d-%H%M-%S'))
    logging.info("Current time is: " + current_time)
    settings = {
        # "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "static_path": os.path.normpath(os.path.dirname(__file__)),
        # "cookie_secret": "__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
        # "login_url": "/login",
        # "xsrf_cookies": True,
    }

    handlers = [url(r"/", IndexHandler, name="home"),
                url(r"/websocket", WebSocket),
                url(r'/static/(.*)',
                    tornado.web.StaticFileHandler,
                    dict(path=settings['static_path'])),
                url(r'/interfaces', InterfaceHandler, name="interfaces"),
                # url(r'/references', ReferencesHandler, name="references"),
                url(r'/ajax', AjaxHandler, name="ajax")
                ]

    application = tornado.web.Application(handlers)
    # application.listen(args.port)

    # Create a custom server socket with SO_REUSEADDR
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Enable address reuse
    # server_socket.bind(("0.0.0.0", args.port))
    server_socket.listen(128)  # Set backlog queue

    # Wrap the socket with a Tornado HTTP server
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.add_socket(server_socket)
    http_server.listen(args.port)

    # webbrowser.open("http://localhost:%d/" % args.port, new=2)

    signal.signal(signal.SIGTERM, signal_handler)
    try:
        # Start the thread for the telemetry processing
        global thread
        thread = threading.Thread(target=run_traffic_matrix_in_thread)
        thread.start()

        logging.info("Starting IOLoop for webserver...")
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        signal_handler(None, None)


def signal_handler(sig, frame):
    global thread
    logging.info('Exiting gracefully...')

    # Stop the worker thread cleanly
    logging.info("Stopping telemetry thread...")
    stop_event.set()  # Tell the thread to stop
    thread.join(timeout=5)  # Ensure it doesn't block indefinitely

    # Stop the Tornado event loop
    io_loop = tornado.ioloop.IOLoop.current()

    # async_method(ioloop=ioloop, callback=ioloop.stop)
    io_loop.add_callback(io_loop.stop)

    logging.info("Stopping webserver...")
    sys.exit(0)


def run_traffic_matrix_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        while not stop_event.is_set():  # Check stop event before running
            loop.run_until_complete(telemetry.traffic_matrix_updater(open_websockets))
            # asyncio.sleep(1)  # Prevent 100% CPU usage
    except asyncio.CancelledError:
        logging.info("Telemetry thread stopped.")
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())  # Proper cleanup
        loop.stop()  # Stop event loop before exiting
        loop.close()


def send_message_open_ws(message):
    for ws in open_websockets:
        ws.send_message(message)


def clean_files():
    # Delete all output files
    logging.info("Cleaning files from last collection...")
    try:
        remove_tree('jsonfiles')
        remove_tree('jsongets')
    except Exception as err:
        logging.info("No files to cleanup...")

    # Recreate output directories
    mkpath('jsonfiles')
    mkpath('jsongets')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Starts a webserver for stuff.")
    parser.add_argument("--port", type=int, default=8000, help="The port on which "
                                                               "to serve the website.")
    args = parser.parse_args()
    main()
