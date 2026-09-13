import uuid
from pathlib import Path

from app.core.config import settings


class StorageService:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR)

    def save(self, project_id: int, filename: str, content: bytes) -> str:
        project_dir = self.base_dir / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        extension = Path(filename).suffix
        stored_name = f"{uuid.uuid4().hex}{extension}"
        destination = project_dir / stored_name
        destination.write_bytes(content)
        return destination.as_posix()

    def delete(self, storage_path: str) -> None:
        path = Path(storage_path)
        if path.exists():
            path.unlink()
