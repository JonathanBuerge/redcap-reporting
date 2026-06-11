import os
import sys

# Wenn das Programm vom PyInstaller (frozen) ausgeführt wird, setze den Pfad
# auf das Verzeichnis der ausführbaren Datei. Andernfalls auf das Verzeichnis dieses Skripts.
if getattr(sys, 'frozen', False):
    bundle_dir = os.path.dirname(sys.executable)
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

os.chdir(bundle_dir)
sys.path.insert(0, bundle_dir)

from src.main import main

if __name__ == '__main__':
    main()
