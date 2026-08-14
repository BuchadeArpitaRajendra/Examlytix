from dotenv import load_dotenv
load_dotenv(override=True)
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTO_FOLDER = os.path.join(BASE_DIR, "photos")
EXPORT_FOLDER = os.path.join(BASE_DIR, "exports")
CASCADE_PATH = os.path.join(BASE_DIR, "haarcascade", "haarcascade_frontalface_default.xml")

os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

FLASK_HOST = os.getenv("FLASK_HOST")
FLASK_PORT = os.getenv("FLASK_PORT")
FLASK_DEBUG = os.getenv("FLASK_DEBUG") == "True"
SECRET_KEY = os.getenv("SECRET_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")