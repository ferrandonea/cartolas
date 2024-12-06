from enum import Enum
from pathlib import Path

class FolderPaths(Enum):
    TEMP = Path("/path/to/temp")
    CORRECT = Path("/path/to/correct")
    WRONG = Path("/path/to/wrong")
    DOWNLOAD = Path("/path/to/download")

    @classmethod
    def validate_folders(cls):
        """
        Verifica que todas las carpetas existan.
        """
        for folder in cls:
            if not folder.value.exists():
                raise FileNotFoundError(f"La carpeta '{folder.value}' no existe.")
    
    @classmethod
    def create_missing_folders(cls):
        """
        Crea las carpetas que no existan.
        """
        for folder in cls:
            if not folder.value.exists():
                folder.value.mkdir(parents=True, exist_ok=True)
                print(f"Carpeta creada: {folder.value}")