import os
import sys

# Defina o ambiente ANTES de importar qualquer outro módulo
if len(sys.argv) > 1:
    os.environ["ENVIRONMENT"] = sys.argv[1]
else:
    os.environ["ENVIRONMENT"] = "development"

import subprocess
from config import settings

def main():
    # Inicia o Streamlit
    subprocess.run(["streamlit", "run", "streamlit_app.py"])

if __name__ == '__main__':
    main()