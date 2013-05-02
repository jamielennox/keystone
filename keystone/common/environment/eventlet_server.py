
import socket
import sys
import ssl

import greenlet
import eventlet.wsgi

from keystone.common import config
from keystone.common import logging

CONF = config.CONF
LOG = logging.getLogger(__name__)


class WritableLogger(object):
    """A thin wrapper that responds to `write` and logs."""

    def __init__(self, logger, level=logging.DEBUG):
        self.logger = logger
        self.level = level

    def write(self, msg):
        self.logger.log(self.level, msg)


class Server(object):
    """Server class to manage multiple WSGI sockets and applications."""

    def __init__(self, application, host=None, port=None, threads=1000):
        self.application = application
        self._host = host or '0.0.0.0'
        self._port = port or 0
        self.pool = eventlet.GreenPool(threads)
        self.socket_info = {}
        self.greenthread = None
        self.do_ssl = False
        self.cert_required = False

    def start(self, key=None, backlog=128):
        """Run a WSGI server with the given application."""
        LOG.debug(_('Starting %(arg0)s on %(host)s:%(port)s') %
                  {'arg0': sys.argv[0],
                   'host': self._host,
                   'port': self._port})

        # TODO(dims): eventlet's green dns/socket module does not actually
        # support IPv6 in getaddrinfo(). We need to get around this in the
        # future or monitor upstream for a fix
        info = socket.getaddrinfo(self._host,
                                  self._port,
                                  socket.AF_UNSPEC,
                                  socket.SOCK_STREAM)[0]
        _socket = eventlet.listen(info[-1],
                                  family=info[0],
                                  backlog=backlog)
        if key:
            self.socket_info[key] = _socket.getsockname()
        # SSL is enabled
        if self.do_ssl:
            if self.cert_required:
                cert_reqs = ssl.CERT_REQUIRED
            else:
                cert_reqs = ssl.CERT_NONE
            sslsocket = eventlet.wrap_ssl(_socket, certfile=self.certfile,
                                          keyfile=self.keyfile,
                                          server_side=True,
                                          cert_reqs=cert_reqs,
                                          ca_certs=self.ca_certs)
            _socket = sslsocket

        self.greenthread = self.pool.spawn(self._run,
                                           self.application,
                                           _socket)

    @property
    def port(self):
        return self.socket_info['socket'][1]

    def set_ssl(self, certfile, keyfile=None, ca_certs=None,
                cert_required=True):
        self.certfile = certfile
        self.keyfile = keyfile
        self.ca_certs = ca_certs
        self.cert_required = cert_required
        self.do_ssl = True

    def kill(self):
        if self.greenthread:
            self.greenthread.kill()

    def join(self):
        """Wait until all servers have completed running."""
        try:
            self.pool.waitall()
        except KeyboardInterrupt, greenlet.GreenletExit:
            pass

    def _run(self, application, socket):
        """Start a WSGI server in a new green thread."""
        log = logging.getLogger('eventlet.wsgi.server')
        try:
            eventlet.wsgi.server(socket, application, custom_pool=self.pool,
                                 log=WritableLogger(log))
        except Exception:
            LOG.exception(_('Server error'))
            raise

