from pathlib import Path

from lab.media.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    """Guarda contra el filesystem local, bajo un root fijo (la carpeta de
    media de una historia -- ver lab/media/paths.py :: story_media_dir()).
    """

    def __init__(self, root: Path):
        self.root = Path(root)

    def _resolve(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if self.root.resolve() not in path.parents and path != self.root.resolve():
            raise ValueError(f"Ruta fuera del root de storage: {relative_path!r}")
        return path

    def save(self, relative_path: str, data: bytes) -> str:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def read(self, relative_path: str) -> bytes:
        return self._resolve(relative_path).read_bytes()

    def exists(self, relative_path: str) -> bool:
        return self._resolve(relative_path).exists()

    def url_or_path(self, relative_path: str) -> str:
        return str(self._resolve(relative_path))
