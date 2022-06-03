from datetime import datetime, date
from convenios_app.bitacoras.forms import EQUIPOS
from convenios_app import db
from convenios_app.models import TrayectoriaEquipo, BitacoraAnalista, Convenio, TrayectoriaEtapa, SdInvolucrada
from convenios_app.main.utils import formato_nombre
from flask_login import current_user
from sqlalchemy import and_, or_
import pandas as pd
import holidays
from numpy import busday_count
from pprint import pprint

FERIADOS= [pd.to_datetime(date[0], format='%Y-%m-%d').date() for
           date in holidays.CL(years=[year for year in range(2015, 2026, 1)]).items()]


def dias_habiles(ingreso, salida):
    """
    Devuelve los días hábiles entre dos fechas, tomando en cuenta los feriados en Chile (2015-2025)
    :param ingreso: fecha de ingreso
    :param salida: fecha de salida
    :return: número de días entre la fechas
    """
    return int(busday_count(ingreso, salida, holidays=FERIADOS))


def actualizar_trayectoria_equipo(id_trayectoria, id_equipo, fecha_formulario, id_convenio):
    # 1. Si no había equipo asignado
    if id_trayectoria == '0' and id_equipo != '0':
        # Agregar nueva asignación de equipo
        nueva_asignacion = TrayectoriaEquipo(
            ingreso=fecha_formulario,
            timestamp_ingreso=datetime.today(),
            id_convenio=id_convenio,
            id_equipo=id_equipo
        )
        # Dejar registro en bitácora del analista
        nuevo_registro_asignacion = BitacoraAnalista(
            observacion=f"Se asigna convenio a: {dict(EQUIPOS).get(int(id_equipo))}.",
            fecha=fecha_formulario,
            timestamp=datetime.today(),
            id_convenio=id_convenio,
            id_autor=current_user.id
        )
        db.session.add(nueva_asignacion)
        db.session.add(nuevo_registro_asignacion)

    # 2. Si el convenio cambio de equipo
    elif id_trayectoria != '0' and id_equipo != '0' and int(
            TrayectoriaEquipo.query.get(id_trayectoria).equipo.id) != int(id_equipo):
        equipo_saliente = TrayectoriaEquipo.query.get(id_trayectoria)
        # Ingresar fecha de salida en equipo saliente
        equipo_saliente.salida = fecha_formulario
        equipo_saliente.timestamp_salida = datetime.today()
        # Agregar nueva asignación de equipo
        nueva_asignacion = TrayectoriaEquipo(
            ingreso=fecha_formulario,
            timestamp_ingreso=datetime.today(),
            id_convenio=id_convenio,
            id_equipo=id_equipo
        )
        # Dejar registro en bitácora del analista
        nuevo_registro_cambio_equipo = BitacoraAnalista(
            observacion=f"Convenio deja de estar asignado a {equipo_saliente.equipo.sigla} y se asigna a {dict(EQUIPOS).get(int(id_equipo))}.",
            fecha=fecha_formulario,
            timestamp=datetime.today(),
            id_convenio=id_convenio,
            id_autor=current_user.id
        )
        db.session.add(nueva_asignacion)
        db.session.add(nuevo_registro_cambio_equipo)

    # 3. Si el convenio sale de un equipo
    elif id_trayectoria != '0' and id_equipo == '0':
        # Ingresar fecha de salida en equipo saliente
        equipo_saliente = TrayectoriaEquipo.query.get(id_trayectoria)
        equipo_saliente.salida = fecha_formulario
        equipo_saliente.timestamp_salida = datetime.today()
        nuevo_registro_salida = BitacoraAnalista(
            observacion=f"Convenio deja de estar asignado a: {equipo_saliente.equipo.sigla}.",
            fecha=fecha_formulario,
            timestamp=datetime.today(),
            id_convenio=id_convenio,
            id_autor=current_user.id
        )
        db.session.add(nuevo_registro_salida)
    db.session.commit()


def actualizar_convenio(convenio, form, sd_actuales, query_sd, sd_seleccionadas):
    """
    Actualiza la tabla Convenio y SD Involucrada en el formulario de editar convenio.
    :param convenio: objeto de la clase Convenio que será actualizado.
    :param form: formulario ingresado por el usuario.
    :return: tablas de la DB actualizadas.
    """
    campos_actualizados = []
    # Actualizar campos
    if convenio.nombre != formato_nombre(form.nombre.data):
        convenio.nombre = formato_nombre(form.nombre.data)
        campos_actualizados.append('Nombre del convenio')
    if convenio.tipo != form.tipo.data:
        convenio.tipo = form.tipo.data
        campos_actualizados.append('Tipo del documento')
    convenio.id_convenio_padre = form.convenio_padre.data if form.tipo.data == 'Adendum' else None
    if convenio.id_coord_sii != int(form.coord_sii.data):
        convenio.id_coord_sii = form.coord_sii.data
        campos_actualizados.append('Coordinador SII')
    if convenio.id_sup_sii is not None and form.sup_sii.data == "0":
        convenio.id_sup_sii = None
        campos_actualizados.append('Suplente SII')
    elif convenio.id_sup_sii != int(form.sup_sii.data) and form.sup_sii.data != '0':
        convenio.id_sup_sii = form.sup_sii.data
        campos_actualizados.append('Suplente SII')
    if convenio.id_coord_ie is not None and form.sup_sii.data == '0':
        convenio.id_coord_ie = None
        campos_actualizados.append('Coordinador IE')
    elif convenio.id_coord_ie != int(form.coord_ie.data) and form.coord_ie.data != '0':
        convenio.id_coord_ie = form.coord_ie.data
        campos_actualizados.append('Coordinador IE')
    if convenio.id_sup_ie is not None and form.sup_ie.data == '0':
        convenio.id_sup_ie = None
        campos_actualizados.append('Suplente IE')
    elif convenio.id_sup_ie != int(form.sup_ie.data) and form.sup_ie.data != '0':
        convenio.id_sup_ie = form.sup_ie.data
        campos_actualizados.append('Suplente IE')
    if convenio.id_responsable_convenio_ie is not None and form.responsable_convenio_ie.data == '0':
        convenio.id_responsable_convenio_ie = None
        campos_actualizados.append('Responsable de convenio IE')
    elif convenio.id_responsable_convenio_ie != int(form.responsable_convenio_ie.data) and form.responsable_convenio_ie.data != '0':
        convenio.id_responsable_convenio_ie = form.responsable_convenio_ie.data
        campos_actualizados.append('Responsable de convenio  IE')
    if convenio.proyecto is not None and form.proyecto.data == "":
        convenio.proyecto = None
        campos_actualizados.append('Número de proyecto')
    elif form.proyecto.data != '' and convenio.proyecto != int(form.proyecto.data):
        convenio.proyecto = form.proyecto.data
        campos_actualizados.append('Número de proyecto')
    if convenio.gabinete_electronico is not None and form.gabinete_electronico.data == '':
        convenio.gabinete_electronico = None
        campos_actualizados.append('Número de Gabinete Electrónico')
    elif form.gabinete_electronico.data != '' and convenio.gabinete_electronico != int(form.gabinete_electronico.data):
        convenio.gabinete_electronico = form.gabinete_electronico.data
        campos_actualizados.append('Número de Gabinete Electrónico')

    # Subdirecciones involucradas
    # Agregar nuevas subdirecciones
    if sd_actuales != sd_seleccionadas:
        campos_actualizados.append('Subdirecciones involucradas')
    for sd in sd_seleccionadas:
        if sd not in sd_actuales:
            nueva_sd_involucrada = SdInvolucrada(
                id_convenio=convenio.id,
                id_subdireccion=sd
            )
            db.session.add(nueva_sd_involucrada)
    # Eliminar subdirecciones que no estén involucradas
    for sd in query_sd:
        if str(sd.id_subdireccion) not in sd_seleccionadas:
            db.session.delete(sd)

    # Estado
    reabierto, adendum = False, False
    if convenio.estado != form.estado.data:
        # Si el convenio deja de estar reemplazado
        if convenio.estado != 'Reemplazado':
            convenio.id_convenio_reemplazo = None
        convenio.estado = form.estado.data
        campos_actualizados.append('Estado')
        # Si el convenio entra en proceso nuevamente
        if convenio.estado == 'En proceso':
            # Asignar etapa última etapa en la que estaba
            ultima_etapa = TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == convenio.id,
                                                              TrayectoriaEtapa.id_etapa != 5)).order_by(TrayectoriaEtapa.ingreso.desc()).first()
            nueva_etapa = TrayectoriaEtapa(
                ingreso=date.today(),
                timestamp_ingreso=datetime.today(),
                id_convenio=convenio.id,
                id_etapa=ultima_etapa.id_etapa
            )
            db.session.add(nueva_etapa)
            # Asignar equipo último equipo en el que estaba
            ultimo_equipo = TrayectoriaEquipo.query.filter(TrayectoriaEquipo.id_convenio == convenio.id).order_by(TrayectoriaEquipo.ingreso.desc()).first()
            primer_equipo = TrayectoriaEquipo(
                id_convenio=convenio.id,
                id_equipo=ultimo_equipo.id_equipo,
                ingreso=date.today(),
                timestamp_ingreso=datetime.today()
            )
            db.session.add(primer_equipo)
            # Observación reapertura
            primera_observacion = BitacoraAnalista(
                observacion=(lambda tipo: f'Convenio vuelve a estar en proceso y se asigna a {ultimo_equipo.equipo.sigla} en {ultima_etapa.etapa.etapa}.'
                if tipo == 'Convenio' else f'Adendum vuelve a estar en proceso y se asigna a {ultimo_equipo.equipo.sigla} en {ultima_etapa.etapa.etapa}.')(convenio.tipo),
                fecha=date.today(),
                timestamp=datetime.today(),
                id_convenio=convenio.id,
                id_autor=current_user.id
            )
            db.session.add(primera_observacion)
            # Redirigir a página del convenio
            reabierto = True
        # Si el convenio es reemplazado
        elif convenio.estado == 'Reemplazado':
            # Asignar convenio de reemplazo
            convenio.id_convenio_reemplazo = form.convenio_reemplazo.data

        # Alertar si el convenio tiene adendum
        adendum_query = Convenio.query.filter_by(id_convenio_padre=convenio.id).first()
        if adendum_query and convenio.estado in ['Pausado', 'Reemplazado', 'Cancelado']:
           adendum = True

    # Agregar observación a la bitácora del analista
    if campos_actualizados:
        if 'Estado' in campos_actualizados:
           # Agregar el estado actualizado
           campos_actualizados[campos_actualizados.index('Estado')] = f'Estado: {convenio.estado}'
        nueva_observacion = BitacoraAnalista(
            observacion=f'Se ha modificado la información de {", ".join(campos_actualizados)} ',
            fecha=date.today(),
            timestamp=datetime.today(),
            id_convenio=convenio.id,
            id_autor=current_user.id
        )
        db.session.add(nueva_observacion)

    db.session.commit()
    if reabierto:
        return 'reabierto'
    elif adendum:
        return 'adendum'
    else:
        return None


def obtener_iniciales(nombre):
    """
    Devuelve las iniciales de un nombre dado.
    :param nombre: string
    :return: string con iniciales en mayúscula
    """
    if nombre != None:
        return "".join([palabra[0].upper() for palabra in nombre.split(" ")])
    else:
        return ""