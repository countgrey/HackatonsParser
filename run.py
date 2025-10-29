#!/usr/bin/env python3

import subprocess
import sys
import time
import threading

def run_parser():
    print("Запуск парсера...")
    result = subprocess.run([sys.executable, "parser.py"])
    if result.returncode == 0:
        print("Парсер завершил работу успешно")
    else:
        print("Парсер завершил работу с ошибкой")

def run_bot():
    print("Запуск телеграм бота...")
    subprocess.run([sys.executable, "bot.py"])

if __name__ == "__main__":
    run_parser()
    
    print("\n" + "="*50)
    run_bot()
