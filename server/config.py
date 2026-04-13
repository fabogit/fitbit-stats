import os

# Base directory for data
DATA_DIR = os.environ.get("DATA_DIR", "data")

# Analysis timeframe
START_DATE = os.environ.get("START_DATE", None)
END_DATE = os.environ.get("END_DATE", None)

# User Metrics (Mifflin-St Jeor) - MUST BE SET VIA API/CONFIG
USER_HEIGHT_CM = int(os.environ.get("USER_HEIGHT_CM", 0))
USER_WEIGHT_KG = float(os.environ.get("USER_WEIGHT_KG", 0.0))
USER_DOB = os.environ.get("USER_DOB", "")
USER_GENDER = os.environ.get("USER_GENDER", "")

# Output paths
import sys
import platform

if getattr(sys, 'frozen', False):
    import platform
    home = os.path.expanduser("~")
    if platform.system() == "Windows":
        CLIENT_PUBLIC_DIR = os.path.join(os.environ.get("APPDATA", home), "com.fitstats")
    elif platform.system() == "Darwin":
        CLIENT_PUBLIC_DIR = os.path.join(home, "Library", "Application Support", "com.fitstats")
    else:
        CLIENT_PUBLIC_DIR = os.path.join(home, ".local", "share", "com.fitstats")
    os.makedirs(CLIENT_PUBLIC_DIR, exist_ok=True)
else:
    CLIENT_PUBLIC_DIR = os.environ.get("CLIENT_PUBLIC_DIR", os.path.join("..", "client", "public"))
