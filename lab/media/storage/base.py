"""
Abstraccion de almacenamiento (docs/LAB_MEDIA_ASSETS.md). lab/media/generation.py
habla solo contra esta interfaz -- hoy solo existe LocalStorageProvider,
pero un S3StorageProvider/AzureBlobStorageProvider futuro se conecta aca
sin tocar el resto de lab/media/.
"""

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    def save(self, relative_path: str, data: bytes) -> str:
        """Guarda data en relative_path (dentro del root del provider). Devuelve
        una referencia resoluble (path absoluto local hoy; podria ser una URL
        con un provider de nube futuro)."""

    @abstractmethod
    def read(self, relative_path: str) -> bytes:
        ...

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        ...

    @abstractmethod
    def url_or_path(self, relative_path: str) -> str:
        """Referencia para mostrar/usar el archivo sin necesariamente leerlo."""
