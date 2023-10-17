from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify, make_response, \
    send_from_directory, current_app
from flask_login import current_user, login_required
from convenios_app.models import (Convenio, Institucion, SdInvolucrada, BitacoraAnalista, TrayectoriaEtapa,
                                  TrayectoriaEquipo,
                                  HitosConvenio, RecepcionConvenio, WSConvenio, EntregaConvenio, RecepcionesSFTP, RegistroEntregas)
from convenios_app.users.utils import admin_only, analista_only
from convenios_app import db
from sqlalchemy import and_, or_
from convenios_app.intercambio.forms import ValidadorForm
from convenios_app.intercambio.utils import Archivo, separar_periodicidad
from convenios_app.bitacoras.utils import dias_habiles, formato_periodicidad, SHAREPOINT_SITE, SHAREPOINT_DOC, obtener_iniciales
from convenios_app.main.utils import generar_nombre_convenio, ID_EQUIPOS, COLORES_ETAPAS, COLORES_EQUIPOS
from convenios_app.informes.utils import obtener_etapa_actual_dias, obtener_equipos_actual_dias, adendum, \
    convenio_cuenta, por_firmar, otros

from datetime import datetime, date
import locale
from itertools import groupby
import win32com.client as win32
import pythoncom
from copy import deepcopy

from pprint import pprint

MESES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre"
}


locale.setlocale(locale.LC_TIME, "es_CL")

intercambio = Blueprint('intercambio', __name__)


@intercambio.route('/recepcion_sftp', methods=['GET', 'POST'])
def recepcion_sftp():
    # Obtener todas las recepciones de los últimos 3 años
    inicio_periodo = datetime.now().year - 2
    recepciones_query = RecepcionesSFTP.query.filter(RecepcionesSFTP.ano >= inicio_periodo).all()

    # Crear la estructura de los datos
    data_structure = {
        'pendientes': [],
        'por_validar': [],
        'observados': [],
        'validados': []
    }
    

    recepciones_data = {str(ano): {str(mes.capitalize()): {}  for mes in MESES.values() } for ano in range(inicio_periodo, datetime.now().year + 1) }

    # Llenar con los datos
    for recepcion in recepciones_query:
        # Datos para llenar el diccionario
        id_recepcion = recepcion.id
        institucion = recepcion.recepcion.convenio.institucion.sigla
        archivo = recepcion.recepcion.archivo
        ano_recepcion = str(recepcion.ano)
        mes_recepcion = str(MESES[recepcion.mes].capitalize())
        titulo = recepcion.recepcion.nombre
        link = f"{SHAREPOINT_SITE}/{SHAREPOINT_DOC}/{institucion}"
        fecha = f"{datetime.strptime(str(recepcion.mes), '%m').strftime('%B')}/{recepcion.ano}"
        sd_revisa = recepcion.recepcion.sd.sigla

        if recepcion.validado == 1: 
            # Agregar si ya existe la institución
            try:
                recepciones_data[ano_recepcion][mes_recepcion][institucion]["validados"].append({
                    "id": id_recepcion,
                    "institucion": institucion,
                    "titulo": titulo,
                    "archivo": archivo,
                    "link": link,
                    "fecha": fecha
                })
            # Añadir institución y agregar recepción
            except KeyError:
                 recepciones_data[ano_recepcion][mes_recepcion][institucion] = deepcopy(data_structure)
                 recepciones_data[ano_recepcion][mes_recepcion][institucion]["validados"].append({
                    "id": id_recepcion,
                    "institucion": institucion,
                    "titulo": titulo,
                    "archivo": archivo,
                    "link": link,
                    "fecha": fecha
                })
                                 
        elif recepcion.recibido == 0 and recepcion.validado == None:
            try:
                recepciones_data[ano_recepcion][mes_recepcion][institucion]["pendientes"].append({
                    "id": id_recepcion,
                    "institucion": institucion,
                    "titulo": titulo,
                    "archivo": archivo,
                    "link": link,
                    "fecha": fecha,
                })
            except KeyError:
                recepciones_data[ano_recepcion][mes_recepcion][institucion] = deepcopy(data_structure)
                recepciones_data[ano_recepcion][mes_recepcion][institucion]["pendientes"].append({
                    "id": id_recepcion,
                    "institucion": institucion,
                    "titulo": titulo,
                    "archivo": archivo,
                    "link": link,
                    "fecha": fecha,
                })

        elif recepcion.recibido == 1 and recepcion.validado == None:
            try:
                recepciones_data[ano_recepcion][mes_recepcion][institucion]["por_validar"].append({
                    "id": id_recepcion,
                    "institucion": institucion,
                    "titulo": titulo,
                    "archivo": archivo,
                    "link": link,
                    "fecha": fecha,
                    "revisa": sd_revisa
                    })
            except KeyError:
                recepciones_data[ano_recepcion][mes_recepcion][institucion] = deepcopy(data_structure)
                recepciones_data[ano_recepcion][mes_recepcion][institucion]["por_validar"].append({
                    "id": id_recepcion,
                    "institucion": institucion,
                    "titulo": titulo,
                    "archivo": archivo,
                    "link": link,
                    "fecha": fecha,
                    "revisa": sd_revisa
                    })
                
        elif recepcion.recibido == 1 and recepcion.validado == 0:
            try:        
                recepciones_data[ano_recepcion][mes_recepcion][institucion]["observados"].append({
                    "id": id_recepcion,
                    "institucion": institucion,
                    "titulo": titulo,
                    "archivo": archivo,
                    "link": link,
                    "fecha": fecha,
                    "observacion": f"{recepcion.recepcion.sd.sigla}: {recepcion.observacion}"              
                })
            except KeyError:
                recepciones_data[ano_recepcion][mes_recepcion][institucion] = deepcopy(data_structure)
                recepciones_data[ano_recepcion][mes_recepcion][institucion]["observados"].append({
                    "id": id_recepcion,
                    "institucion": institucion,
                    "titulo": titulo,
                    "archivo": archivo,
                    "link": link,
                    "fecha": fecha,
                    "observacion": f"{recepcion.recepcion.sd.sigla}: {recepcion.observacion}"              
                })

    if request.method == "POST":
        # Enviar archivos a validación
        if "pendientes" in request.form:
            archivos_recibidos = request.form.getlist("recibido_checkbox")
            for archivo in archivos_recibidos:
                recepcion_por_editar = RecepcionesSFTP.query.get(archivo)
                recepcion_por_editar.recibido = 1
                recepcion_por_editar.id_autor_recibido = current_user.id
                recepcion_por_editar.timestamp_recibido = datetime.today()
            db.session.commit()
            flash("Archivos actualizados correctamente", "success")
            #TODO: ENVIAR CORREO A SUBDIRECCIONES PARA QUE REVISEN LA INFORMACIÓN
        
        # Aprobar archivos
        if "aprobar" in request.form:
            archivos_aprobados = request.form.getlist("aprobado_checkbox")
            for archivo in archivos_aprobados:
                archivo_por_aprobar = RecepcionesSFTP.query.get(archivo)
                archivo_por_aprobar.validado = 1
                archivo_por_aprobar.id_autor_validado = current_user.id
                archivo_por_aprobar.timestamp_validado = datetime.today()
            db.session.commit()
            flash("Archivos actualizados correctamente", "success")

        return redirect(url_for("intercambio.recepcion_sftp"))
    return render_template("intercambio/recepcion_sftp.html", data_recepciones=recepciones_data)



@intercambio.route('/observar_archivo/<int:id_archivo>')
@login_required
def observar_archivo(id_archivo):
    archivo_por_observar = RecepcionesSFTP.query.get(id_archivo)
    archivo_por_observar.validado = 0
    db.session.commit()
    flash("Archivo actualizado correctamente", "success")
    return redirect(url_for("intercambio.recepcion_sftp"))    

@intercambio.route("/recibir_corregido/<int:id_archivo>")
@login_required
@analista_only
def recibir_corregido(id_archivo):
    archivo_corregido = RecepcionesSFTP.query.get(id_archivo)
    archivo_corregido.validado = None
    archivo_corregido.recibido = 1
    db.session.commit()
    flash("Archivo actualizado correctamente", "success")
    return redirect(url_for("intercambio.recepcion_sftp"))



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


@intercambio.route("/entregas_ge", methods=["GET", "POST"])
def entregas_ge():
    # ENTREGAS PENDIENTES POR GE
    # Obtener los años registados en la base de datos
    entregas_pendientes = {
        "enero": [],
        "febrero": [],
        "marzo": [],
        "abril": [],
        "mayo": [],
        "junio": [],
        "julio": [],
        "agosto": [],
        "septiembre": [],
        "octubre": [],
        "noviembre": [],
        "diciembre": []
    }

    entregas_pendientes_query = RegistroEntregas.query.filter(and_(RegistroEntregas.entregado == 0, RegistroEntregas.gabinete == None)).all()
    
    # Completar datos con entregas pendientes
    for entrega in entregas_pendientes_query: 
        # Cambiar por match con python 3.10
        if entrega.mes == 1:
            entregas_pendientes["enero"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 2:
            entregas_pendientes["febrero"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 3:
            entregas_pendientes["marzo"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 4:
            entregas_pendientes["abril"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 5:
            entregas_pendientes["mayo"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 6:
            entregas_pendientes["junio"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 7:
            entregas_pendientes["julio"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 8:
            entregas_pendientes["agosto"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 9:
            entregas_pendientes["septiembre"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 10:
            entregas_pendientes["octubre"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 11:
            entregas_pendientes["noviembre"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                })
        elif entrega.mes == 12:
            entregas_pendientes["diciembre"].append(
                {"id_entrega": entrega.id,
                 "institucion": entrega.entrega.convenio.institucion.sigla,
                 "ano": entrega.ano,
                 "link_resolucion":  entrega.entrega.convenio.link_resolucion,
                 "nombre": entrega.entrega.nombre,
                 "archivo": entrega.entrega.archivo,
                 "nomina": "C/Nom" if entrega.entrega.id_nomina else "S/Nom",
                "encargado": obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre),
                "link_pt": entrega.entrega.convenio.institucion.link_protocolo
                }) 
    
    # Ordenar entregas
    for mes, datos in entregas_pendientes.items():
        datos.sort(key=lambda x: x["institucion"])

    # Asignar entregas a GE
    if request.method == "POST":
        numero_ge = next((item for item in request.form.getlist("numero_ge") if item != ""), None)
        entregas = request.form.getlist("entrega_asignada")

        # Comprobar que las entregas pertenzcan a una sola institución
        if db.session.query(Convenio.id_institucion).join(EntregaConvenio).join(RegistroEntregas).filter(RegistroEntregas.id.in_(entregas)).distinct().count() > 1:
            
            flash("No se ha asignado el GE: ha seleccionado archivos de diferentes instituciones", "danger")
            return redirect(url_for("intercambio.entregas_ge"))

        # Si se agrega una entrega a un GE existente, comprobar que sea de la misma institución
        ge_generado = RegistroEntregas.query.filter(RegistroEntregas.gabinete == numero_ge).first()
        if ge_generado:
            for entrega in entregas:
                entrega_a_comprobar = RegistroEntregas.query.get(entrega)
                if entrega_a_comprobar.entrega.convenio.id_institucion != ge_generado.entrega.convenio.id_institucion:
                    flash("No se ha asigando el GE. Ha seleccionado un archivo pertenenciente a otra institución", "danger")
                    return redirect(url_for("intercambio.entregas_ge"))


        # Asignar GE a las entregas
        for entrega in entregas:
            asignar_ge = RegistroEntregas.query.get(entrega)
            asignar_ge.gabinete = numero_ge
        
        db.session.commit()
        flash(f"Se han asignado {len(entregas)} archivos al Gabinete Electrónico {numero_ge}", "success")
        return redirect(url_for("intercambio.entregas_ge"))
    
    # GABINETES ELECTRÓNICOS ABIERTOS
    # Obtener gabinetes electrónicos abiertos
    ge_query = db.session.query(RegistroEntregas.gabinete).filter(and_(RegistroEntregas.entregado == 0, RegistroEntregas.gabinete != None)).distinct().all()
    
    # Diccionario con los ge y sus archivos
    ge_abiertos = {nro_ge[0]: {"archivos": []} for nro_ge in ge_query}

    # Obtener todas las entregas que tengan un GE asignado
    entregas_con_ge_query = RegistroEntregas.query.filter(and_(RegistroEntregas.entregado == 0, RegistroEntregas.gabinete != None)).all()

    for entrega in entregas_con_ge_query:
        # Agregar institución
        if "institucion" not in ge_abiertos[entrega.gabinete]:
            ge_abiertos[entrega.gabinete]["institucion"] = entrega.entrega.convenio.institucion.sigla
        # Agregar encargado
        if "encargado" not in ge_abiertos[entrega.gabinete]:
            ge_abiertos[entrega.gabinete]["encargado"] = obtener_iniciales(entrega.entrega.convenio.coord_sii.nombre)
        # Agregar link PT
        if "link_sharepoint" not in ge_abiertos[entrega.gabinete]:
            ge_abiertos[entrega.gabinete]["link_sharepoint"] = f"{SHAREPOINT_SITE}/{SHAREPOINT_DOC}/{entrega.entrega.convenio.institucion.sigla}"
        
        # Agregar datos de la entrega
        ge_abiertos[entrega.gabinete]["archivos"].append({
            "id_archivo": entrega.id,
            "nombre_entrega": entrega.entrega.nombre,
            "nombre_archivo": entrega.entrega.archivo,
            "mes_entrega": f"{MESES[entrega.mes]}/{entrega.ano}"
            })



    return render_template("intercambio/entregas_ge.html", entregas_ge=entregas_pendientes, ge_abiertos=ge_abiertos)


@intercambio.route("/eliminar_entrega_ge/<int:id_entrega>")
def eliminar_entrega_ge(id_entrega):
    # Buscar entrega en la BBDD y eliminar el número de GE

    entrega = RegistroEntregas.query.get(id_entrega)
    flash(f"Se ha eliminado la entrega '{entrega.entrega.archivo}' del gabinete {entrega.gabinete}", "success")
    entrega.gabinete = None
    db.session.commit()

    return redirect(url_for("intercambio.entregas_ge"))

@intercambio.route("/entregar_ge/<string:nro_ge>")
def entregar_ge(nro_ge):
    # Buscar entregas asignadas al GE y cambiar estado a enviado
    entregas = RegistroEntregas.query.filter(RegistroEntregas.gabinete == nro_ge).all()

    for entrega in entregas:
        entrega.entregado = 1
    db.session.commit()

    flash(f"Se han enviado {len(entregas)} archivos en el gabinete {nro_ge}", "success")
    return redirect(url_for("intercambio.entregas_ge"))


@intercambio.route("/generar_entregas_ge", methods=["POST"]) 
def generar_entregas_ge():
    año = date.today().year
    mes = request.form.get("mesSelect")
    if mes == '0':
        # Extraer entregas por generar
        periodicidades_excluidas = ["A pedido", "Diario", "Semanal", "Ocurrencia"]

        entregas_generadas = [entrega.id_entrega for entrega in RegistroEntregas.query.filter(RegistroEntregas.ano == año).all()]
        entregas_por_generar = EntregaConvenio.query.filter(and_(EntregaConvenio.estado == 1, EntregaConvenio.metodo == "Gabiente Electrónico", EntregaConvenio.id.not_in(entregas_generadas), EntregaConvenio.periodicidad.not_in(periodicidades_excluidas))).all()

        num_entregas = 0

        # Generar entregas de todo el año
        for entrega in entregas_por_generar:
            if entrega.periodicidad == "Mensual":
                for i in range(1, 13):
                    nueva_entrega = RegistroEntregas(
                        id_entrega=entrega.id,
                        ano=año,
                        mes=i
                    )
                    num_entregas += 1
                    db.session.add(nueva_entrega)
            else:
                meses_por_agregar = separar_periodicidad(entrega.periodicidad)
                for m in meses_por_agregar:
                    nueva_entrega = RegistroEntregas(
                        id_entrega=entrega.id,
                        ano=año,
                        mes=m
                    )
                    num_entregas += 1
                    db.session.add(nueva_entrega)
        
        if num_entregas > 0:
            flash(f"Se han generado {num_entregas} nuevas entregas.", "success")
        else:
            flash(f"No hay entregas nuevas por generar", "warning")

    else:
        # Generar entregas del mes
        entregas_generadas = [entrega.id_entrega for entrega in RegistroEntregas.query.filter(and_(RegistroEntregas.mes == mes, RegistroEntregas.ano == año)).all()]
        if mes == "1":
            # Restricciones especiales para enero
            entregas_por_generar = EntregaConvenio.query.filter(and_(EntregaConvenio.estado == 1, EntregaConvenio.metodo == "Gabiente Electrónico", EntregaConvenio.id.not_in(entregas_generadas), or_(EntregaConvenio.periodicidad == "Mensual", EntregaConvenio.periodicidad == "1", and_(EntregaConvenio.periodicidad.contains("1-"), ~EntregaConvenio.periodicidad.contains("11"))))).all()
        elif mes == "2": 
            # Restricciones especiales para febrero
            entregas_por_generar = EntregaConvenio.query.filter(and_(EntregaConvenio.estado == 1,
                                                         EntregaConvenio.metodo == "Gabiente Electrónico", or_(EntregaConvenio.periodicidad == "2", EntregaConvenio.periodicidad.contains("-2"), EntregaConvenio.periodicidad.contains("2-"), EntregaConvenio.periodicidad == "Mensual"), EntregaConvenio.id.not_in(entregas_generadas))).all()
            
        else:
            entregas_por_generar = EntregaConvenio.query.filter(and_(EntregaConvenio.estado == 1, EntregaConvenio.metodo == "Gabiente Electrónico", or_(EntregaConvenio.periodicidad.contains(mes), EntregaConvenio.periodicidad == "Mensual"), EntregaConvenio.id.not_in(entregas_generadas))).all()

        # Generar las entregas en la BD
        for entrega in entregas_por_generar:
            nueva_entrega = RegistroEntregas(
                id_entrega=entrega.id,
                ano=año,
                mes=mes             
            )
            db.session.add(nueva_entrega)
        if len(entregas_por_generar) > 0:
            flash(f"Se han generado {len(entregas_por_generar)} nuevas entregas.", "success")
        else:
            flash(f"No hay entregas nuevas por generar", "warning")
    
    db.session.commit()
   
    return redirect(url_for("intercambio.entregas_ge"))

# @intercambio.route("/entregas_ge")
# def entregas_ge():
#     entregas_ge = {
#         "enero": [],
#         "febrero": [],
#         "marzo": [],
#         "abril": [],
#         "mayo": [],
#         "junio": [],
#         "julio": [],
#         "agosto": [],
#         "septiembre": [],
#         "octubre": [],
#         "noviembre": [],
#         "diciembre": []
#     }
#     entregas_ge_query = EntregaConvenio.query.filter(and_(EntregaConvenio.estado == 1,
#                                                           EntregaConvenio.metodo == "Gabiente Electrónico")).all()
#     for entrega in entregas_ge_query:
#         periodicidad = entrega.periodicidad.split("-")
#         if "1" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["enero"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "encargado": entrega.convenio.coordinador_sii
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "2" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["febrero"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "3" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["marzo"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "4" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["abril"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "5" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["mayo"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "6" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["junio"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "7" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["julio"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "8" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["agosto"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "9" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["septiembre"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "10" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["octubre"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "11" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["noviembre"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })
#         if "12" in periodicidad or "Mensual" in periodicidad:
#             entregas_ge["diciembre"].append({
#                 "institucion": entrega.convenio.institucion.sigla,
#                 "convenio": entrega.convenio.nombre if entrega.convenio.tipo == "Convenio" else f"(Ad) {entrega.convenio.nombre}",
#                 "link_convenio": entrega.convenio.link_resolucion,
#                 "entrega": entrega.nombre,
#                 "archivo": entrega.archivo,
#                 "nomina": "Requiere nómina" if entrega.id_nomina else "Sin nómina",
#                 "link_pt": entrega.convenio.institucion.link_protocolo
#             })

#     # Ordenar tablas
#     entregas_ge["enero"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["febrero"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["marzo"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["abril"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["mayo"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["junio"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["julio"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["agosto"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["septiembre"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["octubre"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["noviembre"].sort(key=lambda dict: dict["institucion"])
#     entregas_ge["diciembre"].sort(key=lambda dict: dict["institucion"])
#     return render_template("intercambio/entregas_ge.html", entregas_ge=entregas_ge)


@intercambio.route("/validador", methods=["GET", "POST"])
def validador():

    validador_form = ValidadorForm()

    if validador_form.validate_on_submit():
        nombre_archivo = validador_form.archivo.data.filename
        archivo_subido = request.files[validador_form.archivo.name]
        archivo = Archivo(nombre_archivo, archivo_subido, validador_form.separador.data)
        validacion_data = {
                "nombreArchivo": nombre_archivo,
                "rutPorTramos": archivo.rut_por_tramos(),
                "validacionArchivo": archivo.validacion_archivo(),
        }
        return render_template("intercambio/validador_resultados.html", validacion_data=validacion_data)

    return render_template("intercambio/validador.html", validador_form=validador_form)
