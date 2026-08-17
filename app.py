from flask import Flask, send_from_directory

import database
from config import SECRET_KEY, FLASK_HOST, FLASK_PORT, FLASK_DEBUG, PHOTO_FOLDER

app = Flask("VigilProctor")
app.secret_key = SECRET_KEY

# Add route to serve photos
@app.route('/photos/<path:filename>')
def serve_photo(filename):
    """Serve photos from the photos directory"""
    return send_from_directory(PHOTO_FOLDER, filename)

from routes.auth import *
from routes.exam import *
from routes.api import *
from routes.report import *
from routes.admin import *

if __name__ == "__main__":
    database.create_tables()
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG
    )