import re
import time
from pathlib import Path
import chardet
from utils.logger import get_logger

log = get_logger(__name__)

def detect_encoding(file_path: Path) -> str:
    """检测文件编码"""
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)
    result = chardet.detect(raw_data)
    encoding = result['encoding'] or 'utf-8'
    log.debug(f"Detected encoding for {file_path.name}: {encoding}")
    return encoding

def sanitize_filename(filename: str, fallback: str = "upload") -> str:
    """清理上传文件名，避免路径穿越和非法字符。"""
    raw_name = re.split(r"[\\/]+", filename or "")[-1].strip()
    safe_name = re.sub(r'[\\/*?:"<>|\s]+', "_", raw_name)
    safe_name = re.sub(r"_+", "_", safe_name).strip("._")
    if not safe_name:
        safe_name = fallback

    suffix = Path(safe_name).suffix
    stem = Path(safe_name).stem[:120]
    return f"{stem}{suffix}" if suffix else stem


def resolve_safe_upload_path(filename: str, dest_dir: Path) -> tuple[str, Path]:
    """返回安全文件名与目标路径，确保路径位于上传目录内。"""
    safe_name = sanitize_filename(filename)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_root = dest_dir.resolve()
    dest_path = (dest_root / safe_name).resolve()
    if dest_path.parent != dest_root:
        raise ValueError("非法文件路径")
    return safe_name, dest_path


def safe_save_uploaded_file(uploaded_file, dest_dir: Path, max_size_bytes: int | None = None) -> Path:
    """
    保存 Streamlit UploadedFile
    处理 Windows 文件名特殊字符，并限制路径与大小。
    """
    original_name = getattr(uploaded_file, "name", "upload")
    safe_name, dest_path = resolve_safe_upload_path(original_name, dest_dir)
    size = getattr(uploaded_file, "size", None)
    if max_size_bytes is not None and size is not None and size > max_size_bytes:
        raise ValueError(f"文件超过大小限制: {size} bytes > {max_size_bytes} bytes")

    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    log.info(f"Saved uploaded file '{safe_name}' to {dest_path}")
    return dest_path

def cleanup_temp_files(directory: Path, max_age_hours: int) -> int:
    """清理超时文件"""
    count = 0
    now = time.time()
    max_age_seconds = max_age_hours * 3600

    if not directory.exists():
        return count

    for file_path in directory.iterdir():
        if file_path.is_file():
            file_age = now - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    file_path.unlink()
                    count += 1
                    log.debug(f"Deleted old file: {file_path}")
                except Exception as e:
                    log.error(f"Failed to delete {file_path}: {e}")

    log.info(f"Cleaned up {count} files in {directory}")
    return count
