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

def safe_save_uploaded_file(uploaded_file, dest_dir: Path) -> Path:
    """
    保存 Streamlit UploadedFile
    处理 Windows 文件名特殊字符（替换空格、中文路径兼容）
    """
    original_name = uploaded_file.name
    safe_name = re.sub(r'[\\/*?:"<>| ]', "_", original_name)
    
    dest_path = dest_dir / safe_name
    
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    log.info(f"Saved uploaded file to {dest_path}")
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
