"""Read-only folder adding with Windows native Explorer drop support."""
import os
from pathlib import Path
from groove_core import EXTENSIONS


class FolderDropMixin:
    def install_folder_drop(self):
        self._folder_drop = None
        if os.name == 'nt':
            self.after_idle(self._install_windows_drop)

    def _install_windows_drop(self):
        from groove_windows_drop import NativeFolderDrop
        try:
            self._folder_drop = NativeFolderDrop(self, self.drop_paths)
        except (OSError, RuntimeError) as error:
            self.status.set('Drop unavailable. Use Add Folders or Add Files.')
            self.log('Could not enable Windows folder drops: ' + str(error))

    def destroy(self):
        if hasattr(self,'track_editor'):self.track_editor.player.close()
        if getattr(self, '_folder_drop', None):
            self._folder_drop.close()
            self._folder_drop = None
        super().destroy()

    def add_folder_paths(self, paths):
        return self.add_paths(paths, folders_only=True)

    def add_paths(self, paths, folders_only=False):
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
                if (not value or not path.is_absolute() or not
                    (path.is_dir() or (not folders_only and path.suffix.lower() in EXTENSIONS and path.is_file()))):
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
        return self.drop_paths(paths, folders_only=True)

    def drop_paths(self, paths, folders_only=False):
        if self.worker_busy:
            self.status.set('Wait for the current operation to finish, then drop items again.')
            return False
        added, accepted, ignored = self.add_paths(paths, folders_only=folders_only)
        if not accepted:
            self.status.set('Drop folders or supported music files here to add them.')
            return False
        noun='folder(s)' if folders_only else 'item(s)'
        message = (f'Added {added} {noun}. Starting scan…' if added
                   else 'Those folders / files are already in the list.')
        if ignored:
            message += f' Ignored {ignored} item(s) that were unavailable or unsupported.'
        self.status.set(message)
        if added:
            self.scan()
        return True
