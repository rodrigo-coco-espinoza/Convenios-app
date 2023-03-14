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
from itertools import groupby
import win32com.client as win32
import pythoncom

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
    if "generarRecepciones" in request.form:
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

    elif "enviarCorreos" in request.form:
        return redirect(url_for("intercambio.enviar_correos_ie"))

@intercambio.route('/enviar_correos_ie')
@login_required
@analista_only
def enviar_correos_ie():

    locale.setlocale(locale.LC_TIME, "es_CL")

    mes_actual = datetime.now().month
    # Obtener todas las recepciones pendientes del mes (no se consideran las semanales o diarias)
    recepciones_query = RecepcionesSFTP.query.filter(and_(RecepcionesSFTP.mes == mes_actual,
                                                          or_(RecepcionesSFTP.recibido == 0, and_(
                                                              RecepcionesSFTP.recibido == 1, RecepcionesSFTP.validado == 0
                                                          )))).all()
    # Obtener todas las recepciones atrasadas de meses anteriores
    atrasadas_query = RecepcionesSFTP.query.filter(and_(RecepcionesSFTP.mes != mes_actual,
                                                    or_(RecepcionesSFTP.recibido == 0, and_(
                                                        RecepcionesSFTP.recibido == 1, RecepcionesSFTP.validado == 0
                                                    )))).all()

    # Obtener otras recepciones que no son por SFTP
    otras_query = RecepcionConvenio.query.filter(and_(RecepcionConvenio.estado == 1, or_(
        RecepcionConvenio.periodicidad == mes_actual, RecepcionConvenio.periodicidad == "Mensual"
    ))).all()

    # Agrupar todas las recepciones en una variable
    recepciones = {}
    for recepcion in recepciones_query:
        try:
            recepciones[recepcion.recepcion.convenio.institucion.sigla]["recepciones_sftp"].append(recepcion)
        except KeyError:
            recepciones[recepcion.recepcion.convenio.institucion.sigla] = {"recepciones_sftp": [recepcion]}
    for recepcion in atrasadas_query:
        try:
            recepciones[recepcion.recepcion.convenio.institucion.sigla]["atrasadas_sftp"].append(recepcion)
        except KeyError:
            try:
                recepciones[recepcion.recepcion.convenio.institucion.sigla]["atrasadas_sftp"] = [recepcion]
            except KeyError:
                recepciones[recepcion.recepcion.convenio.institucion.sigla] = {"atrasadas_sftp": [recepcion]}
    pprint(recepciones)
    #     "IPS": {
    #         "recepciones_sftp": [1,2,3],
    #         "atrasadas_sftp": [1,2,3],
    #         "otras": [1,2,3]
    #     }
    # }

    if not recepciones_query and not atrasadas_query and not otras_query:
        flash("No hay recepciones pendientes", "warning")
        return redirect(url_for("intercambio.recepcion_sftp"))
    else:
        # Enviar correo por cada institución con las recepciones del mes y atrasadas
        mensaje_aiet = f"""
Estimados, <br><br>Junto con saludar, les envío las recepciones de este mes y las atrasadas.<br><br>"""
        outlook = win32.Dispatch("outlook.application", pythoncom.CoInitialize())

        for recepcion in recepciones_query:
            pass
            # if recepcion.validado == 0:
            #     print("Observado", recepcion.recepcion.nombre)
            # else:
            #     print("pendiente", recepcion.recepcion.nombre)

    #     # Enviar correo a cada institución con las recepciones del mes
    #     mensaje_aiet = f"""
    #         Estimados,<br><br>
    #         Junto con saludar, les envío las recepciones de este mes.<br><br>
    #         """
    #
    #     outlook = win32.Dispatch('outlook.application', pythoncom.CoInitialize())
    #     for institucion, recepciones in groupby(recepciones_query, lambda x: x.convenio.institucion):
    #         mail = outlook.CreateItem(0)
    #         mail.Subject = f'{institucion.sigla} archivos comprometidos {datetime.now().strftime("%B %Y")}'
    #         mail.To = 'convenios@sii.cl'
    #         mail.HTMLBody = f"""
    #         Estimados, <br><br>
    #         Junto con saludar, envío este correo para recordarles los archivos comprometidos por Convenio de Intercambio de Información entre ambas
    #         instituciones. Los archivos que deben enviar son: <br><br>
    #         <ul>
    #         """
    #
    #         mensaje_aiet += f"<b>{institucion.sigla}</b>"
    #
    #         for recepcion in recepciones:
    #             mail.HTMLBody += f'<li>{recepcion.archivo} ({recepcion.metodo})</li>'
    #
    #             mensaje_aiet += f"<li>{recepcion.archivo} ({recepcion.metodo} / {recepcion.sd.sigla})</li>"
    #
    #         mail.HTMLBody += '''</ul><br>Por favor, enviar correo a convenios@sii.cl notificando la entrega de archivos. Si la entrega de información es por SFTP, se solicita seguir las siguientes indicaciones:
    #         <ul><li>Copiar a sftp_sii@sii.cl en el correo de notificación</li><li>No incluir espacios, tildes u otros caracteres especiales en los nombres de los archivos</li><li>Especificar la ruta completa de los archivos dentro del SFTP para facilita la extracción</li></ul><br>Dudas a convenios@sii.cl.<br><br>Saludos.'''
    #         mail.Send()
    #
    #         mensaje_aiet += """</ul><br>"""
    #
    #     mensaje_aiet += "<br>Saludos."
    #     # Enviar correo a AIET con todas las recepciones del mes
    #     mail_aiet = outlook.CreateItem(0)
    #     mail_aiet.Subject = f"Recepciones {datetime.now().strftime('%B %Y')}"
    #     mail_aiet.To = "convenios@sii.cl"
    #     mail_aiet.HTMLBody = mensaje_aiet
    #     mail_aiet.Send()
    #
    #     return "Correos enviados correctamente."
    #
    # flash("Correos enviados exitosamente", "success")
    return redirect(url_for("intercambio.recepcion_sftp"))
