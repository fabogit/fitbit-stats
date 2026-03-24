import os

# Base directory for data
DATA_DIR = os.environ.get("DATA_DIR", "data")

# Analysis timeframe
START_DATE = os.environ.get("START_DATE", None)
END_DATE = os.environ.get("END_DATE", None)

# User Metrics (Mifflin-St Jeor) - MUST BE SET VIA API/CONFIG
USER_HEIGHT_CM = int(os.environ.get("USER_HEIGHT_CM", 175))
USER_WEIGHT_KG = float(os.environ.get("USER_WEIGHT_KG", 75.0))
USER_DOB = os.environ.get("USER_DOB", "2000-01-01")
USER_GENDER = os.environ.get("USER_GENDER", "male")

# Output paths
CLIENT_PUBLIC_DIR = os.environ.get("CLIENT_PUBLIC_DIR", os.path.join("..", "client", "public"))
