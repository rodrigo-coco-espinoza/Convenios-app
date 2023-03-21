from convenios_app import create_app
from convenios_app import db
from dotenv import load_dotenv
import os
from tkinter import Tk


app = create_app()
db.create_all(app=create_app())

load_dotenv()

if __name__ == '__main__':
    Tk().withdraw()
    # Escoger según ambiente
    app.run(host='10.36.1.91', port=8000, debug=True)
