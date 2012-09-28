from collections import deque
import datetime

from collections import namedtuple
PlaylistResource = namedtuple('PlaylistResource', ['server', 'path'])

class Balancer(object):
    '''
    Controls which server is active for a playlist (m3u8)
    '''
    NOT_MODIFIED_TOLERANCE = 8 # in seconds

    def __init__(self):
        self.paths = {}
        self.modified_at = {}

    def update(self, paths):
        '''
        ``paths`` is a dict returned from ``discover.discover()``
        '''
        self._clean_removed_paths(paths)
        for path, servers in paths.items():
            self._update_path(path, servers)

    def notify_modified(self, server, path):
        '''
        Remembers that a given server returned a new playlist
        '''
        self.modified_at[path] = self._now()

    def notify_error(self, server, path):
        '''
        Remembers that a given server failed.
        This immediately changes the active server for this path, is another one exists.
        '''
        if self._active_server_for_path(path) == server:
            self._change_active_server(path)

    @property
    def actives(self):
        '''
        Returns a list of ``PlaylistResource``s
        '''
        for path in self.paths:
            active_server = self._active_server_for_path(path)
            if self._outdated(active_server, path):
                self._change_active_server(path)
                active_server = self._active_server_for_path(path)
            yield PlaylistResource(active_server, path)

    def _clean_removed_paths(self, new_paths):
        removed_paths = set(self.paths.keys()).difference(new_paths.keys())
        for path in removed_paths:
            del self.modified_at[path]
            del self.paths[path]

    def _update_path(self, path, servers):
        active = self._active_server_for_path(path)
        if active in servers:
            self.paths[path] = deque([active])
            self.paths[path].extend([server for server in servers if server != active])
        else:
            self.paths[path] = deque(servers)
            self.modified_at[path] = None

    def _active_server_for_path(self, path):
        servers = self.paths.get(path, [])
        if servers:
            return servers[0]

    def _change_active_server(self, path):
        self.paths[path].rotate(-1)
        self.modified_at[path] = None

    def _outdated(self, server, path):
        last_change = self.modified_at.get(path, None)
        if not last_change:
            # This server is new, so it can't be obsolete
            return False
        delta_from_last_change = self._now() - last_change
        delta_tolerance = datetime.timedelta(seconds=self.NOT_MODIFIED_TOLERANCE)
        return delta_from_last_change > delta_tolerance

    def _now(self):
        # The only reason for this to be a method
        # is that it's easier to monkey patch it
        return datetime.datetime.now()
