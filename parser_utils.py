import subprocess
import sys

def run_parser():
    """Запускает парсер как отдельный процесс"""
    try:
        result = subprocess.run([sys.executable, "parser.py"], 
                              capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)
