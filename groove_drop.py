"""Read-only folder adding with Windows native Explorer drop support."""
import os
from pathlib import Path


class FolderDropMixin:
    def install_folder_drop(self):
        self._folder_drop = None
        if os.name == 'nt':
            self.after_idle(self._install_windows_drop)

    def _install_windows_drop(self):
        from groove_windows_drop import NativeFolderDrop
        try:
            self._folder_drop = NativeFolderDrop(self, self.drop_folder_paths)
        except (OSError, RuntimeError) as error:
            self.status.set('Folder drop unavailable. Use Add Folders.')
            self.log('Could not enable Windows folder drops: ' + str(error))

    def destroy(self):
        if getattr(self, '_folder_drop', None):
            self._folder_drop.close()
            self._folder_drop = None
        super().destroy()

    def add_folder_paths(self, paths):
        """Return added, accepted and ignored counts; canonicalize duplicates."""
        if self.worker_busy:
            return 0, 0, len(paths)
        def key(path):
            return os.path.normcase(str(Path(path).resolve()))
        known = {key(path) for path in self.roots}
        added = accepted = ignored = 0
        for value in paths:
            try:
                path = Path(value)
                if not value or not path.is_absolute() or not path.is_dir():
                    ignored += 1
                    continue
                canonical = key(path)
            except (OSError, ValueError, RuntimeError):
                ignored += 1
                continue
            accepted += 1
            if canonical not in known:
                self.roots.append(str(path.resolve()))
                known.add(canonical)
                added += 1
        self.update_roots()
        return added, accepted, ignored

    def drop_folder_paths(self, paths):
        if self.worker_busy:
            return False
        added, accepted, ignored = self.add_folder_paths(paths)
        if not accepted:
            self.status.set('Drop folders here to add them. Use Add Files for music files.')
            return False
        message = (f'Added {added} folder(s). Click Start Scan when ready.' if added
                   else 'Those folders are already in the list.')
        if ignored:
            message += f' Ignored {ignored} item(s) that were not available folders.'
        self.status.set(message)
        return True
