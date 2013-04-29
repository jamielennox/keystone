import sys

from threading import Thread
from wsgiref import simple_server

from keystone.common import config
from keystone.common import logging

CONF = config.CONF
LOG = logging.getLogger(__name__)


class Server(object):

    def __init__(self, application, host=None, port=None, threads=0):
        self.application = application
        self.host = host
        self.port = port
        self.do_ssl = False
        self.cert_required = False
        self._server = None

    def start(self, key=None, backlog=128):
        """Run a WSGI server with the given application."""
        LOG.debug(_('Starting %(arg0)s on %(host)s:%(port)s') %
                  {'arg0': sys.argv[0],
                   'host': self.host,
                   'port': self.port})

        self.server = serve(self.application, host=self.host, port=self.port, daemon_threads=True, start_loop=False)

        self.host, self.port = self.server.server_address
        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        print "starting thread"
        self.server_thread.start()
        print "STarted on ", self.host, self.port
        # time.sleep(3)

