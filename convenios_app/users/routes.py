from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify
from convenios_app.models import (Institucion, Equipo, Persona, Convenio, SdInvolucrada, BitacoraAnalista,
                                  BitacoraTarea, TrayectoriaEtapa, TrayectoriaEquipo, User)
from convenios_app.users.forms import RegistrationForm, LoginForm
from convenios_app import db, bcrypt
from convenios_app.users.utils import admin_only, analista_only
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import actualizar_trayectoria_equipo, actualizar_convenio, obtener_iniciales
from convenios_app.main.utils import generar_nombre_institucion, generar_nombre_convenio, formato_nombre
from datetime import datetime, date

users = Blueprint('users', __name__)


@users.route("/registrar_usuario", methods=['GET', 'POST'])
@login_required
@admin_only
def registrar_usuario():
    personas = [(persona.id, persona.nombre) for persona in Persona.query.filter(Persona.id_equipo != 2).order_by(Persona.nombre).all()]
    personas.insert(0, (0, 'Seleccione persona'))

    form = RegistrationForm()
    form.persona.choices = personas

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.user.data,
            password=hashed_password,
            permisos=form.tipo.data,
            id_persona=form.persona.data
        )
        db.session.add(user)
        db.session.commit()

        flash('Su cuenta ha sido creada. Ya puede iniciar sesión.', 'success')
        return redirect(url_for('users.ingresar'))

    return render_template('users/registrar_usuario.html', form=form)


@users.route('/ingresar', methods=['GET', 'POST'])
def ingresar():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(User.username == form.user.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f'Bienvenido {user.persona.nombre}', 'success')
            return redirect(url_for('main.home'))
        else:
            flash('Por favor compruebe su usuario y contraseña', 'danger')

    return render_template('users/ingresar.html', form=form)


@users.route('/salir')
@login_required
def salir():
    logout_user()
    return redirect(url_for('main.home'))