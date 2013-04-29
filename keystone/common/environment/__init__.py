
__all__ = ['Server', 'httplib', 'subprocess']

from keystone.common import config
from keystone.common import logging

CONF = config.CONF
LOG = logging.getLogger(__name__)

use_eventlet = False


if use_eventlet:
    LOG.info("Setup Eventlet")
    print ("Setup Eventlet")
    import eventlet
    from keystone.common import utils

    monkeypatch_thread = not CONF.standard_threads
    pydev_debug_url = utils.setup_remote_pydev_debug()
    if pydev_debug_url:
        # in order to work around errors caused by monkey patching we have to
        # set the thread to False.  An explanation is here:
        # http://lists.openstack.org/pipermail/openstack-dev/2012-August/
        # 000794.html
        monkeypatch_thread = False
    eventlet.patcher.monkey_patch(all=False, socket=True, time=True,
                                  thread=monkeypatch_thread)

    from keystone.common.environment.eventlet_server import Server
    from eventlet.green import httplib
    from eventlet.green import subprocess

else:
    LOG.info("Not Using Eventlet")
    print ("Not Using Eventlet")
    from keystone.common.environment.paste_server import Server
    import httplib
    import subprocess
