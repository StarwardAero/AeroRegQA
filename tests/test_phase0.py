import os
from config.settings import settings
from utils.logger import get_logger
from utils.file_utils import detect_encoding
from utils.text_utils import clean_markdown

log = get_logger("test_phase0")

def main():
    log.info("Testing Phase 0...")
    print(f"Base URL: {settings.LLM_BASE_URL}")
    print(f"Chroma DB Dir: {settings.CHROMA_DIR}")
    print(f"Logs Dir: {settings.LOGS_DIR}")
    
    dirty_text = "Hello\x00 World!"
    clean = clean_markdown(dirty_text)
    print(f"Cleaned text: {clean}")
    
    log.info("Phase 0 Test Completed successfully!")

if __name__ == "__main__":
    main()