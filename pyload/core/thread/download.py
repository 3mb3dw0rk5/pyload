# -*- coding: utf-8 -*-

from pyload.utils.convert import to_str
# @author: RaNaN

from __future__ import absolute_import, unicode_literals

import sys
import time
from builtins import str
from queue import Queue
from traceback import print_exc

from future import standard_library

import pycurl
from pyload.requests.request import ResponseException
from pyload.utils.layer.safethreading import Event

from pyload.core.network.base import Abort, Fail, Retry
from pyload.core.network.hoster import Reconnect, Skip
from pyload.core.thread.plugin import PluginThread

standard_library.install_aliases()


class DownloadThread(PluginThread):
    """Thread for downloading files from 'real' hoster plugins."""
    __slots__ = ['active', 'queue', 'running']

    def __init__(self, manager):
        """Constructor."""
        PluginThread.__init__(self, manager)

        self.__running = Event()
        self.queue = Queue()  # job queue
        self.active = None

    @property
    def running(self):
        return self.__running.is_set()

    def _handle_abort(self, file):
        try:
            self.pyload.log.info(
                self._('Download aborted: {0}').format(file.name))
        except Exception:
            pass
        file.set_status('aborted')

    def _handle_reconnect(self, file):
        self.queue.put(file)
        # file.req.clear_cookies()
        while self.manager.reconnecting.isSet():
            time.sleep(0.5)

    def _handle_retry(self, file, reason):
        self.pyload.log.info(
            self._('Download restarted: {0}').format(file.name), reason)
        self.queue.put(file)

    def _handle_notimplement(self, file):
        self.pyload.log.error(
            self._('Plugin {0} is missing a function').format(file.pluginname))
        file.set_status('failed')
        file.error = 'Plugin does not work'
        self.clean(file)

    def _handle_tempoffline(self, file):
        file.set_status('temp. offline')
        self.pyload.log.warning(
            self._('Download is temporary offline: {0}').format(file.name))
        file.error = self._('Internal Server Error')

        if self.pyload.debug:
            print_exc()
            self.debug_report(file)

        self.pyload.adm.download_failed(file)
        self.clean(file)

    def _handle_failed(self, file, errmsg):
        file.set_status('failed')
        self.pyload.log.warning(
            self._('Download failed: {0}').format(file.name), errmsg)
        file.error = errmsg

        if self.pyload.debug:
            print_exc()
            self.debug_report(file)

        self.pyload.adm.download_failed(file)
        self.clean(file)

    # TODO: activate former skipped downloads
    def _handle_fail(self, file, errmsg):
        if errmsg == 'offline':
            file.set_status('offline')
            self.pyload.log.warning(
                self._('Download is offline: {0}').format(file.name))
        elif errmsg == 'temp. offline':
            file.set_status('temp. offline')
            self.pyload.log.warning(
                self._('Download is temporary offline: {0}').format(file.name))
        else:
            file.set_status('failed')
            self.pyload.log.warning(
                self._('Download failed: {0}').format(file.name), errmsg)
            file.error = errmsg

        self.pyload.adm.download_failed(file)
        self.clean(file)

    def _handle_skip(self, file, errmsg):
        file.set_status('skipped')

        self.pyload.log.info(
            self._('Download skipped: {0} due to {1}').format(
                file.name, errmsg))

        self.clean(file)

        self.pyload.files.check_package_finished(file)

        self.active = None
        self.pyload.files.save()

    def _handle_error(self, file, errmsg, errcode=None):
        self.pyload.log.debug(
            'pycurl exception {0}: {1}'.format(errcode, errmsg))

        if errcode in (7, 18, 28, 52, 56):
            self.pyload.log.warning(
                self._(
                    "Couldn't connect to host or connection reset, "
                    'waiting 1 minute and retry'))
            wait = time.time() + 60

            file.wait_until = wait
            file.set_status('waiting')
            while time.time() < wait:
                time.sleep(0.5)

                if file.abort:
                    break

            if file.abort:
                self.pyload.log.info(
                    self._('Download aborted: {0}').format(file.name))
                file.set_status('aborted')
                # do not clean, aborting function does this itself
                # self.clean(file)
            else:
                self.queue.put(file)
        else:
            file.set_status('failed')
            self.pyload.log.error(
                self._('pycurl error {0}: {1}').format(errcode, errmsg))
            if self.pyload.debug:
                print_exc()
                self.debug_report(file)

            self.pyload.adm.download_failed(file)

    def _run(self, file):
        file.init_plugin()

        # after initialization the thread is fully ready
        self.__running.set()

        # this file was deleted while queuing
        # TODO: what will happen with new thread manager?
        # if not file.has_plugin(): continue

        file.plugin.check_for_same_files(starting=True)
        self.pyload.log.info(
            self._('Download starts: {0}'.format(file.name)))

        # start download
        self.pyload.adm.download_preparing(file)
        file.plugin.preprocessing(self)

        self.pyload.log.info(
            self._('Download finished: {0}').format(file.name))
        self.pyload.adm.download_finished(file)
        self.pyload.files.check_package_finished(file)

    def _finalize(self, file):
        self.pyload.files.save()
        file.check_if_processed()
        sys.exc_clear()
        # manager could still be waiting for it
        self.__running.set()
        # only done when job was not put back
        if self.queue.empty():
            self.manager.done(self)

    def run(self):
        """Run method."""
        file = None
        while True:
            del file

            self.active = self.queue.get()
            file = self.active

            if self.active == 'quit':
                self.active = None
                self.manager.discard(self)
                return True

            try:
                self._run(file)
            except NotImplementedError:
                self._handle_notimplement(file)
                continue
            except Abort:
                self._handle_abort(file)
                # abort cleans the file
                # self.clean(file)
                continue
            except Reconnect:
                self._handle_reconnect(file)
                continue
            except Retry as exc:
                self._handle_retry(file, exc.args[0])
                continue
            except Fail as exc:
                self._handle_fail(file, exc.args[0])
                continue
            except pycurl.error as exc:
                errcode = None
                errmsg = exc.args
                if len(exc.args) == 2:
                    errcode, errmsg = exc.args
                self._handle_error(file, errmsg, errcode)
                self.clean(file)
                continue
            except Skip as exc:
                self._handle_skip(file,to_str(exc))
                continue
            except Exception as exc:
                if isinstance(exc, ResponseException) and exc.code == 500:
                    self._handle_tempoffline(file)
                else:
                    self._handle_failed(file, to_str(exc))
                continue
            finally:
                self._finalize(file)

            # file.plugin.req.clean()
            self.active = None
            file.finish_if_done()
            self.pyload.files.save()

    def get_progress_info(self):
        if not self.active:
            return
        return self.active.get_progress_info()

    def put(self, job):
        """Assign a job to the thread."""
        self.queue.put(job)

    def clean(self, file):
        """Set thread inactive and release file."""
        file.release()

    def quit(self):
        """Stops the thread."""
        self.put('quit')
