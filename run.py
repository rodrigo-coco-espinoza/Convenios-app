from convenios_app import create_app
from convenios_app import db

app = create_app()
db.create_all(app=create_app())

if __name__ == '__main__':
    # Escoger según ambiente
    app.run(debug=True)