from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify, make_response, \
    send_from_directory, current_app
from flask_login import current_user, login_required
from convenios_app.models import (Convenio, SdInvolucrada, BitacoraAnalista, TrayectoriaEtapa, TrayectoriaEquipo,
                                  HitosConvenio, RecepcionConvenio, WSConvenio)
from convenios_app import db
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import dias_habiles, formato_periodicidad
from convenios_app.main.utils import generar_nombre_convenio, ID_EQUIPOS, COLORES_ETAPAS, COLORES_EQUIPOS
from convenios_app.informes.utils import obtener_etapa_actual_dias, obtener_equipos_actual_dias, adendum, convenio_cuenta, por_firmar, otros

from datetime import datetime, date
#import pandas as pd
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
            diasxEtapaConvenio[trayectoEtapa.etapa.etapa] += dias_habiles(trayectoEtapa.ingreso, trayectoEtapaSalida)

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
                diasxEquipoEtapaConvenio[trayectoEtapa.etapa.etapa][sigla] += dias_habiles(trayectoEquipoIngreso,
                                                                                           trayectoEquipoSalida)

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
            diasxEquipoEtapaConvenio['total'][sigla] += dias_habiles(trayectoEquipoTotal.ingreso,
                                                                     trayectoEquipoTotalSalida)
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
            diasxEtapaConvenio[trayectoEtapa.etapa.etapa] += dias_habiles(trayectoEtapa.ingreso, trayectoEtapa.salida)

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
                diasxEquipoEtapaConvenio[trayectoEtapa.etapa.etapa][sigla] += dias_habiles(trayectoEquipoIngreso,
                                                                                           trayectoEquipoSalida)

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
            diasxEquipoEtapaConvenio['total'][sigla] += dias_habiles(trayectoEquipoTotal.ingreso, trayectoEquipoTotal.salida)
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


@informes.route('/otros_convenios')
def otros_convenios():
    # Select field convenios en proceso
    convenios_query = Convenio.query.filter(
        and_(Convenio.estado != 'En proceso', Convenio.estado != 'En producción')).all()
    convenios_select = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in convenios_query]
    convenios_select.sort(key=lambda tup: tup[1])
    convenios_select.insert(0, (0, 'Seleccione convenio para ver detalle'))

    # Convenios en números
    cuenta_convenios = {
        'pausados': Convenio.query.filter(Convenio.estado == 'Pausado').count(),
        'cancelados': Convenio.query.filter(Convenio.estado == 'Cancelado').count(),
        'reemplazados': Convenio.query.filter(Convenio.estado == 'Reemplazado').count()
    }

    # Listado otros convenios
    listado_convenios = [[
        convenio.institucion.sigla,
        f'<a style="text-decoration: none; color: #000;" href={url_for("informes.detalle_otros_convenios", id_convenio=convenio.id)}>'
        f'{(lambda tipo: convenio.nombre if tipo == "Convenio" else f"(Ad) {convenio.nombre}")(convenio.tipo)}'
        f'<i class="fas fa-search btn-sm"></i></a>',
        convenio.estado,
        (lambda
             link: f'<a target="_blank" class="text-center" style="text-decoration: none; color: #000;" href="{link}">'
                   f'<i class="fas fa-eye pt-2 text-center btn-lg"></i></a>' if link else
        '<div class="text-center"><i class="fas fa-eye-slash pt-2 text-center text-muted btn-lg"></i></div>')(
            convenio.link_resolucion)
    ]
        for convenio in convenios_query]

    return render_template('informes/otros_convenios.html', convenios_select=convenios_select,
                           cuenta_convenios=cuenta_convenios, listado_convenios=listado_convenios)


@informes.route('/detalle_otros_convenios/<int:id_convenio>', methods=['GET', 'POST'])
def detalle_otros_convenios(id_convenio):
    # Select field convenios en producción
    convenios_query = Convenio.query.filter(
        and_(Convenio.estado != 'En producción', Convenio.estado != 'En proceso')).all()
    convenios_select = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in convenios_query]
    convenios_select.sort(key=lambda tup: tup[1])
    convenios_select.insert(0, (0, 'Ver resumen otros convenios'))

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
    # Si fue reemplazado agregar convenio de reemplazo
    if convenio_query.id_convenio_reemplazo:
        convenio_reemplazo_query = Convenio.query.get(convenio_query.id_convenio_reemplazo)
        informacion_convenio['convenio_reemplazo'] = {
            'nombre': generar_nombre_convenio(convenio_reemplazo_query),
            'id': convenio_reemplazo_query.id,
            'estado': convenio_reemplazo_query.estado
        }
    else:
        informacion_convenio['convenio_reemplazo'] = None

    # Información a intercambiar
    recepciones = [{
        'nombre': recepcion.nombre,
        'archivo': recepcion.archivo,
        'periodicidad': formato_periodicidad(recepcion.periodicidad),
        'sd': recepcion.sd.sigla,
        'estado': 'Activo' if recepcion.estado else 'Inactivo'
    } for recepcion in RecepcionConvenio.query.filter(RecepcionConvenio.id_convenio == id_convenio).all()]

    ws_asignados = [{
        'nombre_aiet': ws.ws.nombre_aiet,
        'nombre_sdi': ws.ws.nombre_sdi,
        'metodo': ws.ws.metodo,
        'estado': 'Activo' if ws.estado else 'Inactivo'
    } for ws in WSConvenio.query.filter(WSConvenio.id_convenio == id_convenio).all()]

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
        cuenta_etapas[trayecto.etapa.etapa] += dias_habiles(trayecto.ingreso, trayecto.salida)
        dias_proceso += dias_habiles(trayecto.ingreso, trayecto.salida)
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
        cuenta_equipos_total[sigla] += dias_habiles(trayecto.ingreso, trayecto.salida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(etapa.ingreso, etapa.salida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(etapa.ingreso, trayecto.salida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(trayecto.ingreso, etapa.salida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(trayecto.ingreso, trayecto.salida)
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

    # Hitos
    hitos_query = HitosConvenio.query.filter(HitosConvenio.id_convenio == id_convenio).order_by(
        HitosConvenio.fecha.asc()).all()
    hitos = [{
        'nombre': hito.hito.nombre,
        'fecha': datetime.strftime(hito.fecha, "%d-%m-%Y"),
        'minuta': hito.minuta,
        'grabacion': hito.grabacion
    } for hito in hitos_query]

    return render_template('informes/detalle_otros_convenios.html', id_convenio=id_convenio,
                           convenios_select=convenios_select, informacion_convenio=informacion_convenio,
                           bitacora=bitacora_dict,
                           trayectoria_etapas=trayectoria_etapas, trayectoria_equipos=trayectoria_equipos,
                           dias_etapas=dias_etapas, dias_equipos=dias_equipos, dias_proceso=dias_proceso,
                           tareas_equipos=tareas_equipos, hitos=hitos, recepciones=recepciones,
                           ws_asignados=ws_asignados)


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
        'firmados': Convenio.query.filter(
            and_(Convenio.estado == 'En proceso', Convenio.fecha_documento != None)).count(),
        'publicados': Convenio.query.filter(
            and_(Convenio.estado == 'En proceso', Convenio.fecha_resolucion != None)).count()
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

    # Información a intercambiar
    recepciones = [{
        'nombre': recepcion.nombre,
        'archivo': recepcion.archivo,
        'periodicidad': formato_periodicidad(recepcion.periodicidad),
        'sd': recepcion.sd.sigla,
        'estado': 'Activo' if recepcion.estado else 'Inactivo'
        } for recepcion in RecepcionConvenio.query.filter(RecepcionConvenio.id_convenio == id_convenio).all()]

    ws_asignados = [{
        'nombre_aiet': ws.ws.nombre_aiet,
        'nombre_sdi': ws.ws.nombre_sdi,
        'metodo': ws.ws.metodo,
        'estado': 'Activo' if ws.estado else 'Inactivo'
        } for ws in WSConvenio.query.filter(WSConvenio.id_convenio == id_convenio).all()]

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
        cuenta_etapas[trayecto.etapa.etapa] += dias_habiles(trayecto.ingreso, trayectoEtapaSalida)
        dias_proceso += dias_habiles(trayecto.ingreso, trayectoEtapaSalida)
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
        cuenta_equipos_total[sigla] += dias_habiles(trayecto.ingreso, trayectoEquipoSalida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(etapa.ingreso, trayectoEtapaSalida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(etapa.ingreso, trayectoEquipoSalida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(trayecto.ingreso, trayectoEtapaSalida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(trayecto.ingreso, trayectoEquipoSalida)
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

    # Hitos
    hitos_query = HitosConvenio.query.filter(HitosConvenio.id_convenio == id_convenio).order_by(HitosConvenio.fecha.asc()).all()
    hitos = [{
        'nombre': hito.hito.nombre,
        'fecha': datetime.strftime(hito.fecha, "%d-%m-%Y"),
        'minuta': hito.minuta,
        'grabacion': hito.grabacion
    } for hito in hitos_query]

    return render_template('informes/detalle_convenio_en_proceso.html', id_convenio=id_convenio,
                           convenios_select=convenios_select,
                           informacion_convenio=informacion_convenio, bitacora=bitacora_dict,
                           trayectoria_etapas=trayectoria_etapas, trayectoria_equipos=trayectoria_equipos,
                           dias_etapas=dias_etapas, dias_equipos=dias_equipos, dias_proceso=dias_proceso,
                           tareas_equipos=tareas_equipos, hitos=hitos, recepciones=recepciones,
                           ws_asignados=ws_asignados)


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
        'convenios': Convenio.query.filter(
            and_(Convenio.estado == 'En producción', Convenio.tipo == 'Convenio')).count(),
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
                           convenio: f'N°{convenio.nro_resolucion} del {datetime.strftime(convenio.fecha_resolucion, "%d-%m-%Y")}' if convenio.fecha_resolucion != None else 'Sin resolución')(
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
                           dias_equipos=dias_equipos, tareas_equipos=tareas_equipos,
                           cuenta_produccion=cuenta_produccion)


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

        # Información a intercambiar
    recepciones = [{
        'nombre': recepcion.nombre,
        'archivo': recepcion.archivo,
        'periodicidad': formato_periodicidad(recepcion.periodicidad),
        'sd': recepcion.sd.sigla,
        'estado': 'Activo' if recepcion.estado else 'Inactivo'
    } for recepcion in RecepcionConvenio.query.filter(RecepcionConvenio.id_convenio == id_convenio).all()]

    ws_asignados = [{
        'nombre_aiet': ws.ws.nombre_aiet,
        'nombre_sdi': ws.ws.nombre_sdi,
        'metodo': ws.ws.metodo,
        'estado': 'Activo' if ws.estado else 'Inactivo'
    } for ws in WSConvenio.query.filter(WSConvenio.id_convenio == id_convenio).all()]

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
        cuenta_etapas[trayecto.etapa.etapa] += dias_habiles(trayecto.ingreso, trayecto.salida)
        dias_proceso += dias_habiles(trayecto.ingreso, trayecto.salida)
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
        cuenta_equipos_total[sigla] += dias_habiles(trayecto.ingreso, trayecto.salida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(etapa.ingreso, etapa.salida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(etapa.ingreso, trayecto.salida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(trayecto.ingreso, etapa.salida)
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
                    cuenta_equipos[etapa.etapa.etapa][sigla] += dias_habiles(trayecto.ingreso, trayecto.salida)
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

    # Hitos
    hitos_query = HitosConvenio.query.filter(HitosConvenio.id_convenio == id_convenio).order_by(
        HitosConvenio.fecha.asc()).all()
    hitos = [{
        'nombre': hito.hito.nombre,
        'fecha': datetime.strftime(hito.fecha, "%d-%m-%Y"),
        'minuta': hito.minuta,
        'grabacion': hito.grabacion
    } for hito in hitos_query]

    return render_template('informes/detalle_convenio_en_produccion.html', id_convenio=id_convenio,
                           convenios_select=convenios_select,
                           informacion_convenio=informacion_convenio, bitacora=bitacora_dict,
                           trayectoria_etapas=trayectoria_etapas, trayectoria_equipos=trayectoria_equipos,
                           dias_etapas=dias_etapas, dias_equipos=dias_equipos, dias_proceso=dias_proceso,
                           tareas_equipos=tareas_equipos, hitos=hitos, recepciones=recepciones,
                           ws_asignados=ws_asignados)


@informes.route('/convenios_por_institucion')
def convenios_por_institucion():

    convenios = Convenio.query.all()

    instituciones= {}
    for convenio in convenios:
        # Convenios en producción o en proceso
        if convenio.estado == 'En producción' or convenio.estado == 'En proceso':
            # Convenios firmados
            if convenio.fecha_documento != None:
                try:
                    instituciones[convenio.institucion.sigla][convenio.tipo] += 1
                except KeyError:
                    try: 
                        instituciones[convenio.institucion.sigla][convenio.tipo] = 1
                    except:
                        instituciones[convenio.institucion.sigla] = {'id_institucion': convenio.id_institucion}
                        instituciones[convenio.institucion.sigla][convenio.tipo] = 1
            # Convenios por firmar
            else:
                try:
                    instituciones[convenio.institucion.sigla]["por_firmar"] += 1
                except KeyError:
                    try:
                        instituciones[convenio.institucion.sigla]["por_firmar"] = 1
                    except KeyError:
                        instituciones[convenio.institucion.sigla] = {'id_institucion': convenio.id_institucion}
                        instituciones[convenio.institucion.sigla]["por_firmar"] = 1                     
        # Otros convenios
        else:
            try:
                instituciones[convenio.institucion.sigla]['otros'] += 1
            except KeyError:
                try: 
                    instituciones[convenio.institucion.sigla]['otros'] = 1
                except KeyError:
                    instituciones[convenio.institucion.sigla] = {'id_institucion': convenio.id_institucion}
                    instituciones[convenio.institucion.sigla]['otros'] = 1
    
        # Agregar recepciones
        recepciones = RecepcionConvenio.query.filter(and_(RecepcionConvenio.id_convenio == convenio.id, RecepcionConvenio.estado == 1)).count()
        try:
            instituciones[convenio.institucion.sigla]['recepciones'] += recepciones
        except KeyError:
            instituciones[convenio.institucion.sigla]['recepciones'] = recepciones
        # Agregar WS
        ws = WSConvenio.query.filter(and_(WSConvenio.id_convenio == convenio.id, WSConvenio.estado == 1)).count()
        try:
            instituciones[convenio.institucion.sigla]['ws'] += ws
        except KeyError:
            instituciones[convenio.institucion.sigla]['ws'] = ws
        # Agregar entregas
        # PENDIENTE
    
    # Tabla
    instituciones_data = []
    for institucion, data in instituciones.items():
        instituciones_data.append([
            institucion,
            f"<p align='center'>{convenio_cuenta(data)}</p>",
            f"<p align='center'>{adendum(data)}</p>",
            f"<p align='center'>{por_firmar(data)}</p>",
            f"<p align='center'>{otros(data)}</p>",
            f"<p align='center'>{data['recepciones'] if data['recepciones'] else '-'}</p>",
            f"<p align='center'>{data['ws'] if data['ws'] else '-'}</p>",
            data['id_institucion']
        ])   
    # Ordenar Tabla
    instituciones_data.sort(key=lambda lista:lista[0])
    # Agregar link y botar id
    for institucion in instituciones_data:
        institucion[0] = f"<a class='simple-link' href='#' data-href={institucion[7]} data-bs-toggle='modal' data-bs-target='#institucionModal'>{institucion[0]} <i class='fa-solid fa-landmark fa-fw me-3'></a>"
        institucion.pop()


    return render_template('informes/convenios_por_institucion.html', instituciones=instituciones_data)

@informes.route('/obtener_detalle_institucion/<int:id_institucion>')
def obtener_detalle_institucion(id_institucion):
    convenios_institucion = Convenio.query.filter(Convenio.id_institucion == id_institucion).all()
    detalle_institucion = []
    for convenio in convenios_institucion:
        # Link según estado
        if convenio.estado == 'En proceso':
            convenio_link = f'<a class="simple-link" href={url_for("informes.detalle_convenio_en_proceso", id_convenio=convenio.id)}>{generar_nombre_convenio(convenio)} <i class="fas fa-search btn-sm"></i></a>'
        elif convenio.estado == 'En producción':
            convenio_link = f'<a class="simple-link" href={url_for("informes.detalle_convenio_en_produccion", id_convenio=convenio.id)}>{generar_nombre_convenio(convenio)} <i class="fas fa-search btn-sm"></i></a>'
        else:
            convenio_link = f'<a class="simple-link" href={url_for("informes.detalle_otros_convenios", id_convenio=convenio.id)}>{generar_nombre_convenio(convenio)} <i class="fas fa-search btn-sm"></i></a>'
        detalle_institucion.append([
            convenio_link,
            convenio.estado,
            f"<p align='center'>{RecepcionConvenio.query.filter(RecepcionConvenio.id_convenio == convenio.id).count()}</p>",
            f"<p align='center'>{WSConvenio.query.filter(WSConvenio.id_convenio == convenio.id).count()}</p>"
        ])

    return jsonify(detalle_institucion)


@informes.route('/documentos')
def documentos():

    return render_template('informes/documentos.html')


# def obtener_info_convenios_en_proceso():
#     convenios_en_proceso = Convenio.query.filter(Convenio.estado == 'En proceso').all()
#     info_convenios = []
#     for convenio in convenios_en_proceso:
#         ultima_observacion = BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == convenio.id,
#                                                                 BitacoraAnalista.estado != 'Eliminado')).order_by(
#             BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).first()
#         proxima_tarea = BitacoraTarea.query.filter(
#             and_(BitacoraTarea.id_convenio == convenio.id, BitacoraTarea.estado == 'Pendiente')).order_by(
#             BitacoraTarea.plazo.asc(), BitacoraTarea.timestamp.asc()).first()
#         etapa_actual = TrayectoriaEtapa.query.filter(
#             and_(TrayectoriaEtapa.id_convenio == convenio.id, TrayectoriaEtapa.salida == None)).first()
#
#         equipos_actual = TrayectoriaEquipo.query.filter(
#             and_(TrayectoriaEquipo.id_convenio == convenio.id, TrayectoriaEquipo.salida == None)).order_by(
#             TrayectoriaEquipo.ingreso.asc()).all()
#         equipos = []
#         for equipo in equipos_actual:
#             equipos.append(f'{equipo.equipo.sigla} ({(date.today() - equipo.ingreso).days})')
#         for _ in range(4 - len(equipos_actual)):
#             equipos.append("")
#
#         info_convenios.append({
#             'nombre': generar_nombre_convenio(convenio),
#             # 'encargados': f'{obtener_iniciales(convenio.coord_sii.nombre)}  )',   #({obtener_iniciales(convenio.sup_sii.nombre)})',
#             # 'coordinador': convenio.coord_sii.nombre,
#             # 'suplente': convenio.sup_sii.nombre,
#             # coord_ie, sup_ie
#             'observacion': f'{ultima_observacion.fecha}: {ultima_observacion.observacion}',
#             'tarea': (lambda tarea: f'{tarea.plazo}: {tarea.tarea}' if tarea != None else "Sin tareas pendientes")(
#                 proxima_tarea),
#             'plazo_tarea': (lambda tarea: tarea.plazo if tarea != None else "Sin tareas pendientes")(proxima_tarea),
#             'etapa': f'{etapa_actual.etapa.etapa} ({(date.today() - etapa_actual.ingreso).days})',
#             'equipos': equipos,
#         })
#     info_convenios.sort(key=lambda dict: dict['nombre'])
#     return info_convenios
