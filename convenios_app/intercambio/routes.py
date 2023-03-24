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

MESES = {
    "1": "enero",
    "2": "febrero",
    "3": "marzo",
    "4": "abril",
    "5": "mayo",
    "6": "junio",
    "7": "julio",
    "8": "agosto",
    "9": "septiembre",
    "10": "octubre",
    "11": "noviembre",
    "12": "diciembre"
}


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
                                                                        RecepcionConvenio.periodicidad == "Mensual",
                                                                        RecepcionConvenio.periodicidad.like(f"%{mes}%")))).all()

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

    recepciones = {}
    # Obtener todas las recepciones pendientes del mes (no se consideran las semanales o diarias)
    mes_actual_query = RecepcionesSFTP.query.filter(and_(RecepcionesSFTP.mes == mes_actual,
                                                          or_(RecepcionesSFTP.recibido == 0, and_(
                                                              RecepcionesSFTP.recibido == 1, RecepcionesSFTP.validado == 0
                                                          )))).all()
    for recepcion in mes_actual_query:
        try:
            recepciones[recepcion.recepcion.convenio.institucion.sigla]["mes_actual_sftp"].append(recepcion)
        except KeyError:
            recepciones[recepcion.recepcion.convenio.institucion.sigla] = {"mes_actual_sftp": [recepcion]}

    # Obtener todas las recepciones atrasadas de meses anteriores
    atrasadas_query = RecepcionesSFTP.query.filter(and_(RecepcionesSFTP.mes != mes_actual,
                                                    or_(RecepcionesSFTP.recibido == 0, and_(
                                                        RecepcionesSFTP.recibido == 1, RecepcionesSFTP.validado == 0
                                                    )))).all()
    for recepcion in atrasadas_query:
        try:
            recepciones[recepcion.recepcion.convenio.institucion.sigla]["atrasadas_sftp"].append(recepcion)
        except KeyError:
            try:
                recepciones[recepcion.recepcion.convenio.institucion.sigla]["atrasadas_sftp"] = [recepcion]
            except KeyError:
                recepciones[recepcion.recepcion.convenio.institucion.sigla] = {"atrasadas_sftp": [recepcion]}

    # Obtener otras recepciones que no son por SFTP
    otras_query = RecepcionConvenio.query.filter(and_(RecepcionConvenio.estado == 1,
                                                      RecepcionConvenio.metodo != "SFTP",
                                                      or_(RecepcionConvenio.periodicidad == mes_actual,
                                                          RecepcionConvenio.periodicidad == "Mensual",
                                                          RecepcionConvenio.periodicidad.like(f"%{mes_actual}%")))).all()
    for recepcion in otras_query:
        try:
            recepciones[recepcion.convenio.institucion.sigla]["otras"].append(recepcion)
        except KeyError:
            try:
                recepciones[recepcion.convenio.institucion.sigla]["otras"] = [recepcion]
            except KeyError:
                recepciones[recepcion.convenio.institucion.sigla] = {"otras": [recepcion]}

    if not recepciones:
        flash("No hay recepciones pendientes", "warning")
        return redirect(url_for("intercambio.recepcion_sftp"))
    else:
        outlook = win32.Dispatch("outlook.application", pythoncom.CoInitialize())
        # Enviar correo por cada institución con las recepciones del mes y atrasadas
        saludo_AIET = \
            f"""Estimados,<br><br>
            Les envío la lista completa de archivos pendientes y observados.<br><br>"""
        despedida_AIET = "Saludos."
        mes_actual_TODAS = \
            f"""<u>Envíos pendientes de {datetime.now().strftime('%B %Y')}</u><ul>"""
        HAY_mes_actual = False
        atrasadas_TODAS = \
            f"""<u>Envíos pendientes de meses anteriores</u><br><ul>"""
        HAY_atrasadas = False

        saludo_IE = \
            f"""Estimado/a,<br><br> Junto con saludar, envío este correo para recordarles las entregas de archivos 
            comprotemidas por Convenio de Intercambio de Información entre ambas instituciones.<br><br>"""
        despedida_IE = "Por favor, enviar correo a convenios@sii.cl notificando la entrada de archivos. Si la entrega " \
                       "de información es por <b>SFTP</b>, se solicita seguir las siguientes indicaciones:" \
                        "<ul><li>Copiar a sftp_sii@sii.cl en el correo de notificación.</li>" \
                        "<li><b>No incluir espacios, tildes u otros carácteres especiales en los nombres de los archivos.</b></li>" \
                        "<li><b>Especificar la ruta completa de los archivos dentro del SFTP para facilitar la extracción.</b></li></ul>" \
                        "Responder este correo en caso de dudas y/o consultas,<br>Saludos."

        for institucion, datos in recepciones.items():
            mes_actual_IE = \
            f"""<u>Envíos pendientes de {datetime.now().strftime('%B %Y')}</u><ul>"""
            atrasadas_IE = \
            f"""<u>Envíos pendientes de meses anteriores</u><br><ul>"""
            for tipo_recepcion, archivos in datos.items():
                if tipo_recepcion == "mes_actual_sftp":
                    HAY_mes_actual = True
                    for archivo in archivos:
                        item = f"<li>{ archivo.recepcion.archivo } ({ archivo.recepcion.metodo }"
                        if archivo.validado == 0:
                            item += f", <span style='color: red;'>observado:</span> { archivo.observacion })</li>"
                        else:
                            item += ")</li>"
                        mes_actual_TODAS += item[:4] + f'<b>{institucion}</b> ' + item[4:]
                        mes_actual_IE += item
                elif tipo_recepcion == "otras":
                    HAY_mes_actual = True
                    for archivo in archivos:
                        item = f"<li>{ archivo.archivo } ({ archivo.metodo })</li>"
                        mes_actual_TODAS += item[:4] + f'<b>{institucion}</b> ' + item[4:]
                        mes_actual_IE += item
                else:
                    HAY_atrasadas = True
                    for archivo in archivos:
                        item = f"<li>{ archivo.recepcion.archivo } ({ archivo.recepcion.metodo}, { MESES[str(archivo.mes)] }"
                        if archivo.validado == 0:
                            item += f", <span style='color: red;'>observado:</span> { archivo.observacion })</li>"
                        else:
                            item += ")</li>"
                        atrasadas_TODAS += item[:4] + f'<b>{institucion}</b> ' + item[4:]
                        atrasadas_IE += item
            # Cerrar listas
            mes_actual_IE += "</ul><br>"
            atrasadas_IE += "</ul><br>"
            # Generar mensaje IE
            mensaje_IE = saludo_IE
            if "mes_actual_sftp" in datos or "otras" in datos:
                mensaje_IE += mes_actual_IE
            if "atrasadas_sftp" in datos:
                mensaje_IE += atrasadas_IE
            mensaje_IE += despedida_IE
            # Enviar correo recepciones IE
            mail_IE = outlook.CreateItem(0)
            mail_IE.Subject = f'{institucion} archivos comprometidos {datetime.now().strftime("%B %Y")}'
            mail_IE.To = 'convenios@sii.cl'
            mail_IE.HTMLBody = mensaje_IE
            mail_IE.Send()

        # Cerrar listas
        mes_actual_TODAS += "</ul><br>"
        atrasadas_TODAS += "</ul><br>"

        # Generar mensaje para AIET
        mensaje_AIET = saludo_AIET
        if HAY_mes_actual:
            mensaje_AIET += mes_actual_TODAS
        if HAY_atrasadas:
            mensaje_AIET += atrasadas_TODAS
        mensaje_AIET += despedida_AIET
        # Enviar correo a AIET
        mail_AIET = outlook.CreateItem(0)
        mail_AIET.Subject = f"Recepciones {datetime.now().strftime('%B %Y')}"
        mail_AIET.To = "convenios@sii.cl"
        mail_AIET.HTMLBody = mensaje_AIET
        mail_AIET.Send()

    flash("Correos enviados exitosamente", "success")
    return redirect(url_for("intercambio.recepcion_sftp"))
