from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify, make_response, \
    send_from_directory, current_app
from flask_login import current_user, login_required
from convenios_app.models import (Institucion, Equipo, Persona, Convenio, SdInvolucrada, BitacoraAnalista,
                                  BitacoraTarea, TrayectoriaEtapa, TrayectoriaEquipo)
from convenios_app.informes.forms import MisConveniosInfoConvenioForm, MisConveniosBitacoraForm, MisConveniosTareaForm
from convenios_app import db
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import actualizar_trayectoria_equipo, actualizar_convenio, obtener_iniciales
from convenios_app.bitacoras.forms import ETAPAS
from convenios_app.users.utils import admin_only, analista_only
from convenios_app.main.utils import generar_nombre_convenio, ID_EQUIPOS, COLORES_ETAPAS, COLORES_EQUIPOS
from convenios_app.informes.utils import obtener_etapa_actual_dias, obtener_equipos_actual_dias

from datetime import datetime, date
from pprint import pprint
from math import ceil, floor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# import pdfkit
# path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
# config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

informes = Blueprint('informes', __name__)

# Variables estadísticas informes convenios en proceso y producción
diasxEtapa_proceso = {
    'Definición de Alcance del Convenio': {'suma': 0, 'cuenta': 0},
    'Confección de Documento de Convenio': {'suma': 0, 'cuenta': 0},
    'Gestión de Visto Bueno y Firmas': {'suma': 0, 'cuenta': 0},
    'Generación de Resolución y Protocolo Técnico': {'suma': 0, 'cuenta': 0},
}
diasxEquipos_suma_proceso = {
    'total': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                            'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Definición de Alcance del Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                         'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Confección de Documento de Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                          'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Gestión de Visto Bueno y Firmas': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                      'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Generación de Resolución y Protocolo Técnico': dict.fromkeys(
        ['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
         'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
}
diasxEquipos_cuenta_proceso = {
    'total': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                            'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Definición de Alcance del Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                         'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Confección de Documento de Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                          'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Gestión de Visto Bueno y Firmas': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                      'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Generación de Resolución y Protocolo Técnico': dict.fromkeys(
        ['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
         'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
}
tareasxEquipos_proceso = {
    'total': {},
    'Definición de Alcance del Convenio': {},
    'Confección de Documento de Convenio': {},
    'Gestión de Visto Bueno y Firmas': {},
    'Generación de Resolución y Protocolo Técnico': {}
}

diasxEtapa_produccion = {
    'Definición de Alcance del Convenio': {'suma': 0, 'cuenta': 0},
    'Confección de Documento de Convenio': {'suma': 0, 'cuenta': 0},
    'Gestión de Visto Bueno y Firmas': {'suma': 0, 'cuenta': 0},
    'Generación de Resolución y Protocolo Técnico': {'suma': 0, 'cuenta': 0},
}
diasxEquipos_suma_produccion = {
    'total': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                            'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Definición de Alcance del Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                         'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Confección de Documento de Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                          'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Gestión de Visto Bueno y Firmas': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                      'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Generación de Resolución y Protocolo Técnico': dict.fromkeys(
        ['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
         'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
}
diasxEquipos_cuenta_produccion = {
    'total': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                            'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Definición de Alcance del Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                         'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Confección de Documento de Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                          'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Gestión de Visto Bueno y Firmas': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                      'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    'Generación de Resolución y Protocolo Técnico': dict.fromkeys(
        ['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
         'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
}
tareasxEquipos_produccion = {
    'total': {},
    'Definición de Alcance del Convenio': {},
    'Confección de Documento de Convenio': {},
    'Gestión de Visto Bueno y Firmas': {},
    'Generación de Resolución y Protocolo Técnico': {}
}


def estadisticas_convenios():
    """
    Calcula las estadísticas para los informes de convenios en proceso y convenios en producción
    :return:
    """
    # Convenios en proceso
    global diasxEtapa_proceso
    global diasxEquipos_suma_proceso
    global diasxEquipos_cuenta_proceso
    global tareasxEquipos_proceso
    # Considerar solo los que hayan iniciado el proceso después del 01-01-2020 para las estadísticas
    convenios_query_2020 = [convenio for convenio in Convenio.query.filter(Convenio.estado == 'En proceso').all()
                            if TrayectoriaEtapa.query.filter(TrayectoriaEtapa.id_convenio == convenio.id).
                                order_by(TrayectoriaEtapa.ingreso.asc()).first().ingreso >= date(2020, 1, 1)]
    # Días por etapa
    # Sumar días en etapa de cada convenio
    for convenio in convenios_query_2020:
        # Días por etapa
        trayectoria_etapa_query = TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == convenio.id,
                                                                     TrayectoriaEtapa.id_etapa != 5)).all()
        # Contar los días en tapa y en equipo en cada etapa por convenio
        diasxEtapaConvenio = {
            'Definición de Alcance del Convenio': 0,
            'Confección de Documento de Convenio': 0,
            'Gestión de Visto Bueno y Firmas': 0,
            'Generación de Resolución y Protocolo Técnico': 0,
        }
        diasxEquipoEtapaConvenio = {
            'total': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                    'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
            'Definición de Alcance del Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                                 'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
            'Confección de Documento de Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                                  'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
            'Gestión de Visto Bueno y Firmas': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                              'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
            'Generación de Resolución y Protocolo Técnico': dict.fromkeys(
                ['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                 'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
        }

        cuentaxEquipoEtapaConvenio = {
            'total': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                    'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], False),
            'Definición de Alcance del Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                                 'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'],
                                                                False),
            'Confección de Documento de Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                                  'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'],
                                                                 False),
            'Gestión de Visto Bueno y Firmas': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                              'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], False),
            'Generación de Resolución y Protocolo Técnico': dict.fromkeys(
                ['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                 'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], False)
        }
        tareasxEquipoEtapaConvenio = {
            'Definición de Alcance del Convenio': {},
            'Confección de Documento de Convenio': {},
            'Gestión de Visto Bueno y Firmas': {},
            'Generación de Resolución y Protocolo Técnico': {}
        }

        for trayectoEtapa in trayectoria_etapa_query:
            # Fecha de salida de la etapa
            trayectoEtapaSalida = (lambda salida: salida if salida != None else date.today())(trayectoEtapa.salida)
            # Sumar días del trayecto a los días de la etapa del convenio
            diasxEtapaConvenio[trayectoEtapa.etapa.etapa] += (trayectoEtapaSalida - trayectoEtapa.ingreso).days

            # Obtener equipos de cada trayecto de etapa
            trayectoria_equipos_query = TrayectoriaEquipo.query.filter(
                and_(TrayectoriaEquipo.id_convenio == convenio.id,
                     and_(TrayectoriaEquipo.ingreso <= trayectoEtapaSalida,
                          or_(TrayectoriaEquipo.salida >= trayectoEtapa.ingreso,
                              TrayectoriaEquipo.salida == None)))).all()

            # Sumar días del trayecto a los días del equipo
            for trayectoEquipo in trayectoria_equipos_query:
                trayectoEquipoSalida = (lambda salida: salida if salida != None else date.today())(
                    trayectoEquipo.salida)
                sigla = (lambda sigla: 'SDGEET' if sigla == 'AIET' else sigla)(trayectoEquipo.equipo.sigla)

                # Marcar que el equipo tuvo el convenio en la etapa
                cuentaxEquipoEtapaConvenio[trayectoEtapa.etapa.etapa][sigla] = True

                trayectoEquipoIngreso = (
                    lambda ingreso: ingreso if ingreso >= trayectoEtapa.ingreso else trayectoEtapa.ingreso)(
                    trayectoEquipo.ingreso)
                trayectoEquipoSalida = (
                    lambda salida: salida if salida <= trayectoEtapaSalida else trayectoEtapaSalida)(
                    trayectoEquipoSalida)
                # Sumar los días
                diasxEquipoEtapaConvenio[trayectoEtapa.etapa.etapa][sigla] += (
                            trayectoEquipoSalida - trayectoEquipoIngreso).days

                # Contar tarea en el equipo y etapa correspondiente
                try:
                    tareasxEquipoEtapaConvenio[trayectoEtapa.etapa.etapa][sigla] += 1
                except KeyError:
                    tareasxEquipoEtapaConvenio[trayectoEtapa.etapa.etapa][sigla] = 1

        # Días total por equipo del convenio
        trayectoria_equipo_total_query = TrayectoriaEquipo.query.filter(
            TrayectoriaEquipo.id_convenio == convenio.id).all()
        tareasxEquipoTotalConvenio = {}
        for trayectoEquipoTotal in trayectoria_equipo_total_query:
            sigla = (lambda sigla: 'SDGEET' if sigla == 'AIET' else sigla)(trayectoEquipoTotal.equipo.sigla)
            trayectoEquipoTotalSalida = (lambda salida: salida if salida != None else date.today())(
                trayectoEquipoTotal.salida)
            cuentaxEquipoEtapaConvenio['total'][sigla] = True
            diasxEquipoEtapaConvenio['total'][sigla] += (trayectoEquipoTotalSalida - trayectoEquipoTotal.ingreso).days
            # Sumar tareas
            try:
                tareasxEquipoTotalConvenio[sigla] += 1
            except KeyError:
                tareasxEquipoTotalConvenio[sigla] = 1

        # Sumar días del convenio al total de etapas si el convenio estuvo en la etapa
        for (etapa, dias) in diasxEtapaConvenio.items():
            if dias > 0:
                diasxEtapa_proceso[etapa]['suma'] += dias
                diasxEtapa_proceso[etapa]['cuenta'] += 1

        # Sumar dias del convenio al total de equipos si el convenio estuvo en la etapa
        for (etapa, equipos) in diasxEquipoEtapaConvenio.items():
            for (equipo, dias) in equipos.items():
                # Sumar si el convenio pasó por el equipo (puede que sea con dias = 0)
                if cuentaxEquipoEtapaConvenio[etapa][equipo]:
                    diasxEquipos_suma_proceso[etapa][equipo] += dias
                    diasxEquipos_cuenta_proceso[etapa][equipo] += 1

        # Sumar tareas del convenio al total de tareas
        for equipo, tareas in tareasxEquipoTotalConvenio.items():
            try:
                tareasxEquipos_proceso['total'][equipo] += tareas
            except KeyError:
                tareasxEquipos_proceso['total'][equipo] = tareas
        for etapa, datos in tareasxEquipoEtapaConvenio.items():
            for equipo, tareas in datos.items():
                try:
                    tareasxEquipos_proceso[etapa][equipo] += tareas
                except KeyError:
                    tareasxEquipos_proceso[etapa][equipo] = tareas

    # Convenios en producción
    global diasxEtapa_produccion
    global diasxEquipos_suma_produccion
    global diasxEquipos_cuenta_produccion
    global tareasxEquipos_produccion
    # Días convenio (considerar solo los que hayan iniciado el proceso después del 01-01-2020)
    convenios_dias_query = [convenio if
                            TrayectoriaEtapa.query.filter(TrayectoriaEtapa.id_convenio == convenio.id).
                                order_by(TrayectoriaEtapa.ingreso.asc()).first().ingreso >= date(2020, 1, 1) else None
                            for convenio in Convenio.query.filter(Convenio.estado == 'En producción').order_by(
            Convenio.id.asc()).all()]
    convenios_dias_query = list(filter(None, convenios_dias_query))
    # Días por etapa
    # Sumar días en etapa de cada convenio
    for convenio in convenios_dias_query:
        # Días por etapa
        trayectoria_etapa_query = TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == convenio.id,
                                                                     TrayectoriaEtapa.id_etapa != 5)).all()
        # Contar los días en tapa y en equipo en cada etapa por convenio
        diasxEtapaConvenio = {
            'Definición de Alcance del Convenio': 0,
            'Confección de Documento de Convenio': 0,
            'Gestión de Visto Bueno y Firmas': 0,
            'Generación de Resolución y Protocolo Técnico': 0,
        }
        diasxEquipoEtapaConvenio = {
            'total': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                    'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
            'Definición de Alcance del Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                                 'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
            'Confección de Documento de Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                                  'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
            'Gestión de Visto Bueno y Firmas': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                              'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
            'Generación de Resolución y Protocolo Técnico': dict.fromkeys(
                ['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                 'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
        }
        cuentaxEquipoEtapaConvenio = {
            'total': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                    'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], False),
            'Definición de Alcance del Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                                 'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'],
                                                                False),
            'Confección de Documento de Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                                  'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'],
                                                                 False),
            'Gestión de Visto Bueno y Firmas': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                              'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], False),
            'Generación de Resolución y Protocolo Técnico': dict.fromkeys(
                ['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                 'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], False)
        }
        tareasxEquipoEtapaConvenio = {
            'Definición de Alcance del Convenio': {},
            'Confección de Documento de Convenio': {},
            'Gestión de Visto Bueno y Firmas': {},
            'Generación de Resolución y Protocolo Técnico': {}
        }
        for trayectoEtapa in trayectoria_etapa_query:
            # Sumar días del trayecto a los días de la etapa del convenio
            diasxEtapaConvenio[trayectoEtapa.etapa.etapa] += (trayectoEtapa.salida - trayectoEtapa.ingreso).days

            # Obtener equipos de cada trayecto de etapa
            trayectoria_equipos_query = TrayectoriaEquipo.query.filter(
                and_(TrayectoriaEquipo.id_convenio == convenio.id,
                     and_(TrayectoriaEquipo.ingreso <= trayectoEtapa.salida,
                          TrayectoriaEquipo.salida >= trayectoEtapa.ingreso))).all()
            # Sumar días del trayecto a los días del equipo
            for trayectoEquipo in trayectoria_equipos_query:
                sigla = (lambda sigla: 'SDGEET' if sigla == 'AIET' else sigla)(trayectoEquipo.equipo.sigla)
                trayectoEquipoIngreso = (
                    lambda ingreso: ingreso if ingreso >= trayectoEtapa.ingreso else trayectoEtapa.ingreso)(
                    trayectoEquipo.ingreso)
                trayectoEquipoSalida = (
                    lambda salida: salida if salida <= trayectoEtapa.salida else trayectoEtapa.salida)(
                    trayectoEquipo.salida)

                # Marcar que el equipo tuvo el convenio durante la etapa
                cuentaxEquipoEtapaConvenio[trayectoEtapa.etapa.etapa][sigla] = True
                # Sumar días
                diasxEquipoEtapaConvenio[trayectoEtapa.etapa.etapa][sigla] += (
                            trayectoEquipoSalida - trayectoEquipoIngreso).days

                # Contar tarea en el equipo y etapa correspondiente
                try:
                    tareasxEquipoEtapaConvenio[trayectoEtapa.etapa.etapa][sigla] += 1
                except KeyError:
                    tareasxEquipoEtapaConvenio[trayectoEtapa.etapa.etapa][sigla] = 1

        # Días total por equipo del convenio
        trayectoria_equipo_total_query = TrayectoriaEquipo.query.filter(
            TrayectoriaEquipo.id_convenio == convenio.id).all()
        tareasxEquipoTotalConvenio = {}
        for trayectoEquipoTotal in trayectoria_equipo_total_query:
            sigla = (lambda sigla: 'SDGEET' if sigla == 'AIET' else sigla)(trayectoEquipoTotal.equipo.sigla)
            cuentaxEquipoEtapaConvenio['total'][sigla] = True
            diasxEquipoEtapaConvenio['total'][sigla] += (trayectoEquipoTotal.salida - trayectoEquipoTotal.ingreso).days
            # Sumar tareas
            try:
                tareasxEquipoTotalConvenio[sigla] += 1
            except KeyError:
                tareasxEquipoTotalConvenio[sigla] = 1

        # Sumar días del convenio al total de etapas si el convenio estuvo en la etapa
        for (etapa, dias) in diasxEtapaConvenio.items():
            if dias > 0:
                diasxEtapa_produccion[etapa]['suma'] += dias
                diasxEtapa_produccion[etapa]['cuenta'] += 1

        # Sumar dias del convenio al total de equipos si el convenio estuvo en la etapa
        for (etapa, equipos) in diasxEquipoEtapaConvenio.items():
            for (equipo, dias) in equipos.items():
                # Sumar si el convenio pasó por el equipo (puede que sea con dias = 0)
                if cuentaxEquipoEtapaConvenio[etapa][equipo]:
                    diasxEquipos_suma_produccion[etapa][equipo] += dias
                    diasxEquipos_cuenta_produccion[etapa][equipo] += 1

        # Sumar tareas del convenio al total de tareas
        for equipo, tareas in tareasxEquipoTotalConvenio.items():
            try:
                tareasxEquipos_produccion['total'][equipo] += tareas
            except KeyError:
                tareasxEquipos_produccion['total'][equipo] = tareas
        for etapa, datos in tareasxEquipoEtapaConvenio.items():
            for equipo, tareas in datos.items():
                try:
                    tareasxEquipos_produccion[etapa][equipo] += tareas
                except KeyError:
                    tareasxEquipos_produccion[etapa][equipo] = tareas


# Programar que se calculen las estadístcas 2 veces al día
trigger = OrTrigger([CronTrigger(hour=6), CronTrigger(hour=13)])
scheduler = BackgroundScheduler()
scheduler.add_job(func=estadisticas_convenios, trigger=trigger)
scheduler.start()
estadisticas_convenios()


@informes.route('/mis_convenios/<int:id_persona>', methods=['GET', 'POST'])
@login_required
@analista_only
def mis_convenios(id_persona):
    if current_user.permisos != 'Admin':
        persona = Persona.query.get_or_404(id_persona)
        if persona.id != current_user.id_persona:
            abort(403)

    convenios_analista_query = Convenio.query.filter(Convenio.id_coord_sii == id_persona).all()

    # Tareas pendientes
    id_convenios = [convenio.id for convenio in convenios_analista_query]
    tareas_query = BitacoraTarea.query.filter(and_(BitacoraTarea.id_convenio.in_(id_convenios)),
                                              BitacoraTarea.estado == 'Pendiente').order_by(
        BitacoraTarea.plazo.asc()).all()
    tareas_pendientes = []
    for tarea in tareas_query:
        tareas_pendientes.append({
            'id_convenio': tarea.convenio.id,
            'nombre_convenio': generar_nombre_convenio(tarea.convenio),
            'tarea': tarea.tarea,
            'plazo': tarea.plazo,
            'id_tarea': tarea.id
        })
    tareas_pendientes.sort(key=lambda dict: dict['plazo'])

    # Actualizar bitácora
    convenios_select = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in convenios_analista_query]
    convenios_select.insert(0, (0, 'Seleccionar convenio'))

    # Formulario información de convenio
    form_info_convenio = MisConveniosInfoConvenioForm()
    form_info_convenio.etapa.choices.insert(0, (0, 'Seleccione convenio para ver'))
    if 'informacion_convenio' in request.form and form_info_convenio.validate_on_submit():
        convenio = Convenio.query.get(form_info_convenio.id_convenio.data)
        # Actualizar áreas y etapas
        form_info_equipos = [
            (form_info_convenio.id_trayectoriaEquipo_1.data, form_info_convenio.equipo_1.data, form_info_convenio.fecha_equipo_1.data),
            (form_info_convenio.id_trayectoriaEquipo_2.data, form_info_convenio.equipo_2.data, form_info_convenio.fecha_equipo_2.data),
            (form_info_convenio.id_trayectoriaEquipo_3.data, form_info_convenio.equipo_3.data, form_info_convenio.fecha_equipo_3.data),
            (form_info_convenio.id_trayectoriaEquipo_4.data, form_info_convenio.equipo_4.data, form_info_convenio.fecha_equipo_4.data)
        ]

        # Trayectoria etapas
        etapa_actual = TrayectoriaEtapa.query.get(form_info_convenio.id_trayectoriaEtapa.data)
        if etapa_actual.id_etapa != int(form_info_convenio.etapa.data):
            etapa_actual.actualizar_trayectoria_etapa(form_info_convenio)
            # Si se finaliza el proceso
            if form_info_convenio.etapa.data == '5':
                # Finalizar etapa 'Finalizado'
                ultima_etapa = TrayectoriaEtapa.query.filter(
                    and_(TrayectoriaEtapa.id_convenio == form_info_convenio.id_convenio.data,
                         TrayectoriaEtapa.salida == None)).first()
                ultima_etapa.salida = form_info_convenio.fecha_etapa.data
                ultima_etapa.timestamp_salida = datetime.today()
                # Desasignar equipos de trabajo
                for equipo in form_info_equipos:
                    actualizar_trayectoria_equipo(equipo[0], '0', form_info_convenio.fecha_etapa.data, form_info_convenio.id_convenio.data)
                # Eliminar tareas pendientes
                tareas_pendientes_convenio = BitacoraTarea.query.filter(
                    and_(BitacoraTarea.id_convenio == form_info_convenio.id_convenio.data,
                         BitacoraTarea.estado == 'Pendiente')).all()
                for tarea in tareas_pendientes_convenio:
                    tarea.estado = 'Eliminado'
                    tarea.timestamp = datetime.today()
                # Dejar registro en la bitácora
                ultimo_registro_bitacora = BitacoraAnalista(
                    observacion='Se cambia etapa a: Finalizado',
                    fecha=form_info_convenio.fecha_etapa.data,
                    timestamp=datetime.today(),
                    id_convenio=form_info_convenio.id_convenio.data,
                    id_autor=current_user.id
                )
                db.session.add(ultimo_registro_bitacora)
                db.session.commit()

                flash(
                    f'{generar_nombre_convenio(convenio)} ha sido finalizado. No olvide cambiar el estado del {convenio.tipo}.',
                    'warning')
                return redirect(url_for('bitacoras.editar_convenio', id_convenio=form_info_convenio.id_convenio.data))
            # Si convenio sigue en proceso
            else:
                # Dejar registro en bitácora del analista
                observacion_cambio_etapa = BitacoraAnalista(
                    observacion=f'Se cambia etapa a: {dict(ETAPAS).get(int(form_info_convenio.etapa.data))}',
                    fecha=form_info_convenio.fecha_etapa.data,
                    timestamp=datetime.today(),
                    id_convenio=form_info_convenio.id_convenio.data,
                    id_autor=current_user.id
                )
                db.session.add(observacion_cambio_etapa)
                db.session.commit()

        # Trayectoria equipos
        for equipo in form_info_equipos:
            actualizar_trayectoria_equipo(equipo[0], equipo[1], equipo[2], form_info_convenio.id_convenio.data)
        flash(f'Se ha actualizado la información de {generar_nombre_convenio(convenio)}', 'success')
        return redirect(url_for('informes.mis_convenios', id_persona=id_persona))

    # Formulario nueva observación bitácora
    form_bitacora = MisConveniosBitacoraForm()
    if 'bitacora_analista' in request.form and form_bitacora.validate_on_submit():
        # Agregar nueva observación
        nueva_observacion = BitacoraAnalista(
            observacion=form_bitacora.observacion.data,
            fecha=form_bitacora.fecha.data,
            timestamp=datetime.today(),
            id_convenio=form_bitacora.id_convenio_bitacora.data,
            id_autor=current_user.id
        )
        db.session.add(nueva_observacion)
        db.session.commit()
        convenio = Convenio.query.get(form_bitacora.id_convenio_bitacora.data)
        flash(f'Se actualizado la bitácora de {generar_nombre_convenio(convenio)}', 'success')
        return redirect(url_for('informes.mis_convenios', id_persona=id_persona))

    # Formulario nueva tarea
    form_tarea = MisConveniosTareaForm()
    if 'nueva_tarea' in request.form and form_tarea.validate_on_submit():
        # Agregar nueva tarea
        nueva_tarea = BitacoraTarea(
            tarea=form_tarea.tarea.data,
            plazo=form_tarea.plazo.data,
            timestamp=datetime.today(),
            id_convenio=form_tarea.id_convenio_tarea.data,
            id_autor=current_user.id
        )
        db.session.add(nueva_tarea)
        db.session.commit()
        convenio = Convenio.query.get(form_tarea.id_convenio_tarea.data)
        flash(f'Se ha agregado tarea a {generar_nombre_convenio(convenio)}', 'success')
        return redirect(url_for('informes.mis_convenios', id_persona=id_persona))


    # Estado actual de mis convenios
    tabla_estado_actual = []
    for convenio in convenios_analista_query:
        nombre = generar_nombre_convenio(convenio)
        observacion_query = BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == convenio.id,
                                                               BitacoraAnalista.estado != 'Eliminado')).order_by(
            BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).first()
        ultima_observacion = f'({datetime.strftime(observacion_query.fecha, "%d-%m-%Y")}) {observacion_query.observacion}'
        etapa = convenio.estado
        suplente = f'<p align="center">{(lambda sup: obtener_iniciales(sup.nombre) if sup else "")(convenio.sup_sii)}</p>'
        link_resolucion = (lambda
                               link: f'<a target="_blank" class="text-center" style="text-decoration: none; color: #000;" href="{link}">'
                                     f'<i class="fas fa-eye pt-2 text-center btn-lg"></i></a>' if link else
        '<div class="text-center"><i class="fas fa-eye-slash pt-2 text-center text-muted btn-lg"></i></div>')(
            convenio.link_resolucion)
        tabla_estado_actual.append([nombre, etapa, ultima_observacion, suplente, link_resolucion, convenio.id])
    # Ordenar tabla
    tabla_estado_actual.sort(key=lambda lista: lista[0])
    # Agregar link al nombre del convenio y botar el id
    for convenio in tabla_estado_actual:
        convenio[0] = f'<a style="text-decoration: none; color: #000;" href={url_for("bitacoras.bitacora_convenio", id_convenio=convenio[5])}>' \
                 f'{convenio[0]} <i class="fa-solid fa-keyboard fa-fw"></i></a>'
        convenio.pop()

    return render_template('informes/mis_convenios.html', tareas_pendientes=tareas_pendientes, hoy=date.today(),
                           id_persona=id_persona, convenios_select=convenios_select, form_info=form_info_convenio,
                           form_bitacora=form_bitacora, form_tarea=form_tarea, tabla_estado_actual=tabla_estado_actual)


@informes.route('/convenios_en_proceso')
def convenios_en_proceso():
    # Select field convenios en proceso
    convenios_query = Convenio.query.filter(Convenio.estado == 'En proceso').all()
    convenios_select = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in convenios_query]
    convenios_select.sort(key=lambda tup: tup[1])
    convenios_select.insert(0, (0, 'Seleccione convenio para ver detalle'))

    # Convenios en números
    cuenta_convenios = {
        'proceso': Convenio.query.filter(Convenio.estado == 'En proceso').count(),
        'firmados': Convenio.query.filter(and_(Convenio.estado == 'En proceso', Convenio.fecha_documento != None)).count(),
        'publicados': Convenio.query.filter(and_(Convenio.estado == 'En proceso', Convenio.fecha_resolucion != None)).count()
    }

    # Calcular promedio de dias por equipo
    dias_promedio_equipos = {}
    for etapa, datos in diasxEquipos_suma_proceso.items():
        dias_promedio_equipos[etapa] = {}
        for equipo, dias in datos.items():
            if diasxEquipos_cuenta_proceso[etapa][equipo] > 0:
                dias_promedio_equipos[etapa][equipo] = round(dias / diasxEquipos_cuenta_proceso[etapa][equipo])

    # Formato datos para gráficos de días por equipo
    dias_equipos = {
        'total': [[equipo, dias, COLORES_EQUIPOS[equipo]] for equipo, dias in dias_promedio_equipos['total'].items()],
        'definicion': [[equipo, dias, COLORES_EQUIPOS[equipo]] for equipo, dias in
                       dias_promedio_equipos['Definición de Alcance del Convenio'].items()],
        'confeccion': [[equipo, dias, COLORES_EQUIPOS[equipo]] for equipo, dias in
                       dias_promedio_equipos['Confección de Documento de Convenio'].items()],
        'firmas': [[equipo, dias, COLORES_EQUIPOS[equipo]] for equipo, dias in
                   dias_promedio_equipos['Gestión de Visto Bueno y Firmas'].items()],
        'resolucion': [[equipo, dias, COLORES_EQUIPOS[equipo]] for equipo, dias in
                       dias_promedio_equipos['Generación de Resolución y Protocolo Técnico'].items()]
    }
    for etapa, datos in dias_equipos.items():
        datos.insert(0, ['Equipo', 'Días en equipo'])

    # Calcular promedio de dias por etapa y del proceso
    dias_proceso = 0
    dias_promedio_etapas = {}
    for etapa, datos in diasxEtapa_proceso.items():
        dias_promedio_etapas[etapa] = round(datos['suma'] / datos['cuenta'])
        dias_proceso += round(datos['suma'] / datos['cuenta'])
    # Formato datos para los gráficos de días por etapa
    dias_etapas = {
        'total': [[etapa, dias] for etapa, dias in dias_promedio_etapas.items()],
        'definicion': [
            ['Definición de Alcance del Convenio', dias_promedio_etapas['Definición de Alcance del Convenio']],
            ['Confección de Documento de Convenio', 0],
            ['Gestión de Visto Bueno y Firmas', 0],
            ['Generación de Resolución y Protocolo Técnico', 0]],
        'confeccion': [['Definición de Alcance del Convenio', 0],
                       ['Confección de Documento de Convenio',
                        dias_promedio_etapas['Confección de Documento de Convenio']],
                       ['Gestión de Visto Bueno y Firmas', 0],
                       ['Generación de Resolución y Protocolo Técnico', 0]],
        'firmas': [['Definición de Alcance del Convenio', 0],
                   ['Confección de Documento de Convenio', 0],
                   ['Gestión de Visto Bueno y Firmas', dias_promedio_etapas['Gestión de Visto Bueno y Firmas']],
                   ['Generación de Resolución y Protocolo Técnico', 0]],
        'resolucion': [['Definición de Alcance del Convenio', 0],
                       ['Confección de Documento de Convenio', 0],
                       ['Gestión de Visto Bueno y Firmas', 0],
                       ['Generación de Resolución y Protocolo Técnico',
                        dias_promedio_etapas['Generación de Resolución y Protocolo Técnico']]]
    }
    for etapa, datos in dias_etapas.items():
        datos.insert(0, ['Etapa', 'Días en etapa'])

    # Calcular promedio de tareas por equipo en cada etapa
    tareas_promedio_equipos = {}
    for etapa, datos in tareasxEquipos_proceso.items():
        tareas_promedio_equipos[etapa] = {}
        for equipo, tareas in datos.items():
            if diasxEquipos_cuenta_proceso[etapa][equipo] > 0:
                tareas_promedio_equipos[etapa][equipo] = ceil(tareas / diasxEquipos_cuenta_proceso[etapa][equipo])
    # Formato datos para el gráfico de tareas por equipo
    tareas_equipos = {}
    for etapa, datos in tareas_promedio_equipos.items():
        tareas_lista = [['Área', 'Tiempo de respuesta (días)']]
        colores_etapa = []
        for i, (equipo, tareas) in enumerate(datos.items()):
            tareas_lista[0].insert(1, 'Tareas')
            tareas_lista.append([])
            tareas_lista[i + 1].append(equipo)
            if i == 0:
                tareas_lista[i + 1].append(tareas)
                for j in range(0, len(datos) - (i + 1)):
                    tareas_lista[i + 1].append(0)
            else:
                for j in range(0, i):
                    tareas_lista[i + 1].append(0)
                tareas_lista[i + 1].append(tareas)
                for j in range(0, len(datos) - (i + 1)):
                    tareas_lista[i + 1].append(0)
            # Tiempo de respuesta promedio
            tareas_lista[i + 1].append(
                round(diasxEquipos_suma_proceso[etapa][equipo] / tareasxEquipos_proceso[etapa][equipo]))
            colores_etapa.append(COLORES_EQUIPOS[equipo])

            # Pasar datos al diccionario
            if etapa == 'total':
                tareas_equipos['total'] = {'datos': tareas_lista,
                                           'colores': colores_etapa,
                                           }
            elif etapa == 'Definición de Alcance del Convenio':
                tareas_equipos['definicion'] = {'datos': tareas_lista,
                                                'colores': colores_etapa,
                                                }
            elif etapa == 'Confección de Documento de Convenio':
                tareas_equipos['confeccion'] = {'datos': tareas_lista,
                                                'colores': colores_etapa,
                                                }
            elif etapa == 'Gestión de Visto Bueno y Firmas':
                tareas_equipos['firmas'] = {'datos': tareas_lista,
                                            'colores': colores_etapa,
                                            }
            elif etapa == 'Generación de Resolución y Protocolo Técnico':
                tareas_equipos['resolucion'] = {'datos': tareas_lista,
                                                'colores': colores_etapa,
                                                }

    # Listado convenios en proceso
    listado_convenios = [[
        convenio.institucion.sigla,
        f'<a style="text-decoration: none; color: #000;" href={url_for("informes.detalle_convenio_en_proceso", id_convenio=convenio.id)}>'
        f'{(lambda tipo: convenio.nombre if tipo == "Convenio" else f"(Ad) {convenio.nombre}")(convenio.tipo)}'
        f'<i class="fas fa-search btn-sm"></i></a>',
        obtener_etapa_actual_dias(convenio),
        obtener_equipos_actual_dias(convenio),
        (lambda
             link: f'<a target="_blank" class="text-center" style="text-decoration: none; color: #000;" href="{link}">'
                   f'<i class="fas fa-eye pt-2 text-center btn-lg"></i></a>' if link else
        '<div class="text-center"><i class="fas fa-eye-slash pt-2 text-center text-muted btn-lg"></i></div>')(
            convenio.link_resolucion)
    ]
        for convenio in convenios_query]
    return render_template('informes/convenios_en_proceso.html', convenios_select=convenios_select,
                           listado_convenios=listado_convenios, dias_etapas=dias_etapas, dias_proceso=dias_proceso,
                           dias_equipos=dias_equipos, tareas_equipos=tareas_equipos, cuenta_convenios=cuenta_convenios)


@informes.route('/detalle_convenio_en_proceso/<int:id_convenio>', methods=['GET', 'POST'])
def detalle_convenio_en_proceso(id_convenio):
    # Select field convenios en producción
    convenios_query = Convenio.query.filter(Convenio.estado == 'En proceso').all()
    convenios_select = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in convenios_query]
    convenios_select.sort(key=lambda tup: tup[1])
    convenios_select.insert(0, (0, 'Ver resumen convenios en producción'))

    # Obtener datos para el informe
    convenio_query = Convenio.query.get(id_convenio)

    # Información del convenio
    subdirecciones_involucradas = SdInvolucrada.query.filter(SdInvolucrada.id_convenio == id_convenio).all()
    informacion_convenio = {
        'fecha_firma': (lambda firma: datetime.strftime(firma, '%d-%m-%Y') if firma else 'No firmado')(
            convenio_query.fecha_documento),
        'fecha_resolucion': (lambda convenio: datetime.strftime(convenio.fecha_resolucion,
                                                                "%d-%m-%Y") if convenio.fecha_resolucion != None else "Sin resolución")(
            convenio_query),
        'nro_resolucion': convenio_query.nro_resolucion,
        'link_resolucion': (lambda convenio: convenio.link_resolucion if convenio.link_resolucion != None else "")(
            convenio_query),
        'coord_sii': convenio_query.coord_sii.nombre,
        'sup_sii': (lambda convenio: convenio.sup_sii.nombre if convenio.id_sup_sii != None else "Sin asignar")(
            convenio_query),
        'gabinete': (
            lambda convenio: convenio.gabinete_electronico if convenio.gabinete_electronico != None else 'Sin asignar')(
            convenio_query),
        'proyecto': (lambda convenio: convenio.proyecto if convenio.proyecto != None else 'Sin asignar')(
            convenio_query),
        'subdirecciones': [subdireccion.subdireccion.sigla for subdireccion in subdirecciones_involucradas],
        'sd_techo': ceil(len(subdirecciones_involucradas) / 2),
        'sd_total': len(subdirecciones_involucradas),
        'adendum': []
    }
    # Si es un adendum agregar el convenio padre (que también debe estar en producción)
    if convenio_query.tipo == 'Adendum':
        informacion_convenio['convenio_padre'] = {
            'nombre_convenio_padre': generar_nombre_convenio(Convenio.query.get(convenio_query.id_convenio_padre)),
            'id_convenio_padre': convenio_query.id_convenio_padre,
            'estado_convenio_padre': Convenio.query.get(convenio_query.id_convenio_padre).estado
        }
    else:
        informacion_convenio['convenio_padre'] = None

    # Agregar adendum si existen y su estado (para el link a la página correspondiente)
    adendum_query = Convenio.query.filter(Convenio.id_convenio_padre == id_convenio).all()
    if adendum_query:
        for adendum in adendum_query:
            informacion_convenio['adendum'].append({
                'nombre_adendum': generar_nombre_convenio(adendum),
                'id_adendum': adendum.id,
                'estado_adendum': adendum.estado
            })
        informacion_convenio['adendum'].sort(key=lambda dict: dict['nombre_adendum'])
    else:
        informacion_convenio['adendum'] = None

    # Estadísticas y Trayectoria
    trayectoria_etapas_query = TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == id_convenio,
                                                                  TrayectoriaEtapa.id_etapa != 5)).all()
    trayectoria_equipos_query = TrayectoriaEquipo.query.filter(TrayectoriaEquipo.id_convenio == id_convenio).all()

    # Estadísticas del proceso
    dias_proceso = 0
    # Días por etapa
    cuenta_etapas = {
        'Definición de Alcance del Convenio': 0,
        'Confección de Documento de Convenio': 0,
        'Gestión de Visto Bueno y Firmas': 0,
        'Generación de Resolución y Protocolo Técnico': 0
    }
    for trayecto in trayectoria_etapas_query:
        # Fecha de salida de la etapa
        trayectoEtapaSalida = (lambda salida: salida if salida != None else date.today())(trayecto.salida)
        cuenta_etapas[trayecto.etapa.etapa] += (trayectoEtapaSalida - trayecto.ingreso).days
        dias_proceso += (trayectoEtapaSalida - trayecto.ingreso).days
    dias_etapas_total = [[etapa, dias] for etapa, dias in cuenta_etapas.items()]
    dias_etapas = {
        'total': dias_etapas_total,
        'definicion': [['Definición de Alcance del Convenio', cuenta_etapas['Definición de Alcance del Convenio']],
                       ['Confección de Documento de Convenio', 0],
                       ['Gestión de Visto Bueno y Firmas', 0],
                       ['Generación de Resolución y Protocolo Técnico', 0]],
        'confeccion': [['Definición de Alcance del Convenio', 0],
                       ['Confección de Documento de Convenio', cuenta_etapas['Confección de Documento de Convenio']],
                       ['Gestión de Visto Bueno y Firmas', 0],
                       ['Generación de Resolución y Protocolo Técnico', 0]],
        'firmas': [['Definición de Alcance del Convenio', 0],
                   ['Confección de Documento de Convenio', 0],
                   ['Gestión de Visto Bueno y Firmas', cuenta_etapas['Gestión de Visto Bueno y Firmas']],
                   ['Generación de Resolución y Protocolo Técnico', 0]],
        'resolucion': [['Definición de Alcance del Convenio', 0],
                       ['Confección de Documento de Convenio', 0],
                       ['Gestión de Visto Bueno y Firmas', 0],
                       ['Generación de Resolución y Protocolo Técnico',
                        cuenta_etapas['Generación de Resolución y Protocolo Técnico']]]
    }
    for etapa, datos in dias_etapas.items():
        datos.insert(0, ['Etapa', 'Días en etapa'])

    # Días por área
    # Contar días del convenio en cada equipo y número de tareas
    cuenta_equipos_total = {
        'SDGEET': 0,
        'IE': 0,
        'SDAC': 0,
        'SDAV': 0,
        'SDF': 0,
        'SDI': 0,
        'SDJ': 0,
        'GDIR': 0,
        'DGC': 0,
        'SDA': 0,
        'SDACORP': 0,
        'SDDP': 0,
        'SDN': 0
    }
    cuenta_tareas_total = {}
    for trayecto in trayectoria_equipos_query:
        trayectoEquipoSalida = (lambda salida: salida if salida != None else date.today())(trayecto.salida)
        sigla = (lambda sigla: 'SDGEET' if sigla == 'AIET' else sigla)(trayecto.equipo.sigla)
        cuenta_equipos_total[sigla] += (trayectoEquipoSalida - trayecto.ingreso).days
        # Agregar al diccionario si no existe
        try:
            cuenta_tareas_total[sigla] += 1
        except KeyError:
            cuenta_tareas_total[sigla] = 1
    # Eliminar equipos con 0 tareas en cuenta_tareas_total

    dias_equipos_total = [[equipo, dias, COLORES_EQUIPOS[equipo]]
                          for equipo, dias in cuenta_equipos_total.items()
                          if equipo in cuenta_tareas_total]
    tareas_total = [['Área', 'Tiempo respuesta (días)']]
    for i, (equipo, tareas) in enumerate(cuenta_tareas_total.items()):
        tareas_total[0].insert(1, 'Tareas')
        tareas_total.append([])
        tareas_total[i + 1].append(equipo)
        if i == 0:
            tareas_total[i + 1].append(tareas)
            for j in range(0, len(cuenta_tareas_total) - (i + 1)):
                tareas_total[i + 1].append(0)
        else:
            for j in range(0, i):
                tareas_total[i + 1].append(0)
            tareas_total[i + 1].append(tareas)
            for j in range(0, len(cuenta_tareas_total) - (i + 1)):
                tareas_total[i + 1].append(0)
        # Tiempo de respuesta promedio
        tareas_total[i + 1].append(round(cuenta_equipos_total[equipo] / tareas))

    cuenta_equipos = {
        'total': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
        'Definición de Alcance del Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                             'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
        'Confección de Documento de Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                              'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
        'Gestión de Visto Bueno y Firmas': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                          'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
        'Generación de Resolución y Protocolo Técnico': dict.fromkeys(
            ['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
             'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    }

    trayectoria_equipos = {
        'total': {
            'datos': [],
            'colores': []
        },
        'etapas': []
    }

    tareas_etapa = {}

    for etapa in trayectoria_etapas_query:
        trayectoEtapaSalida = (lambda salida: salida if salida != None else date.today())(etapa.salida)
        equipos_query = TrayectoriaEquipo.query.filter(and_(TrayectoriaEquipo.id_convenio == id_convenio,
                                                            and_(TrayectoriaEquipo.ingreso <= trayectoEtapaSalida,
                                                                 or_(TrayectoriaEquipo.salida >= etapa.ingreso,
                                                                     TrayectoriaEquipo.salida == None)))).all()
        cuenta_tareas_etapa = {}
        # Agregar etapa a la trayectoria de equipos
        trayectoria_equipos['etapas'].append({'datos': [], 'colores': []})
        # Calular días considerando solo el inicio y término de la etapa
        for trayecto in equipos_query:
            trayectoEquipoSalida = (lambda salida: salida if salida != None else date.today())(trayecto.salida)
            trayectoria_equipos['etapas'][-1]['colores'].append(COLORES_EQUIPOS[trayecto.equipo.sigla])
            sigla = (lambda sigla: 'SDGEET' if sigla == 'AIET' else sigla)(trayecto.equipo.sigla)
            # Días por equipo
            if trayecto.ingreso <= etapa.ingreso:
                if trayectoEquipoSalida >= trayectoEtapaSalida:
                    cuenta_equipos[etapa.etapa.etapa][sigla] += (trayectoEtapaSalida - etapa.ingreso).days
                    trayectoria_equipos['etapas'][-1]['datos'].append({
                        'equipo': sigla,
                        'ingreso_dia': int(datetime.strftime(etapa.ingreso, '%d')),
                        'ingreso_mes': int(datetime.strftime(etapa.ingreso, '%m')) - 1,
                        'ingreso_año': datetime.strftime(etapa.ingreso, '%Y'),
                        'salida_dia': datetime.strftime(trayectoEtapaSalida, '%d'),
                        'salida_mes': int(datetime.strftime(trayectoEtapaSalida, '%m')) - 1,
                        'salida_año': datetime.strftime(trayectoEtapaSalida, '%Y'),
                    })
                else:
                    cuenta_equipos[etapa.etapa.etapa][sigla] += (trayectoEquipoSalida - etapa.ingreso).days
                    trayectoria_equipos['etapas'][-1]['datos'].append({
                        'equipo': sigla,
                        'ingreso_dia': int(datetime.strftime(etapa.ingreso, '%d')),
                        'ingreso_mes': int(datetime.strftime(etapa.ingreso, '%m')) - 1,
                        'ingreso_año': datetime.strftime(etapa.ingreso, '%Y'),
                        'salida_dia': datetime.strftime(trayectoEquipoSalida, '%d'),
                        'salida_mes': int(datetime.strftime(trayectoEquipoSalida, '%m')) - 1,
                        'salida_año': datetime.strftime(trayectoEquipoSalida, '%Y'),
                    })

            else:
                if trayectoEquipoSalida >= trayectoEtapaSalida:
                    cuenta_equipos[etapa.etapa.etapa][sigla] += (trayectoEtapaSalida - trayecto.ingreso).days
                    trayectoria_equipos['etapas'][-1]['datos'].append({
                        'equipo': sigla,
                        'ingreso_dia': int(datetime.strftime(trayecto.ingreso, '%d')),
                        'ingreso_mes': int(datetime.strftime(trayecto.ingreso, '%m')) - 1,
                        'ingreso_año': datetime.strftime(trayecto.ingreso, '%Y'),
                        'salida_dia': datetime.strftime(trayectoEtapaSalida, '%d'),
                        'salida_mes': int(datetime.strftime(trayectoEtapaSalida, '%m')) - 1,
                        'salida_año': datetime.strftime(trayectoEtapaSalida, '%Y'),
                    })
                else:
                    cuenta_equipos[etapa.etapa.etapa][sigla] += (trayectoEquipoSalida - trayecto.ingreso).days
                    trayectoria_equipos['etapas'][-1]['datos'].append({
                        'equipo': sigla,
                        'ingreso_dia': int(datetime.strftime(trayecto.ingreso, '%d')),
                        'ingreso_mes': int(datetime.strftime(trayecto.ingreso, '%m')) - 1,
                        'ingreso_año': datetime.strftime(trayecto.ingreso, '%Y'),
                        'salida_dia': datetime.strftime(trayectoEquipoSalida, '%d'),
                        'salida_mes': int(datetime.strftime(trayectoEquipoSalida, '%m')) - 1,
                        'salida_año': datetime.strftime(trayectoEquipoSalida, '%Y'),
                    })

            # Contar tareas
            try:
                cuenta_tareas_etapa[sigla] += 1
            except KeyError:
                cuenta_tareas_etapa[sigla] = 1

        trayectoria_equipos['etapas'][-1]['colores'] = list(dict.fromkeys(trayectoria_equipos['etapas'][-1]['colores']))

        tareas_etapa[etapa.etapa.etapa] = cuenta_tareas_etapa

    dias_equipos = {
        'total': dias_equipos_total,
        'definicion': [[equipo, dias, COLORES_EQUIPOS[equipo]]
                       for equipo, dias in cuenta_equipos['Definición de Alcance del Convenio'].items()
                       if 'Definición de Alcance del Convenio' in tareas_etapa and equipo in tareas_etapa[
                           'Definición de Alcance del Convenio']],
        'confeccion': [[equipo, dias, COLORES_EQUIPOS[equipo]]
                       for equipo, dias in cuenta_equipos['Confección de Documento de Convenio'].items()
                       if 'Confección de Documento de Convenio' in tareas_etapa and equipo in tareas_etapa[
                           'Confección de Documento de Convenio']],
        'firmas': [[equipo, dias, COLORES_EQUIPOS[equipo]]
                   for equipo, dias in cuenta_equipos['Gestión de Visto Bueno y Firmas'].items()
                   if 'Gestión de Visto Bueno y Firmas' in tareas_etapa and equipo in tareas_etapa[
                       'Gestión de Visto Bueno y Firmas']],
        'resolucion': [[equipo, dias, COLORES_EQUIPOS[equipo]]
                       for equipo, dias in cuenta_equipos['Generación de Resolución y Protocolo Técnico'].items()
                       if 'Generación de Resolución y Protocolo Técnico' in tareas_etapa and equipo in tareas_etapa[
                           'Generación de Resolución y Protocolo Técnico']]
    }
    for etapa, datos in dias_equipos.items():
        datos.insert(0, ['Equipos', 'Días en equipo'])

    tareas_equipos = dict.fromkeys(['total', 'definicion', 'confeccion', 'firmas', 'resolucion'],
                                   {'datos': tareas_total,
                                    'colores': [COLORES_EQUIPOS[equipo] for equipo, tarea in
                                                cuenta_tareas_total.items()]
                                    })

    for etapa, equipos in tareas_etapa.items():
        tareas_lista = [['Área', 'Tiempo respuesta (días)']]
        colores_etapa = []
        # Añadir encabezado
        for i, (equipo, tareas) in enumerate(equipos.items()):
            tareas_lista[0].insert(1, 'Tareas')
            tareas_lista.append([])
            tareas_lista[i + 1].append(equipo)
            if i == 0:
                tareas_lista[i + 1].append(tareas)
                for j in range(0, len(equipos) - (i + 1)):
                    tareas_lista[i + 1].append(0)
            else:
                for j in range(0, i):
                    tareas_lista[i + 1].append(0)
                tareas_lista[i + 1].append(tareas)
                for j in range(0, len(equipos) - (i + 1)):
                    tareas_lista[i + 1].append(0)

            # Tiempo de respuesta promedio
            tareas_lista[i + 1].append(round(cuenta_equipos[etapa][equipo] / tareas))
            # Colores
            colores_etapa.append(COLORES_EQUIPOS[equipo])

        # Pasar datos al diccionario
        if etapa == 'Definición de Alcance del Convenio':
            tareas_equipos['definicion'] = {'datos': tareas_lista,
                                            'colores': colores_etapa,
                                            }
        elif etapa == 'Confección de Documento de Convenio':
            tareas_equipos['confeccion'] = {'datos': tareas_lista,
                                            'colores': colores_etapa,
                                            }
        elif etapa == 'Gestión de Visto Bueno y Firmas':
            tareas_equipos['firmas'] = {'datos': tareas_lista,
                                        'colores': colores_etapa,
                                        }
        elif etapa == 'Generación de Resolución y Protocolo Técnico':
            tareas_equipos['resolucion'] = {'datos': tareas_lista,
                                            'colores': colores_etapa,
                                            }

    # Timeline Trayectoria
    # Etapas
    trayectoria_etapas = [{
        'etapa': trayecto.etapa.etapa,
        'ingreso_dia': int(datetime.strftime(trayecto.ingreso, '%d')),
        'ingreso_mes': int(datetime.strftime(trayecto.ingreso, '%m')) - 1,
        'ingreso_año': datetime.strftime(trayecto.ingreso, '%Y'),
        'salida_dia': datetime.strftime((lambda salida: salida if salida != None else date.today())(trayecto.salida),
                                        '%d'),
        'salida_mes': int(
            datetime.strftime((lambda salida: salida if salida != None else date.today())(trayecto.salida), '%m')) - 1,
        'salida_año': datetime.strftime((lambda salida: salida if salida != None else date.today())(trayecto.salida),
                                        '%Y'),
    } for trayecto in trayectoria_etapas_query]

    for trayecto in trayectoria_etapas:
        trayecto['color'] = COLORES_ETAPAS[trayecto['etapa']]

    # Equipos
    trayectoria_equipos['total']['datos'] = [{
        'equipo': (lambda sigla: sigla if sigla != 'AIET' else 'SDGEET')(trayecto.equipo.sigla),
        'ingreso_dia': int(datetime.strftime(trayecto.ingreso, '%d')),
        'ingreso_mes': int(datetime.strftime(trayecto.ingreso, '%m')) - 1,
        'ingreso_año': datetime.strftime(trayecto.ingreso, '%Y'),
        'salida_dia': datetime.strftime((lambda salida: salida if salida != None else date.today())(trayecto.salida),
                                        '%d'),
        'salida_mes': int(
            datetime.strftime((lambda salida: salida if salida != None else date.today())(trayecto.salida), '%m')) - 1,
        'salida_año': datetime.strftime((lambda salida: salida if salida != None else date.today())(trayecto.salida),
                                        '%Y'),
    } for trayecto in trayectoria_equipos_query]
    trayectoria_equipos['total']['colores'] = list(
        dict.fromkeys([COLORES_EQUIPOS[trayecto.equipo.sigla] for trayecto in trayectoria_equipos_query]))

    # Bitácora
    bitacora_dict = [{
        'id': registro.id,
        'observacion': registro.observacion,
        'fecha': datetime.strftime(registro.fecha, '%YYYY-%MM-%DD'),
        'dia': datetime.strftime(registro.fecha, '%d'),
        'mes': int(datetime.strftime(registro.fecha, '%m')) - 1,
        'año': datetime.strftime(registro.fecha, '%Y'),
    }
        for registro in ((BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == id_convenio,
                                                             BitacoraAnalista.estado != 'Eliminado')))).
            order_by(BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).all()]

    return render_template('informes/detalle_convenio_en_proceso.html', id_convenio=id_convenio,
                           convenios_select=convenios_select,
                           informacion_convenio=informacion_convenio, bitacora=bitacora_dict,
                           trayectoria_etapas=trayectoria_etapas, trayectoria_equipos=trayectoria_equipos,
                           dias_etapas=dias_etapas, dias_equipos=dias_equipos, dias_proceso=dias_proceso,
                           tareas_equipos=tareas_equipos)


@informes.route('/convenios_en_produccion')
def convenios_en_produccion():
    # Select field convenios en producción
    convenios_query = Convenio.query.filter(Convenio.estado == 'En producción').order_by(
        Convenio.id.asc()).all()
    convenios_select = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in convenios_query]
    convenios_select.sort(key=lambda tup: tup[1])
    convenios_select.insert(0, (0, 'Seleccione convenio para ver detalle'))

    # Convenios en producción
    cuenta_produccion = {
        'convenios': Convenio.query.filter(and_(Convenio.estado == 'En producción', Convenio.tipo == 'Convenio')).count(),
        'adendum': Convenio.query.filter(and_(Convenio.estado == 'En producción', Convenio.tipo == 'Adendum')).count()
    }

    # Calcular promedio de dias por equipo
    dias_promedio_equipos = {}
    for etapa, datos in diasxEquipos_suma_produccion.items():
        dias_promedio_equipos[etapa] = {}
        for equipo, dias in datos.items():
            if diasxEquipos_cuenta_produccion[etapa][equipo] > 0:
                dias_promedio_equipos[etapa][equipo] = round(dias / diasxEquipos_cuenta_produccion[etapa][equipo])

    # Formato datos para gráficos de días por equipo
    dias_equipos = {
        'total': [[equipo, dias, COLORES_EQUIPOS[equipo]] for equipo, dias in dias_promedio_equipos['total'].items()],
        'definicion': [[equipo, dias, COLORES_EQUIPOS[equipo]] for equipo, dias in
                       dias_promedio_equipos['Definición de Alcance del Convenio'].items()],
        'confeccion': [[equipo, dias, COLORES_EQUIPOS[equipo]] for equipo, dias in
                       dias_promedio_equipos['Confección de Documento de Convenio'].items()],
        'firmas': [[equipo, dias, COLORES_EQUIPOS[equipo]] for equipo, dias in
                   dias_promedio_equipos['Gestión de Visto Bueno y Firmas'].items()],
        'resolucion': [[equipo, dias, COLORES_EQUIPOS[equipo]] for equipo, dias in
                       dias_promedio_equipos['Generación de Resolución y Protocolo Técnico'].items()]
    }
    for etapa, datos in dias_equipos.items():
        datos.insert(0, ['Equipo', 'Días en equipo'])
    # Calcular promedio de dias por etapa y del proceso
    dias_proceso = 0
    dias_promedio_etapas = {}
    for etapa, datos in diasxEtapa_produccion.items():
        dias_promedio_etapas[etapa] = round(datos['suma'] / datos['cuenta'])
        dias_proceso += round(datos['suma'] / datos['cuenta'])
    # Formato datos para los gráficos de días por etapa
    dias_etapas = {
        'total': [[etapa, dias] for etapa, dias in dias_promedio_etapas.items()],
        'definicion': [
            ['Definición de Alcance del Convenio', dias_promedio_etapas['Definición de Alcance del Convenio']],
            ['Confección de Documento de Convenio', 0],
            ['Gestión de Visto Bueno y Firmas', 0],
            ['Generación de Resolución y Protocolo Técnico', 0]],
        'confeccion': [['Definición de Alcance del Convenio', 0],
                       ['Confección de Documento de Convenio',
                        dias_promedio_etapas['Confección de Documento de Convenio']],
                       ['Gestión de Visto Bueno y Firmas', 0],
                       ['Generación de Resolución y Protocolo Técnico', 0]],
        'firmas': [['Definición de Alcance del Convenio', 0],
                   ['Confección de Documento de Convenio', 0],
                   ['Gestión de Visto Bueno y Firmas', dias_promedio_etapas['Gestión de Visto Bueno y Firmas']],
                   ['Generación de Resolución y Protocolo Técnico', 0]],
        'resolucion': [['Definición de Alcance del Convenio', 0],
                       ['Confección de Documento de Convenio', 0],
                       ['Gestión de Visto Bueno y Firmas', 0],
                       ['Generación de Resolución y Protocolo Técnico',
                        dias_promedio_etapas['Generación de Resolución y Protocolo Técnico']]]
    }
    for etapa, datos in dias_etapas.items():
        datos.insert(0, ['Etapa', 'Días en etapa'])

    # Calcular promedio de tareas por equipo en cada etapa
    tareas_promedio_equipos = {}
    for etapa, datos in tareasxEquipos_produccion.items():
        tareas_promedio_equipos[etapa] = {}
        for equipo, tareas in datos.items():
            if diasxEquipos_cuenta_produccion[etapa][equipo] > 0:
                tareas_promedio_equipos[etapa][equipo] = ceil(tareas / diasxEquipos_cuenta_produccion[etapa][equipo])
    # Formato datos para el gráfico de tareas por equipo
    tareas_equipos = {}
    for etapa, datos in tareas_promedio_equipos.items():
        tareas_lista = [['Área', 'Tiempo de respuesta (días)']]
        colores_etapa = []
        for i, (equipo, tareas) in enumerate(datos.items()):
            tareas_lista[0].insert(1, 'Tareas')
            tareas_lista.append([])
            tareas_lista[i + 1].append(equipo)
            if i == 0:
                tareas_lista[i + 1].append(tareas)
                for j in range(0, len(datos) - (i + 1)):
                    tareas_lista[i + 1].append(0)
            else:
                for j in range(0, i):
                    tareas_lista[i + 1].append(0)
                tareas_lista[i + 1].append(tareas)
                for j in range(0, len(datos) - (i + 1)):
                    tareas_lista[i + 1].append(0)
            # Tiempo de respuesta promedio
            tareas_lista[i + 1].append(
                round(diasxEquipos_suma_produccion[etapa][equipo] / tareasxEquipos_produccion[etapa][equipo]))
            colores_etapa.append(COLORES_EQUIPOS[equipo])

            # Pasar datos al diccionario
            if etapa == 'total':
                tareas_equipos['total'] = {'datos': tareas_lista,
                                           'colores': colores_etapa,
                                           }
            elif etapa == 'Definición de Alcance del Convenio':
                tareas_equipos['definicion'] = {'datos': tareas_lista,
                                                'colores': colores_etapa,
                                                }
            elif etapa == 'Confección de Documento de Convenio':
                tareas_equipos['confeccion'] = {'datos': tareas_lista,
                                                'colores': colores_etapa,
                                                }
            elif etapa == 'Gestión de Visto Bueno y Firmas':
                tareas_equipos['firmas'] = {'datos': tareas_lista,
                                            'colores': colores_etapa,
                                            }
            elif etapa == 'Generación de Resolución y Protocolo Técnico':
                tareas_equipos['resolucion'] = {'datos': tareas_lista,
                                                'colores': colores_etapa,
                                                }

    # Listado convenios en producción
    listado_convenios = [{
        'id_convenio': convenio.id,
        'institucion': convenio.institucion.sigla,
        'nombre': f'<a style="text-decoration: none; color: #000;" href={url_for("informes.detalle_convenio_en_produccion", id_convenio=convenio.id)}>'
                  f'{(lambda tipo: convenio.nombre if tipo == "Convenio" else f"(Ad) {convenio.nombre}")(convenio.tipo)}'
                  f'<i class="fas fa-search btn-sm"></i></a>',
        'dia_firma': datetime.strftime(convenio.fecha_documento, '%d'),
        'mes_firma': int(datetime.strftime(convenio.fecha_documento, '%m')) - 1,
        'año_firma': datetime.strftime(convenio.fecha_documento, '%Y'),
        'resolucion': (lambda
                           convenio: f'{convenio.nro_resolucion} del {datetime.strftime(convenio.fecha_resolucion, "%d-%m-%Y")}' if convenio.fecha_resolucion != None else 'Sin resolución')(
            convenio),
        'link_resolucion': (lambda
                                link: f'<a target="_blank" class="text-center" style="text-decoration: none; color: #000;" href="{link}">'
                                      f'<i class="fas fa-eye pt-2 text-center btn-lg"></i></a>' if link else
        '<div class="text-center"><i class="fas fa-eye-slash pt-2 text-center text-muted btn-lg"></i></div>')(
            convenio.link_resolucion)
    }
        for convenio in convenios_query]

    return render_template('informes/convenios_en_produccion.html', convenios_select=convenios_select,
                           listado_convenios=listado_convenios, dias_etapas=dias_etapas, dias_proceso=dias_proceso,
                           dias_equipos=dias_equipos, tareas_equipos=tareas_equipos, cuenta_produccion=cuenta_produccion)


@informes.route('/detalle_convenio_en_produccion/<int:id_convenio>', methods=['GET', 'POST'])
def detalle_convenio_en_produccion(id_convenio):
    # Select field convenios en producción
    convenios_query = Convenio.query.filter(Convenio.estado == 'En producción').all()
    convenios_select = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in convenios_query]
    convenios_select.sort(key=lambda tup: tup[1])
    convenios_select.insert(0, (0, 'Ver resumen convenios en producción'))

    # Obtener datos para el informe
    convenio_query = Convenio.query.get(id_convenio)

    # Información del convenio
    subdirecciones_involucradas = SdInvolucrada.query.filter(SdInvolucrada.id_convenio == id_convenio).all()
    informacion_convenio = {
        'fecha_firma': datetime.strftime(convenio_query.fecha_documento, "%d-%m-%Y"),
        'fecha_resolucion': (lambda convenio: datetime.strftime(convenio.fecha_resolucion,
                                                                "%d-%m-%Y") if convenio.fecha_resolucion != None else "Sin resolución")(
            convenio_query),
        'nro_resolucion': convenio_query.nro_resolucion,
        'link_resolucion': (lambda convenio: convenio.link_resolucion if convenio.link_resolucion != None else "")(
            convenio_query),
        'coord_sii': convenio_query.coord_sii.nombre,
        'sup_sii': (lambda convenio: convenio.sup_sii.nombre if convenio.id_sup_sii != None else "Sin asignar")(
            convenio_query),
        'gabinete': (
            lambda convenio: convenio.gabinete_electronico if convenio.gabinete_electronico != None else 'Sin asignar')(
            convenio_query),
        'proyecto': (lambda convenio: convenio.proyecto if convenio.proyecto != None else 'Sin asignar')(
            convenio_query),
        'subdirecciones': [subdireccion.subdireccion.sigla for subdireccion in subdirecciones_involucradas],
        'sd_techo': ceil(len(subdirecciones_involucradas) / 2),
        'sd_total': len(subdirecciones_involucradas),
        'adendum': []
    }
    # Si es un adendum agregar el convenio padre (que también debe estar en producción)
    if convenio_query.tipo == 'Adendum':
        informacion_convenio['convenio_padre'] = {
            'nombre_convenio_padre': generar_nombre_convenio(Convenio.query.get(convenio_query.id_convenio_padre)),
            'id_convenio_padre': convenio_query.id_convenio_padre
        }
    else:
        informacion_convenio['convenio_padre'] = None

    # Agregar adendum si existen y su estado (para el link a la página correspondiente)
    adendum_query = Convenio.query.filter(Convenio.id_convenio_padre == id_convenio).all()
    if adendum_query:
        for adendum in adendum_query:
            informacion_convenio['adendum'].append({
                'nombre_adendum': generar_nombre_convenio(adendum),
                'id_adendum': adendum.id,
                'estado_adendum': adendum.estado
            })
        informacion_convenio['adendum'].sort(key=lambda dict: dict['nombre_adendum'])
    else:
        informacion_convenio['adendum'] = None

    # Estadísticas y Trayectoria
    trayectoria_etapas_query = TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == id_convenio,
                                                                  TrayectoriaEtapa.id_etapa != 5)).all()
    trayectoria_equipos_query = TrayectoriaEquipo.query.filter(TrayectoriaEquipo.id_convenio == id_convenio).all()

    # Estadísticas del proceso
    dias_proceso = 0
    # Días por etapa
    cuenta_etapas = {
        'Definición de Alcance del Convenio': 0,
        'Confección de Documento de Convenio': 0,
        'Gestión de Visto Bueno y Firmas': 0,
        'Generación de Resolución y Protocolo Técnico': 0
    }
    for trayecto in trayectoria_etapas_query:
        cuenta_etapas[trayecto.etapa.etapa] += (trayecto.salida - trayecto.ingreso).days
        dias_proceso += (trayecto.salida - trayecto.ingreso).days
    dias_etapas_total = [[etapa, dias] for etapa, dias in cuenta_etapas.items()]
    dias_etapas = {
        'total': dias_etapas_total,
        'definicion': [['Definición de Alcance del Convenio', cuenta_etapas['Definición de Alcance del Convenio']],
                       ['Confección de Documento de Convenio', 0],
                       ['Gestión de Visto Bueno y Firmas', 0],
                       ['Generación de Resolución y Protocolo Técnico', 0]],
        'confeccion': [['Definición de Alcance del Convenio', 0],
                       ['Confección de Documento de Convenio', cuenta_etapas['Confección de Documento de Convenio']],
                       ['Gestión de Visto Bueno y Firmas', 0],
                       ['Generación de Resolución y Protocolo Técnico', 0]],
        'firmas': [['Definición de Alcance del Convenio', 0],
                   ['Confección de Documento de Convenio', 0],
                   ['Gestión de Visto Bueno y Firmas', cuenta_etapas['Gestión de Visto Bueno y Firmas']],
                   ['Generación de Resolución y Protocolo Técnico', 0]],
        'resolucion': [['Definición de Alcance del Convenio', 0],
                       ['Confección de Documento de Convenio', 0],
                       ['Gestión de Visto Bueno y Firmas', 0],
                       ['Generación de Resolución y Protocolo Técnico',
                        cuenta_etapas['Generación de Resolución y Protocolo Técnico']]]
    }
    for etapa, datos in dias_etapas.items():
        datos.insert(0, ['Etapa', 'Días en etapa'])

    # Días por área
    # Contar días del convenio en cada equipo y número de tareas
    cuenta_equipos_total = {
        'SDGEET': 0,
        'IE': 0,
        'SDAC': 0,
        'SDAV': 0,
        'SDF': 0,
        'SDI': 0,
        'SDJ': 0,
        'GDIR': 0,
        'DGC': 0,
        'SDA': 0,
        'SDACORP': 0,
        'SDDP': 0,
        'SDN': 0
    }
    cuenta_tareas_total = {}
    for trayecto in trayectoria_equipos_query:
        sigla = (lambda sigla: 'SDGEET' if sigla == 'AIET' else sigla)(trayecto.equipo.sigla)
        cuenta_equipos_total[sigla] += (trayecto.salida - trayecto.ingreso).days
        # Agregar al diccionario si no existe
        try:
            cuenta_tareas_total[sigla] += 1
        except KeyError:
            cuenta_tareas_total[sigla] = 1
    # Eliminar equipos con 0 tareas en cuenta_tareas_total

    dias_equipos_total = [[equipo, dias, COLORES_EQUIPOS[equipo]]
                          for equipo, dias in cuenta_equipos_total.items()
                          if equipo in cuenta_tareas_total]
    tareas_total = [['Área', 'Tiempo respuesta (días)']]
    for i, (equipo, tareas) in enumerate(cuenta_tareas_total.items()):
        tareas_total[0].insert(1, 'Tareas')
        tareas_total.append([])
        tareas_total[i + 1].append(equipo)
        if i == 0:
            tareas_total[i + 1].append(tareas)
            for j in range(0, len(cuenta_tareas_total) - (i + 1)):
                tareas_total[i + 1].append(0)
        else:
            for j in range(0, i):
                tareas_total[i + 1].append(0)
            tareas_total[i + 1].append(tareas)
            for j in range(0, len(cuenta_tareas_total) - (i + 1)):
                tareas_total[i + 1].append(0)
        # Tiempo de respuesta promedio
        tareas_total[i + 1].append(round(cuenta_equipos_total[equipo] / tareas))

    cuenta_equipos = {
        'total': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
        'Definición de Alcance del Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                             'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
        'Confección de Documento de Convenio': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                              'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
        'Gestión de Visto Bueno y Firmas': dict.fromkeys(['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
                                                          'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
        'Generación de Resolución y Protocolo Técnico': dict.fromkeys(
            ['SDGEET', 'IE', 'SDAC', 'SDAV', 'SDF', 'SDI', 'SDJ',
             'GDIR', 'DGC', 'SDA', 'SDACORP', 'SDDP', 'SDN'], 0),
    }

    trayectoria_equipos = {
        'total': {
            'datos': [],
            'colores': []
        },
        'etapas': []
    }

    tareas_etapa = {}

    for etapa in trayectoria_etapas_query:
        equipos_query = TrayectoriaEquipo.query.filter(and_(TrayectoriaEquipo.id_convenio == id_convenio,
                                                            and_(TrayectoriaEquipo.ingreso < etapa.salida,
                                                                 TrayectoriaEquipo.salida > etapa.ingreso))).all()
        cuenta_tareas_etapa = {}
        # Agregar etapa a la trayectoria de equipos
        trayectoria_equipos['etapas'].append({'datos': [], 'colores': []})
        # Calular días considerando solo el inicio y término de la etapa
        for trayecto in equipos_query:
            trayectoria_equipos['etapas'][-1]['colores'].append(COLORES_EQUIPOS[trayecto.equipo.sigla])
            sigla = (lambda sigla: 'SDGEET' if sigla == 'AIET' else sigla)(trayecto.equipo.sigla)
            # Días por equipo
            if trayecto.ingreso < etapa.ingreso:
                if trayecto.salida > etapa.salida:
                    cuenta_equipos[etapa.etapa.etapa][sigla] += (etapa.salida - etapa.ingreso).days
                    trayectoria_equipos['etapas'][-1]['datos'].append({
                        'equipo': sigla,
                        'ingreso_dia': int(datetime.strftime(etapa.ingreso, '%d')),
                        'ingreso_mes': int(datetime.strftime(etapa.ingreso, '%m')) - 1,
                        'ingreso_año': datetime.strftime(etapa.ingreso, '%Y'),
                        'salida_dia': datetime.strftime(etapa.salida, '%d'),
                        'salida_mes': int(datetime.strftime(etapa.salida, '%m')) - 1,
                        'salida_año': datetime.strftime(etapa.salida, '%Y'),
                    })
                else:
                    cuenta_equipos[etapa.etapa.etapa][sigla] += (trayecto.salida - etapa.ingreso).days
                    trayectoria_equipos['etapas'][-1]['datos'].append({
                        'equipo': sigla,
                        'ingreso_dia': int(datetime.strftime(etapa.ingreso, '%d')),
                        'ingreso_mes': int(datetime.strftime(etapa.ingreso, '%m')) - 1,
                        'ingreso_año': datetime.strftime(etapa.ingreso, '%Y'),
                        'salida_dia': datetime.strftime(trayecto.salida, '%d'),
                        'salida_mes': int(datetime.strftime(trayecto.salida, '%m')) - 1,
                        'salida_año': datetime.strftime(trayecto.salida, '%Y'),
                    })

            else:
                if trayecto.salida > etapa.salida:
                    cuenta_equipos[etapa.etapa.etapa][sigla] += (etapa.salida - trayecto.ingreso).days
                    trayectoria_equipos['etapas'][-1]['datos'].append({
                        'equipo': sigla,
                        'ingreso_dia': int(datetime.strftime(trayecto.ingreso, '%d')),
                        'ingreso_mes': int(datetime.strftime(trayecto.ingreso, '%m')) - 1,
                        'ingreso_año': datetime.strftime(trayecto.ingreso, '%Y'),
                        'salida_dia': datetime.strftime(etapa.salida, '%d'),
                        'salida_mes': int(datetime.strftime(etapa.salida, '%m')) - 1,
                        'salida_año': datetime.strftime(etapa.salida, '%Y'),
                    })
                else:
                    cuenta_equipos[etapa.etapa.etapa][sigla] += (trayecto.salida - trayecto.ingreso).days
                    trayectoria_equipos['etapas'][-1]['datos'].append({
                        'equipo': sigla,
                        'ingreso_dia': int(datetime.strftime(trayecto.ingreso, '%d')),
                        'ingreso_mes': int(datetime.strftime(trayecto.ingreso, '%m')) - 1,
                        'ingreso_año': datetime.strftime(trayecto.ingreso, '%Y'),
                        'salida_dia': datetime.strftime(trayecto.salida, '%d'),
                        'salida_mes': int(datetime.strftime(trayecto.salida, '%m')) - 1,
                        'salida_año': datetime.strftime(trayecto.salida, '%Y'),
                    })

            # Contar tareas
            try:
                cuenta_tareas_etapa[sigla] += 1
            except KeyError:
                cuenta_tareas_etapa[sigla] = 1

        trayectoria_equipos['etapas'][-1]['colores'] = list(dict.fromkeys(trayectoria_equipos['etapas'][-1]['colores']))

        tareas_etapa[etapa.etapa.etapa] = cuenta_tareas_etapa

    dias_equipos = {
        'total': dias_equipos_total,
        'definicion': [[equipo, dias, COLORES_EQUIPOS[equipo]]
                       for equipo, dias in cuenta_equipos['Definición de Alcance del Convenio'].items()
                       if 'Definición de Alcance del Convenio' in tareas_etapa and equipo in tareas_etapa[
                           'Definición de Alcance del Convenio']],
        'confeccion': [[equipo, dias, COLORES_EQUIPOS[equipo]]
                       for equipo, dias in cuenta_equipos['Confección de Documento de Convenio'].items()
                       if 'Confección de Documento de Convenio' in tareas_etapa and equipo in tareas_etapa[
                           'Confección de Documento de Convenio']],
        'firmas': [[equipo, dias, COLORES_EQUIPOS[equipo]]
                   for equipo, dias in cuenta_equipos['Gestión de Visto Bueno y Firmas'].items()
                   if 'Gestión de Visto Bueno y Firmas' in tareas_etapa and equipo in tareas_etapa[
                       'Gestión de Visto Bueno y Firmas']],
        'resolucion': [[equipo, dias, COLORES_EQUIPOS[equipo]]
                       for equipo, dias in cuenta_equipos['Generación de Resolución y Protocolo Técnico'].items()
                       if 'Generación de Resolución y Protocolo Técnico' in tareas_etapa and equipo in tareas_etapa[
                           'Generación de Resolución y Protocolo Técnico']]
    }
    for etapa, datos in dias_equipos.items():
        datos.insert(0, ['Equipos', 'Días en equipo'])

    tareas_equipos = dict.fromkeys(['total', 'definicion', 'confeccion', 'firmas', 'resolucion'],
                                   {'datos': tareas_total,
                                    'colores': [COLORES_EQUIPOS[equipo] for equipo, tarea in
                                                cuenta_tareas_total.items()]
                                    })

    for etapa, equipos in tareas_etapa.items():
        tareas_lista = [['Área', 'Tiempo respuesta (días)']]
        colores_etapa = []
        # Añadir encabezado
        for i, (equipo, tareas) in enumerate(equipos.items()):
            tareas_lista[0].insert(1, 'Tareas')
            tareas_lista.append([])
            tareas_lista[i + 1].append(equipo)
            if i == 0:
                tareas_lista[i + 1].append(tareas)
                for j in range(0, len(equipos) - (i + 1)):
                    tareas_lista[i + 1].append(0)
            else:
                for j in range(0, i):
                    tareas_lista[i + 1].append(0)
                tareas_lista[i + 1].append(tareas)
                for j in range(0, len(equipos) - (i + 1)):
                    tareas_lista[i + 1].append(0)

            # Tiempo de respuesta promedio
            tareas_lista[i + 1].append(round(cuenta_equipos[etapa][equipo] / tareas))
            # Colores
            colores_etapa.append(COLORES_EQUIPOS[equipo])

        # Pasar datos al diccionario
        if etapa == 'Definición de Alcance del Convenio':
            tareas_equipos['definicion'] = {'datos': tareas_lista,
                                            'colores': colores_etapa,
                                            }
        elif etapa == 'Confección de Documento de Convenio':
            tareas_equipos['confeccion'] = {'datos': tareas_lista,
                                            'colores': colores_etapa,
                                            }
        elif etapa == 'Gestión de Visto Bueno y Firmas':
            tareas_equipos['firmas'] = {'datos': tareas_lista,
                                        'colores': colores_etapa,
                                        }
        elif etapa == 'Generación de Resolución y Protocolo Técnico':
            tareas_equipos['resolucion'] = {'datos': tareas_lista,
                                            'colores': colores_etapa,
                                            }

    # Timeline Trayectoria
    # Etapas
    trayectoria_etapas = [{
        'etapa': trayecto.etapa.etapa,
        'ingreso_dia': int(datetime.strftime(trayecto.ingreso, '%d')),
        'ingreso_mes': int(datetime.strftime(trayecto.ingreso, '%m')) - 1,
        'ingreso_año': datetime.strftime(trayecto.ingreso, '%Y'),
        'salida_dia': datetime.strftime(trayecto.salida, '%d'),
        'salida_mes': int(datetime.strftime(trayecto.salida, '%m')) - 1,
        'salida_año': datetime.strftime(trayecto.salida, '%Y'),
    } for trayecto in trayectoria_etapas_query]

    for trayecto in trayectoria_etapas:
        trayecto['color'] = COLORES_ETAPAS[trayecto['etapa']]

    # Equipos
    trayectoria_equipos['total']['datos'] = [{
        'equipo': (lambda sigla: sigla if sigla != 'AIET' else 'SDGEET')(trayecto.equipo.sigla),
        'ingreso_dia': int(datetime.strftime(trayecto.ingreso, '%d')),
        'ingreso_mes': int(datetime.strftime(trayecto.ingreso, '%m')) - 1,
        'ingreso_año': datetime.strftime(trayecto.ingreso, '%Y'),
        'salida_dia': datetime.strftime(trayecto.salida, '%d'),
        'salida_mes': int(datetime.strftime(trayecto.salida, '%m')) - 1,
        'salida_año': datetime.strftime(trayecto.salida, '%Y'),
    } for trayecto in trayectoria_equipos_query]
    trayectoria_equipos['total']['colores'] = list(
        dict.fromkeys([COLORES_EQUIPOS[trayecto.equipo.sigla] for trayecto in trayectoria_equipos_query]))

    # Bitácora
    bitacora_dict = [{
        'id': registro.id,
        'observacion': registro.observacion,
        'fecha': datetime.strftime(registro.fecha, '%YYYY-%MM-%DD'),
        'dia': datetime.strftime(registro.fecha, '%d'),
        'mes': int(datetime.strftime(registro.fecha, '%m')) - 1,
        'año': datetime.strftime(registro.fecha, '%Y'),
    }
        for registro in ((BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == id_convenio,
                                                             BitacoraAnalista.estado != 'Eliminado')))).
            order_by(BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).all()]

    return render_template('informes/detalle_convenio_en_produccion.html', id_convenio=id_convenio,
                           convenios_select=convenios_select,
                           informacion_convenio=informacion_convenio, bitacora=bitacora_dict,
                           trayectoria_etapas=trayectoria_etapas, trayectoria_equipos=trayectoria_equipos,
                           dias_etapas=dias_etapas, dias_equipos=dias_equipos, dias_proceso=dias_proceso,
                           tareas_equipos=tareas_equipos)


@informes.route('/obtener_info_convenio/<int:id_convenio>')
def obtener_info_convenio(id_convenio):
    convenio_query = Convenio.query.get(id_convenio)
    etapa_query = (lambda estado: TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == id_convenio,
                                                         TrayectoriaEtapa.salida == None)).first() if estado == 'En proceso' else
                    TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == id_convenio,
                                       TrayectoriaEtapa.id_etapa == 5)).order_by(TrayectoriaEtapa.ingreso.asc()).first()
                   )(convenio_query.estado)
    # Calcular días en proceso
    dias_proceso = 0
    for trayectoEtapa in TrayectoriaEtapa.query.filter(TrayectoriaEtapa.id_convenio == id_convenio).all():
        salida_etapa = (lambda salida: salida if salida != None else date.today())(trayectoEtapa.salida)
        dias_proceso += (salida_etapa - trayectoEtapa.ingreso).days

    # Calcular áreas actuales y días en proceso
    equipos_query = TrayectoriaEquipo.query.filter(
        and_(TrayectoriaEquipo.id_convenio == id_convenio, TrayectoriaEquipo.salida == None)).order_by(
        TrayectoriaEquipo.ingreso.asc()).all()
    equipos = []
    for trayectoEquipo in equipos_query:
        equipos.append({
            'id_trayectoEquipo': trayectoEquipo.id,
            'id_equipo': trayectoEquipo.id_equipo,
            'ingreso': datetime.strftime(trayectoEquipo.ingreso, '%Y-%m-%d'),
            'dias_equipo': (date.today() - trayectoEquipo.ingreso).days
        })
    for i in range(4 - len(equipos_query)):
        equipos.append({
            'id_trayectoEquipo': 0,
            'id_equipo': 0,
            'ingreso': "",
            'dias_equipo': ""
        })

    info_convenio = {
        'id_convenio': id_convenio,
        'dias_proceso': dias_proceso,
        'etapa': {
            'id_trayectoEtapa': etapa_query.id,
            'id_etapa': etapa_query.id_etapa,
            'fecha_etapa': datetime.strftime(etapa_query.ingreso, '%Y-%m-%d'),
            'dias_etapa': (lambda etapa: (date.today() - etapa_query.ingreso).days if etapa != 5 else '')(etapa_query.id_etapa)
        },
        'equipos': equipos

    }
    return jsonify(info_convenio)






def obtener_info_convenios_en_proceso():
    convenios_en_proceso = Convenio.query.filter(Convenio.estado == 'En proceso').all()
    info_convenios = []
    for convenio in convenios_en_proceso:
        ultima_observacion = BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == convenio.id,
                                                                BitacoraAnalista.estado != 'Eliminado')).order_by(
            BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).first()
        proxima_tarea = BitacoraTarea.query.filter(
            and_(BitacoraTarea.id_convenio == convenio.id, BitacoraTarea.estado == 'Pendiente')).order_by(
            BitacoraTarea.plazo.asc(), BitacoraTarea.timestamp.asc()).first()
        etapa_actual = TrayectoriaEtapa.query.filter(
            and_(TrayectoriaEtapa.id_convenio == convenio.id, TrayectoriaEtapa.salida == None)).first()

        equipos_actual = TrayectoriaEquipo.query.filter(
            and_(TrayectoriaEquipo.id_convenio == convenio.id, TrayectoriaEquipo.salida == None)).order_by(
            TrayectoriaEquipo.ingreso.asc()).all()
        equipos = []
        for equipo in equipos_actual:
            equipos.append(f'{equipo.equipo.sigla} ({(date.today() - equipo.ingreso).days})')
        for _ in range(4 - len(equipos_actual)):
            equipos.append("")

        info_convenios.append({
            'nombre': generar_nombre_convenio(convenio),
            # 'encargados': f'{obtener_iniciales(convenio.coord_sii.nombre)}  )',   #({obtener_iniciales(convenio.sup_sii.nombre)})',
            # 'coordinador': convenio.coord_sii.nombre,
            # 'suplente': convenio.sup_sii.nombre,
            # coord_ie, sup_ie
            'observacion': f'{ultima_observacion.fecha}: {ultima_observacion.observacion}',
            'tarea': (lambda tarea: f'{tarea.plazo}: {tarea.tarea}' if tarea != None else "Sin tareas pendientes")(
                proxima_tarea),
            'plazo_tarea': (lambda tarea: tarea.plazo if tarea != None else "Sin tareas pendientes")(proxima_tarea),
            'etapa': f'{etapa_actual.etapa.etapa} ({(date.today() - etapa_actual.ingreso).days})',
            'equipos': equipos,
        })
    info_convenios.sort(key=lambda dict: dict['nombre'])
    return info_convenios


@informes.route('/resumen_convenios_en_proceso')
def resumen_convenios_en_proceso():
    info_convenios = obtener_info_convenios_en_proceso()
    return render_template('informes/convenios_en_proceso.html', info_convenios=info_convenios, hoy=date.today())


#
# @informes.route('/resumen_convenios_en_proceso_pdf')
# def resumen_convenios_en_proceso_pdf():
#     info_convenios = obtener_info_convenios_en_proceso()
#     informe_rendered = render_template('/informes/convenios_en_proceso_pdf.html', info_convenios=info_convenios, hoy=date.today())
#     informe_rendered.encode('utf-8')
#     try:
#         informe_pdf = pdfkit.from_string(informe_rendered, 'C:\Convenios_App\convenios_app\documentos\informe_en_proceso.pdf', configuration=config)
#     except IOError:
#         pass
#
#     return send_from_directory('C:\Convenios_App\convenios_app\documentos', 'informe_en_proceso.pdf', as_attachment=True, attachment_filename=f'Convenios_en_proceso_{date.today()}.pdf')


@informes.route('/informe_aiet')
def informe_aiet():
    info_convenios = obtener_info_convenios_en_proceso()
    return render_template('informes/informe_aiet.html', info_convenios=info_convenios, hoy=date.today())


#
# @informes.route('/informe_aiet_pdf')
# def informe_aiet_pdf():
#     info_convenios = obtener_info_convenios_en_proceso()
#     informe_rendered = render_template('/informes/informe_aiet_pdf.html', info_convenios=info_convenios, hoy=date.today())
#     try:
#         informe_pdf = pdfkit.from_string(informe_rendered, 'C:\Convenios_App\convenios_app\documentos\informe_aiet.pdf', configuration=config )
#     except IOError:
#         pass
#
#     return send_from_directory('C:\Convenios_App\convenios_app\documentos', 'informe_aiet.pdf', as_attachment=True, attachment_filename=f'Informe_aiet_{date.today()}.pdf')


@informes.route('/mis_tareas/<int:id_persona>')
def mis_tareas(id_persona):
    # Select persona
    analistas = [(persona.id, persona.nombre) for persona in
                 Persona.query.filter(Persona.id_equipo == 1).order_by(Persona.nombre.asc()).all()]

    # Obtener convenios en proceso del analista
    convenios_analista = [convenio.id for convenio in Convenio.query.filter(
        and_(Convenio.id_coord_sii == id_persona, Convenio.estado == 'En proceso')).all()]
    tareas_query = BitacoraTarea.query.filter(and_(BitacoraTarea.id_convenio.in_(convenios_analista)),
                                              BitacoraTarea.estado == 'Pendiente').order_by(
        BitacoraTarea.plazo.asc()).all()
    tareas = [(tarea.tarea, tarea.plazo, generar_nombre_convenio(tarea.convenio), tarea.id, tarea.id_convenio) for tarea
              in tareas_query]
    tareas.sort(key=lambda tup: tup[2])

    return render_template('informes/mis_tareas.html', analistas=analistas, tareas=tareas, id_persona=id_persona,
                           hoy=date.today())
