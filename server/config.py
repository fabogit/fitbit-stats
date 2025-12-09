import os

# Base directory for data
DATA_DIR = "data"

# Analysis timeframe
START_DATE = "2024-04-01"
END_DATE = None  # None means "up to the latest available data"

# User Metrics (Mifflin-St Jeor)
USER_HEIGHT_CM = 180
USER_AGE = 38
USER_GENDER = 'male'

# Output paths
CLIENT_PUBLIC_DIR = os.path.join("..", "client", "public")