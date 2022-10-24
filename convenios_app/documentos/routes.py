from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify, send_from_directory
from flask_login import current_user, login_required
from convenios_app.users.utils import admin_only, analista_only
from convenios_app.models import (Institucion, Equipo, Persona, Convenio, SdInvolucrada, BitacoraAnalista,
                                  BitacoraTarea, TrayectoriaEtapa, TrayectoriaEquipo, CatalogoWS, WSConvenio,
                                  RecepcionConvenio, Hito, HitosConvenio)
from convenios_app.bitacoras.forms import (NuevoConvenioForm, EditarConvenioForm, NuevaBitacoraAnalistaForm,
                                           NuevaTareaForm, InfoConvenioForm, ETAPAS, AgregarRecepcionForm,
                                           RegistrarHitoForm, EditarRecepcionForm)
from convenios_app import db
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import (actualizar_trayectoria_equipo, actualizar_convenio, obtener_iniciales,
                                           dias_habiles, formato_periodicidad)
from convenios_app.main.utils import generar_nombre_institucion, generar_nombre_convenio, formato_nombre
from datetime import datetime, date

documentos = Blueprint('documentos', __name__)


@documentos.route('/proceso_de_convenio')
def proceso_de_convenio():
    return render_template('documentos/proceso_de_convenio.html')

@documentos.route('/files/<documento>')
def files(documento):
    return send_from_directory(directory='static/files', path=documento)
    
@documentos.route('/catalogo_ws')
def catalogo_ws():
    return 'catalogo'