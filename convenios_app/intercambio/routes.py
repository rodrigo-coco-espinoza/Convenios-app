from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify, make_response, \
    send_from_directory, current_app
from flask_login import current_user, login_required
from convenios_app.models import (Convenio, Institucion, SdInvolucrada, BitacoraAnalista, TrayectoriaEtapa,
                                  TrayectoriaEquipo,
                                  HitosConvenio, RecepcionConvenio, WSConvenio, EntregaConvenio, RecepcionesSFTP)
from convenios_app.users.utils import admin_only, analista_only
from convenios_app import db
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import dias_habiles, formato_periodicidad
from convenios_app.main.utils import generar_nombre_convenio, ID_EQUIPOS, COLORES_ETAPAS, COLORES_EQUIPOS
from convenios_app.informes.utils import obtener_etapa_actual_dias, obtener_equipos_actual_dias, adendum, \
    convenio_cuenta, por_firmar, otros

from datetime import datetime, date
import locale

from pprint import pprint
from math import ceil, floor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

locale.setlocale(locale.LC_TIME, "es_CL")

intercambio = Blueprint('intercambio', __name__)


@intercambio.route('/recepcion_sftp', methods=['GET', 'POST'])
@login_required
@analista_only
def recepcion_sftp():
    # Obtener las recepciones pendientes
    recepciones_query = RecepcionesSFTP.query.filter(RecepcionesSFTP.recibido == 0).all()
    recepciones_data = [
        {
            "recepcion_id": recepcion.id,
            "institucion": recepcion.recepcion.convenio.institucion.sigla,
            "titulo": recepcion.recepcion.nombre,
            "archivo": recepcion.recepcion.archivo,
            "fecha": f"{datetime.strptime(str(recepcion.mes), '%m').strftime('%B')}/{recepcion.ano}",
        }
        for recepcion in recepciones_query]

    # Obtener los archivos pendientes de validación
    informacion_por_validar_query = RecepcionesSFTP.query.filter(and_(RecepcionesSFTP.recibido == 1, RecepcionesSFTP.validado == None)).all()
    informacion_por_validar = [
        {
            "institucion": archivo.recepcion.convenio.institucion.sigla,
            "titulo": archivo.recepcion.nombre,
            "archivo": archivo.recepcion.archivo,
            "fecha": f"{datetime.strptime(str(archivo.mes), '%m').strftime('%B')}/{archivo.ano}",
            "revisa": archivo.recepcion.sd.sigla
        }
        for archivo in informacion_por_validar_query]

    # Obtener archivos observados
    informacion_observada_query = RecepcionesSFTP.query.filter(and_(RecepcionesSFTP.recibido == 1, RecepcionesSFTP.validado == 0)).all()
    informacion_observada = [
        {
            "institucion": archivo.recepcion.convenio.institucion.sigla,
            "titulo": archivo.recepcion.nombre,
            "archivo": archivo.recepcion.archivo,
            "fecha": f"{datetime.strptime(str(archivo.mes), '%m').strftime('%B')}/{archivo.ano}",
            "observacion": f"{archivo.recepcion.sd.sigla}: {archivo.observacion}"
        }
        for archivo in informacion_observada_query]

    if request.method == "POST":
        archivos_recibidos = request.form.getlist("recibido_checkbox")
        for archivo in archivos_recibidos:
            recepcion_por_editar = RecepcionesSFTP.query.get(archivo)
            recepcion_por_editar.recibido = 1
            recepcion_por_editar.id_autor_recibido = current_user.id
            recepcion_por_editar.timestamp_recibido = datetime.today()
        db.session.commit()

        #TODO: ENVIAR CORREO A SUBDIRECCIONES PARA QUE REVISEN LA INFORMACIÓN

        return redirect(url_for("intercambio.recepcion_sftp"))

    return render_template("intercambio/recepcion_sftp.html", recepciones_data=recepciones_data,
                           informacion_por_validar=informacion_por_validar, informacion_observada=informacion_observada)


@intercambio.route('/generar_recepciones_sftp_mes', methods=['GET', 'POST'])
@login_required
@analista_only
def generar_recepciones_sftp_mes():
    mes = request.form.get("mesSelect")
    año = date.today().year
    # Verificar que las recepciones no hayan sido generadas
    if RecepcionesSFTP.query.filter(and_(RecepcionesSFTP.ano == año, RecepcionesSFTP.mes == mes)).first():
        flash(f"Ya se han generado las recepciones por SFTP de {datetime.strptime(mes, '%m').strftime('%B')}/{año}",
              "warning")
        return redirect(url_for("intercambio.recepcion_sftp"))
    else:
        # Obtener todas las recepciones activas del mes
        recepciones_query = RecepcionConvenio.query.filter(and_(RecepcionConvenio.metodo == "SFTP",
                                                                RecepcionConvenio.estado == 1,
                                                                or_(RecepcionConvenio.periodicidad == mes,
                                                                    RecepcionConvenio.periodicidad == "Mensual"))).all()

        # Agregar a la base de datos
        for recepcion in recepciones_query:
            nueva_recepcion = RecepcionesSFTP(
                id_recepcion=recepcion.id,
                ano=año,
                mes=mes,
                recibido=0
            )
            db.session.add(nueva_recepcion)
        db.session.commit()

        flash(
            f"Se han generado correctametne las recepciones por SFTP de {datetime.strptime(mes, '%m').strftime('%B')}/{año}",
            "success")
        return redirect(url_for("intercambio.recepcion_sftp"))
