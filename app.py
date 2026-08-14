from flask import Flask

import database
from config import SECRET_KEY, FLASK_HOST, FLASK_PORT, FLASK_DEBUG

app = Flask("VigilProctor")
app.secret_key = SECRET_KEY

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