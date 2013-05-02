import sys

from paste.httpserver import serve

from keystone.common import config
from keystone.common import logging

from OpenSSL import SSL

CONF = config.CONF
LOG = logging.getLogger(__name__)

use_process = False

if use_process:
    from multiprocessing import Process as Concurrent
else:
    # using threads does not respond to KeyboardInterrupt
    # so will server forever and not be cancellable
    from threading import Thread as Concurrent


class Server(Concurrent):

    def __init__(self, application, host=None, port=None, threads=0, key=None):
        Concurrent.__init__(self)

        self.application = application
        self.host = host
        self.port = port
        self.cert_required = False
        self.daemon = True
        self.server = None
        self.ssl_context = None

    def start(self):
        # This allows the server to be created in the main thread but
        # served from the new thread

        self.server = serve(self.application,
                            host=self.host, port=self.port,
                            daemon_threads=True, use_threadpool=False,
                            start_loop=False, request_queue_size=1,
                            ssl_context=self.ssl_context)

        self.host, self.port = self.server.server_address

        super(Server, self).start()

    def set_ssl(self, certfile, keyfile=None,
                ca_certs=None, cert_required=True):
        if not self.context:
            self.context = SSL.context(SSL.TLSv1_METHOD)
            self.context.set_options(SSL.OP_NO_SSLv2)

        if keyfile:
            self.context.use_privatekey_file(keyfile)

        if certfile:
            self.context.use_certificate_file(certfile)

        if ca_certs:
            self.context.use_certificate_chain_file(ca_certs)

        if ca_certs:
            self.context.set_verify(SSL.VERIFY_PEER | SSL.VERIFY_CLIENT_ONCE,
                                    self._ssl_verify_callback)

    def _ssl_verify_callback(self, conn, cert, err_no, depth, result):
        if not result:
            print "CLIENT CERT FAILED"

        return result

    def run(self, key=None, backlog=128):
        """Run a WSGI server with the given application."""
        LOG.debug(_('Starting %(arg0)s on %(host)s:%(port)s') %
                  {'arg0': sys.argv[0],
                   'host': self.host,
                   'port': self.port})

        self.server.serve_forever()

    def kill(self):
        if use_process:
            self.terminate()
        else:
            self.server.shutdown()

        self.join()
