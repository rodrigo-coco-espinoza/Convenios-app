from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify
from flask_login import current_user, login_required
from convenios_app.users.utils import admin_only, analista_only
from convenios_app.models import (Institucion, Equipo, Persona, Convenio, SdInvolucrada, BitacoraAnalista,
                                  BitacoraTarea, TrayectoriaEtapa, TrayectoriaEquipo, CatalogoWS, WSConvenio,
                                  RecepcionConvenio, Hito, HitosConvenio, EntregaConvenio, NominaEntrega)
from convenios_app.bitacoras.forms import (NuevoConvenioForm, EditarConvenioForm, NuevaBitacoraAnalistaForm,
                                           NuevaTareaForm, InfoConvenioForm, ETAPAS, AgregarRecepcionForm,
                                           RegistrarHitoForm, EditarRecepcionForm, AgregarEntregaForm,
                                           EditarEntregaForm)
from convenios_app import db
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import (actualizar_trayectoria_equipo, actualizar_convenio, obtener_iniciales,
                                           dias_habiles, formato_periodicidad)
from convenios_app.main.utils import generar_nombre_institucion, generar_nombre_convenio, formato_nombre
from datetime import datetime, date

bitacoras = Blueprint('bitacoras', __name__)

# TODO: actualizar ID en tabla final
ID_AIET = 1
HITOS = [hito for hito in Hito.query.all()]


@bitacoras.route('/bitacora')
@login_required
@analista_only
def bitacora():
    # CONVENIOS EN PROCESO
    # Crear select field con convenios
    convenios_proceso_query = Convenio.query.filter(Convenio.estado == 'En proceso').all()
    convenios_proceso_select = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in
                                convenios_proceso_query]
    convenios_proceso_select.sort(key=lambda tup: tup[1])
    convenios_proceso_select.insert(0, (0, 'Seleccione convenio para ver bitácora'))

    # Gráfico convenios en proceso
    grafico_proceso = [[ETAPAS[0][1], 0],
                       [ETAPAS[1][1], 0],
                       [ETAPAS[2][1], 0],
                       [ETAPAS[3][1], 0]]

    for convenio in convenios_proceso_query:
        etapa_actual = TrayectoriaEtapa.query.filter(
            and_(TrayectoriaEtapa.id_convenio == convenio.id, TrayectoriaEtapa.salida == None)).first()
        if etapa_actual.etapa.etapa == ETAPAS[0][1]:
            grafico_proceso[0][1] += 1
        elif etapa_actual.etapa.etapa == ETAPAS[1][1]:
            grafico_proceso[1][1] += 1
        elif etapa_actual.etapa.etapa == ETAPAS[2][1]:
            grafico_proceso[2][1] += 1
        elif etapa_actual.etapa.etapa == ETAPAS[3][1]:
            grafico_proceso[3][1] += 1
    # Tabla convenios por analista
    # TODO: CAMBIAR CUANDO SE TENGAN LOS USUARIOS (ASINGAR ROL)
    data_analistas_proceso = {
        'Cristian Gutiérrez Vergara': [0, 0],
        'Jorge Carrasco Reyes': [0, 0],
        'Juan Lipán Mella': [0, 0],
        'Rodrigo Espinoza Fuentes': [0, 0],
        'Susana Bahamonde Fortunatte': [0, 0],
        'Total': [0, 0]
    }

    # Tabla resumen convenios en proceso
    tabla_resumen_proceso = []
    for convenio in convenios_proceso_query:
        # Información analistas
        for nombre, convenios in data_analistas_proceso.items():
            if convenio.coord_sii.nombre == nombre:
                data_analistas_proceso[nombre][0] += 1
                data_analistas_proceso['Total'][0] += 1
            elif convenio.sup_sii != None and convenio.sup_sii.nombre == nombre:
                data_analistas_proceso[nombre][1] += 1
                data_analistas_proceso['Total'][1] += 1

        # Información resumen
        nombre = generar_nombre_convenio(convenio)
        observacion_query = BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == convenio.id,
                                                               BitacoraAnalista.estado != 'Eliminado')).order_by(
            BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).first()
        ultima_observacion = f'({datetime.strftime(observacion_query.fecha, "%d-%m-%Y")}) {observacion_query.observacion}'
        tarea_query = BitacoraTarea.query.filter(
            and_(BitacoraTarea.id_convenio == convenio.id, BitacoraTarea.estado == 'Pendiente')).order_by(
            BitacoraTarea.plazo.asc(), BitacoraTarea.timestamp.asc()).first()
        if tarea_query is None:
            proxima_tarea = 'Sin tareas pendientes'
        elif tarea_query.plazo <= date.today():
            proxima_tarea = f'<p style="display:inline" class="text-danger">({datetime.strftime(tarea_query.plazo, "%d-%m-%Y")})</p> {tarea_query.tarea}'
        else:
            proxima_tarea = f'({datetime.strftime(tarea_query.plazo, "%d-%m-%Y")}) {tarea_query.tarea}'
        coord = f'<p align="center">{obtener_iniciales(convenio.coord_sii.nombre)}<br>({(lambda sup: obtener_iniciales(sup.nombre) if sup else "")(convenio.sup_sii)})</p>'

        tabla_resumen_proceso.append([nombre, ultima_observacion, proxima_tarea, coord, convenio.id])

    # Ordenar tabla resumen
    tabla_resumen_proceso.sort(key=lambda lista: lista[0])
    # Agregar link al nombre del convenio y botar el id
    for convenio in tabla_resumen_proceso:
        convenio[
            0] = f'<a class="simple-link" href={url_for("bitacoras.bitacora_convenio", id_convenio=convenio[4])}>' \
                 f'{convenio[0]} <i class="fa-solid fa-keyboard fa-fw"></i></a>'
        convenio.pop()

    # CONVENIOS EN PRODUCCIÓN
    # Crear select field con convenios
    convenios_produccion_query = Convenio.query.filter(Convenio.estado == 'En producción').all()
    convenios_produccion_select = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in
                                   convenios_produccion_query]
    convenios_produccion_select.sort(key=lambda tup: tup[1])
    convenios_produccion_select.insert(0, (0, 'Seleccione convenio'))

    # Gráfico convenios en produccion
    grafico_produccion = [
        ['Convenios',
         Convenio.query.filter(and_(Convenio.estado == 'En producción', Convenio.tipo == 'Convenio')).count()],
        ['Adendum', Convenio.query.filter(and_(Convenio.estado == 'En producción', Convenio.tipo == 'Adendum')).count()]
    ]

    # Tabla convenios por analista
    data_analistas_produccion = {
        'Cristian Gutiérrez Vergara': [0, 0],
        'Jorge Carrasco Reyes': [0, 0],
        'Juan Lipán Mella': [0, 0],
        'Rodrigo Espinoza Fuentes': [0, 0],
        'Susana Bahamonde Fortunatte': [0, 0],
        'Total': [0, 0]
    }
    sin_asignar_produccion = 0
    # Tabla resumen convenios en produccion
    tabla_resumen_produccion = []
    for convenio in convenios_produccion_query:
        # Información analistas
        if convenio.coord_sii.nombre == 'Pamela Leyton Leyton':
            sin_asignar_produccion += 1
        for nombre, convenios in data_analistas_produccion.items():
            if convenio.coord_sii.nombre == nombre:
                data_analistas_produccion[nombre][0] += 1
                data_analistas_produccion['Total'][0] += 1
            elif convenio.sup_sii != None and convenio.sup_sii.nombre == nombre:
                data_analistas_produccion[nombre][1] += 1
                data_analistas_produccion['Total'][1] += 1

        # Información resumen
        nombre = generar_nombre_convenio(convenio)
        coordinador = f'<p align="center">{obtener_iniciales(convenio.coord_sii.nombre)}</p>'
        suplente = (lambda
                        suplente: f'<p align="center">{obtener_iniciales(suplente.nombre)}</p>' if suplente != None else '<p align="center">-</p>')(
            convenio.sup_sii)
        link_resolucion = (lambda
                               link: f'<a target="_blank" class="text-center" class="simple-link" href="{link}">'
                                     f'<i class="fas fa-eye pt-2 text-center btn-lg"></i></a>' if link else
        '<div class="text-center"><i class="fas fa-eye-slash pt-2 text-center text-muted btn-lg"></i></div>')(
            convenio.link_resolucion)

        tabla_resumen_produccion.append([nombre, coordinador, suplente, link_resolucion, convenio.id])

    # Ordenar tabla resumen
    tabla_resumen_produccion.sort(key=lambda lista: lista[0])
    # Agregar link al nombre del convenio y botar el id
    for convenio in tabla_resumen_produccion:
        convenio[
            0] = f'<a class="simple-link" href={url_for("bitacoras.bitacora_convenio", id_convenio=convenio[4])}>' \
                 f'{convenio[0]} <i class="fa-solid fa-keyboard fa-fw"></i></a>'
        convenio.pop()

    # OTROS CONVENIOS
    # Crear select field con convenios
    convenios_otros_query = Convenio.query.filter(
        and_(Convenio.estado != 'En proceso', Convenio.estado != 'En producción')).all()
    convenios_otros_select = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in
                              convenios_otros_query]
    convenios_otros_select.sort(key=lambda tup: tup[1])
    convenios_otros_select.insert(0, (0, 'Seleccione convenio para ver bitácora'))

    # Gráfico otros convenios
    grafico_otros = [
        ['Cancelados', Convenio.query.filter(Convenio.estado == 'Cancelado').count()],
        ['Pausados', Convenio.query.filter(Convenio.estado == 'Pausado').count()],
        ['Reemplazados', Convenio.query.filter(Convenio.estado == 'Reemplazado').count()]
    ]

    # Tabla resumen otros convenios
    tabla_resumen_otros = []
    for convenio in convenios_otros_query:
        nombre = generar_nombre_convenio(convenio)
        estado = convenio.estado
        coordinador = f'<p align="center">{obtener_iniciales(convenio.coord_sii.nombre)}</p>'
        suplente = (lambda
                        suplente: f'<p align="center">{obtener_iniciales(suplente.nombre)}</p>' if suplente != None else '<p align="center">-</p>')(
            convenio.sup_sii)
        tabla_resumen_otros.append([nombre, estado, coordinador, suplente, convenio.id])
    # Ordenar tabla
    tabla_resumen_otros.sort(key=lambda lista: lista[0])
    # Agregar link a la bitácora
    for convenio in tabla_resumen_otros:
        convenio[
            0] = f'<a class="simple-link" href={url_for("bitacoras.bitacora_convenio", id_convenio=convenio[4])}>' \
                 f'{convenio[0]} <i class="fa-solid fa-keyboard fa-fw"></i></a>'
        convenio.pop()

    # Cuenta convenios para gráficos
    cuenta = {
        'proceso': len(convenios_proceso_query),
        'produccion': len(convenios_produccion_query),
        'otros': len(convenios_otros_query)
    }
    return render_template('bitacoras/bitacora.html', convenios_proceso=convenios_proceso_select,
                           tabla_resumen_proceso=tabla_resumen_proceso, data_analistas_proceso=data_analistas_proceso,
                           convenios_produccion=convenios_produccion_select,
                           sin_asignar_produccion=sin_asignar_produccion,
                           data_analistas_produccion=data_analistas_produccion, cuenta=cuenta,
                           tabla_resumen_produccion=tabla_resumen_produccion, otros_convenios=convenios_otros_select,
                           tabla_resumen_otros=tabla_resumen_otros, grafico_proceso=grafico_proceso,
                           grafico_produccion=grafico_produccion, grafico_otros=grafico_otros)


@bitacoras.route('/bitacora_convenio/<int:id_convenio>', methods=['GET', 'POST'])
@login_required
@analista_only
def bitacora_convenio(id_convenio):
    # Crear select field con convenios
    convenios = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in
                 Convenio.query.all()]
    convenios.sort(key=lambda tup: tup[1])

    # Información de convenio
    convenio = Convenio.query.get(id_convenio)
    etapa = TrayectoriaEtapa.query.filter(
        and_(TrayectoriaEtapa.id_convenio == id_convenio, TrayectoriaEtapa.salida == None)).first()
    trayectoria_equipos_query = TrayectoriaEquipo.query.filter(
        and_(TrayectoriaEquipo.id_convenio == id_convenio, TrayectoriaEquipo.salida == None)). \
        order_by(TrayectoriaEquipo.ingreso.asc()).all()
    tareas_pendientes_query = BitacoraTarea.query.filter(and_(BitacoraTarea.id_convenio == id_convenio,
                                                              BitacoraTarea.estado == 'Pendiente')). \
        order_by(BitacoraTarea.plazo.asc(), BitacoraTarea.timestamp.asc()).all()
    tareas_pendientes = [(tarea.tarea, tarea.plazo, tarea.id) for tarea in tareas_pendientes_query]
    trayectoria_equipos = []
    for trayectoria in trayectoria_equipos_query:
        trayectoria_equipos.append({
            'id_trayectoria': trayectoria.id,
            'id_equipo': trayectoria.id_equipo,
            'ingreso': trayectoria.ingreso,
            'dias_equipo': dias_habiles(trayectoria.ingreso, date.today())
        })
    for i in range(4 - len(trayectoria_equipos_query)):
        trayectoria_equipos.append({
            'id_trayectoria': 0,
            'id_equipo': 0,
            'ingreso': "",
            'dias_equipo': ""
        })

    # Calcular días en proceso
    dias_en_proceso = 0
    for etapa in TrayectoriaEtapa.query.filter(TrayectoriaEtapa.id_convenio == id_convenio).order_by(
            TrayectoriaEtapa.ingreso.asc()).all():
        salida_etapa = (lambda salida: salida if salida != None else date.today())(etapa.salida)
        dias_en_proceso += dias_habiles(etapa.ingreso, salida_etapa)

    info_convenio = {
        'dias_proceso': dias_en_proceso,
        'etapa_actual': etapa.etapa.etapa,
        'dias_etapa': (lambda id_etapa: dias_habiles(etapa.ingreso, date.today()) if id_etapa != 5 else '')(
            etapa.id_etapa),
        'coord': convenio.coord_sii.nombre,
        'sup': (lambda convenio: convenio.sup_sii.nombre if convenio.id_sup_sii != None else "")(convenio),
        'equipos': trayectoria_equipos,
        'proyecto': convenio.proyecto,
        'link_resolucion': (lambda convenio: convenio.link_resolucion if convenio.link_resolucion != None else "")(
            convenio),
        'link_project': (lambda convenio: convenio.link_project if convenio.link_project != None else "")(
            convenio),
        'link_protocolo': (lambda institucion: institucion.link_protocolo if institucion.link_protocolo != None else "")(
            convenio.institucion),
        'link_repositorio': (lambda institucion: institucion.link_repositorio if institucion.link_repositorio != None else "")(
            convenio.institucion),
        'estado': convenio.estado
    }

    form_info = InfoConvenioForm(
        id_convenio=id_convenio,
        id_trayectoria=etapa.id,
        etapa=etapa.id_etapa,
        fecha_etapa=etapa.ingreso,
        id_trayectoria_1=trayectoria_equipos[0]['id_trayectoria'],
        equipo_1=trayectoria_equipos[0]['id_equipo'],
        fecha_equipo_1=trayectoria_equipos[0]['ingreso'],
        id_trayectoria_2=trayectoria_equipos[1]['id_trayectoria'],
        equipo_2=trayectoria_equipos[1]['id_equipo'],
        fecha_equipo_2=trayectoria_equipos[1]['ingreso'],
        id_trayectoria_3=trayectoria_equipos[2]['id_trayectoria'],
        equipo_3=trayectoria_equipos[2]['id_equipo'],
        fecha_equipo_3=trayectoria_equipos[2]['ingreso'],
        id_trayectoria_4=trayectoria_equipos[3]['id_trayectoria'],
        equipo_4=trayectoria_equipos[3]['id_equipo'],
        fecha_equipo_4=trayectoria_equipos[3]['ingreso'],
        fecha_firma_documento=convenio.fecha_documento,
        fecha_firma_resolucion=convenio.fecha_resolucion,
        nro_resolucion=convenio.nro_resolucion,
        gabinete_electronico=convenio.gabinete_electronico
    )

    ultimo_proyecto = (lambda convenio: convenio.proyecto if convenio.proyecto != None else 0)(
    Convenio.query.order_by(Convenio.proyecto.desc()).first())
    ultimo_proyecto_texto = (lambda
                                 convenio: f'Último proyecto registrado: {ultimo_proyecto}' if not convenio.proyecto else convenio.proyecto)(convenio)
    form_info.proyecto.render_kw = {'placeholder': ultimo_proyecto_texto}

    if 'informacion_convenio' in request.form and form_info.validate_on_submit():

        form_info_equipos = [
            (form_info.id_trayectoria_1.data, form_info.equipo_1.data, form_info.fecha_equipo_1.data),
            (form_info.id_trayectoria_2.data, form_info.equipo_2.data, form_info.fecha_equipo_2.data),
            (form_info.id_trayectoria_3.data, form_info.equipo_3.data, form_info.fecha_equipo_3.data),
            (form_info.id_trayectoria_4.data, form_info.equipo_4.data, form_info.fecha_equipo_4.data)
        ]

        # Actualizar trayectoria de etapas
        if etapa.id_etapa != int(form_info.etapa.data):
            # Si se finaliza el proceso
            if form_info.etapa.data == '5':
                # Finalizar etapa actual
                etapa.actualizar_trayectoria_etapa(form_info)
                # Finalizar etapa Finalizado
                ultima_etapa = TrayectoriaEtapa.query.filter(
                    and_(TrayectoriaEtapa.id_convenio == id_convenio, TrayectoriaEtapa.salida == None)).first()
                ultima_etapa.salida = form_info.fecha_etapa.data
                ultima_etapa.timestamp_salida = datetime.today()
                # Desasignar equipos de trabajo
                for equipo in form_info_equipos:
                    actualizar_trayectoria_equipo(equipo[0], '0', form_info.fecha_etapa.data, id_convenio)
                # Eliminar tareas pendientes
                for tarea in tareas_pendientes_query:
                    tarea.estado = 'Eliminado'
                    tarea.timestamp = datetime.today()
                # Dejar registro en la bitácora
                ultimo_registro_bitacora = BitacoraAnalista(
                    observacion='Se cambia etapa a: Finalizado',
                    fecha=form_info.fecha_etapa.data,
                    timestamp=datetime.today(),
                    id_convenio=id_convenio,
                    id_autor=current_user.id
                )
                db.session.add(ultimo_registro_bitacora)
                db.session.commit()

                flash(
                    f'{generar_nombre_convenio(convenio)} ha sido finalizado. No olvide cambiar el estado del {convenio.tipo}.',
                    'warning')
                return redirect(url_for('bitacoras.editar_convenio', id_convenio=id_convenio))
            else:
                etapa.actualizar_trayectoria_etapa(form_info)
                # Dejar registro en bitácora del analista
                observacion_cambio_etapa = BitacoraAnalista(
                    observacion=f"Se cambia etapa a: {dict(ETAPAS).get(int(form_info.etapa.data))}.",
                    fecha=form_info.fecha_etapa.data,
                    timestamp=datetime.today(),
                    id_convenio=id_convenio,
                    id_autor=current_user.id
                )
                db.session.add(observacion_cambio_etapa)
                db.session.commit()

        # Actualizar trayectoria de equipos de trabajo
        for equipo in form_info_equipos:
            actualizar_trayectoria_equipo(equipo[0], equipo[1], equipo[2], id_convenio)

        # Actualizar fechas de documento y resolución
        if convenio.fecha_documento != form_info.fecha_firma_documento.data:
            convenio.fecha_documento = form_info.fecha_firma_documento.data
            observacion_fecha_documento = BitacoraAnalista(
                observacion=f'Convenio se firma con fecha {form_info.fecha_firma_documento.data}',
                fecha=form_info.fecha_firma_documento.data,
                timestamp=datetime.today(),
                id_convenio=id_convenio,
                id_autor=current_user.id
            )
            db.session.add(observacion_fecha_documento)
        if convenio.fecha_resolucion != form_info.fecha_firma_resolucion.data:
            convenio.fecha_resolucion = form_info.fecha_firma_resolucion.data
            observacion_fecha_resolucion = BitacoraAnalista(
                observacion=f'Se publica resolución N°{form_info.nro_resolucion.data} con fecha {form_info.fecha_firma_resolucion.data}',
                fecha=form_info.fecha_firma_resolucion.data,
                timestamp=datetime.today(),
                id_convenio=id_convenio,
                id_autor=current_user.id
            )
            db.session.add(observacion_fecha_resolucion)

        # Actualizar número de resolución
        convenio.nro_resolucion = form_info.nro_resolucion.data
        # Actualizar número de proyecto
        if convenio.proyecto is not None and form_info.proyecto.data == "":
            convenio.proyecto = None
        elif form_info.proyecto.data != '' and convenio.proyecto != int(form_info.proyecto.data):
            convenio.proyecto = form_info.proyecto.data
        # Actualizar número de gabiente electrónico
        convenio.gabinete_electronico = form_info.gabinete_electronico.data

        # Actualizar link project
        if not convenio.link_project and convenio.link_project != form_info.link_project.data:
            convenio.link_project = form_info.link_project.data
        # Actualizar link resolución
        if not convenio.link_resolucion and convenio.link_resolucion != form_info.link_resolucion.data:
            convenio.link_resolucion = form_info.link_resolucion.data
        # Actualizar link protocolo técnico
        if not convenio.institucion.link_protocolo and convenio.institucion.link_protocolo != form_info.link_protocolo.data:
            convenio.institucion.link_protocolo = form_info.link_protocolo.data
        # Actualizar link repositorio
        if not convenio.institucion.link_repositorio and convenio.institucion.link_repositorio != form_info.link_repositorio.data:
            convenio.institucion.link_repositorio = form_info.link_repositorio.data

        db.session.commit()

        flash('Se ha actualizado la información del convenio.', 'success')
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

    # Formulario nueva bitacora analista
    # Obtener bitácora analista
    bitacora_analista = [(registro.observacion, datetime.strftime(registro.fecha, '%d-%m-%Y'), registro.id) for registro
                         in
                         BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == id_convenio,
                                                            BitacoraAnalista.estado != 'Eliminado')).
                             order_by(BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).all()]
    # TODO: cambiarlo a la función en main/utils

    form_nuevo = NuevaBitacoraAnalistaForm()
    if 'bitacora_analista' in request.form and form_nuevo.validate_on_submit():
        # Agregar nueva observación
        nueva_observacion = BitacoraAnalista(
            observacion=form_nuevo.observacion.data,
            fecha=form_nuevo.fecha.data,
            timestamp=datetime.today(),
            id_convenio=id_convenio,
            id_autor=current_user.id
        )
        db.session.add(nueva_observacion)
        db.session.commit()
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

    # Formulario nueva tarea
    form_tarea = NuevaTareaForm()
    if 'nueva_tarea' in request.form and form_tarea.validate_on_submit():
        # Agregar nueva tarea
        nueva_tarea = BitacoraTarea(
            tarea=form_tarea.tarea.data,
            plazo=form_tarea.plazo.data,
            timestamp=datetime.today(),
            id_convenio=id_convenio,
            id_autor=current_user.id
        )
        db.session.add(nueva_tarea)
        db.session.commit()
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

    # WEB SERVICES
    # WS asignados tabla
    ws_asignados_query = WSConvenio.query.filter(WSConvenio.id_convenio == id_convenio).all()
    ws_asignados = [{
        'id_asignado': ws.id,
        'activo': 'checked' if ws.estado else "",
        'nombre_aiet': ws.ws.nombre_aiet,
        'nombre_sdi': ws.ws.nombre_sdi,
        'metodo': ws.ws.metodo
        } for ws in ws_asignados_query]
    # Formulario para asignar WS
    ws_asignados_id = [webservice.id_ws for webservice in ws_asignados_query]
    ws_contribuyentes_query = CatalogoWS.query.filter(and_(CatalogoWS.categoria == 'Información de contribuyentes',
                                                           CatalogoWS.estado == 1, CatalogoWS.pisee == 0)).all()
    ws_contribuyentes = [
        {'id_ws': ws.id,
         'nombre_aiet': ws.nombre_aiet,
         'nombre_sdi': ws.nombre_sdi,
         'metodo': ws.metodo,
         'url': ws.url,
         'observacion': f'{"WS reservado. " if ws.reservado else ""}{ws.observacion if ws.observacion else ""}',
         'asignado': 'checked' if ws.id in ws_asignados_id else ""
         }
        for ws in ws_contribuyentes_query]
    ws_contribuyentes.sort(key=lambda dict: dict['nombre_aiet'])
    ws_tributaria_query = CatalogoWS.query.filter(and_(CatalogoWS.categoria == 'Información tributaria',
                                                       CatalogoWS.estado == 1, CatalogoWS.pisee == 0)).all()
    ws_tributaria = [
        {'id_ws': ws.id,
         'nombre_aiet': ws.nombre_aiet,
         'nombre_sdi': ws.nombre_sdi,
         'metodo': ws.metodo,
         'url': ws.url,
         'observacion': f'{"WS reservado. " if ws.reservado else ""}{ws.observacion if ws.observacion else ""}',
         'asignado': 'checked' if ws.id in ws_asignados_id else ""
         }
        for ws in ws_tributaria_query]
    ws_tributaria.sort(key=lambda dict: dict['nombre_aiet'])
    ws_bbrr_query = CatalogoWS.query.filter(and_(CatalogoWS.categoria == 'Información de bienes raíces',
                                                 CatalogoWS.estado == 1, CatalogoWS.pisee == 0)).all()
    ws_bbrr = [
        {'id_ws': ws.id,
         'nombre_aiet': ws.nombre_aiet,
         'nombre_sdi': ws.nombre_sdi,
         'metodo': ws.metodo,
         'url': ws.url,
         'observacion': f'{"WS reservado. " if ws.reservado else ""}{ws.observacion if ws.observacion else ""}',
         'asignado': 'checked' if ws.id in ws_asignados_id else ""
         }
        for ws in ws_bbrr_query]
    ws_bbrr.sort(key=lambda dict: dict['nombre_aiet'])
    ws_pisee_query = CatalogoWS.query.filter(and_(CatalogoWS.estado == 1, CatalogoWS.pisee == 1)).all()
    ws_pisee = [
        {'id_ws': ws.id,
         'nombre_aiet': ws.nombre_aiet,
         'nombre_sdi': ws.nombre_sdi,
         'metodo': ws.metodo,
         'url': ws.url,
         'observacion': f'{"WS reservado. " if ws.reservado else ""}{ws.observacion if ws.observacion else ""}',
         'asignado': 'checked' if ws.id in ws_asignados_id else ""
         }
        for ws in ws_pisee_query]
    ws_pisee.sort(key=lambda dict: dict['nombre_aiet'])
    ws_no_disponibles_query = CatalogoWS.query.filter(CatalogoWS.estado == 0).all()
    ws_no_disponibles = [
        {'id_ws': ws.id,
         'nombre_aiet': ws.nombre_aiet,
         'nombre_sdi': ws.nombre_sdi,
         'metodo': ws.metodo,
         'url': ws.url,
         'observacion': f'{"WS reservado. " if ws.reservado else ""}{ws.observacion if ws.observacion else ""}',
         'asignado': 'checked' if ws.id in ws_asignados_id else ""
         }
        for ws in ws_no_disponibles_query]
    ws_no_disponibles.sort(key=lambda dict: dict['nombre_aiet'])

    if 'asignar_ws' in request.form:
        mensaje = False
        ws_seleccionados = request.form.getlist('ws_checkbox')
        # Agregar nuevos WS
        for ws in ws_seleccionados:
            if int(ws) not in ws_asignados_id:
                nuevo_ws = WSConvenio(
                    id_convenio=id_convenio,
                    id_ws=int(ws),
                    estado=0
                )
                mensaje = True
                db.session.add(nuevo_ws)

        # Eliminar WS
        for ws in ws_asignados_query:
            if str(ws.id_ws) not in ws_seleccionados:
                db.session.delete(ws)
                mensaje = True

        if mensaje:
            # Dejar registgro en bitácora
            bitacora_ws = BitacoraAnalista(
                observacion='Se ha actualizado la información de Web Services.',
                fecha=date.today(),
                timestamp=datetime.today(),
                id_convenio=id_convenio,
                id_autor=current_user.id
            )
            db.session.add(bitacora_ws)
            db.session.commit()
            flash('Se ha actualizado la información de Web Services.', 'success')
            return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

    # RECEPCIÓN
    # Recepciones registradas
    recepciones_query = RecepcionConvenio.query.filter(RecepcionConvenio.id_convenio == id_convenio).all()
    recepciones_registradas = [{
        'id_recepcion': recepcion.id,
        'nombre': recepcion.nombre,
        'archivo': recepcion.archivo if recepcion.archivo else "",
        'periodo': formato_periodicidad(recepcion.periodicidad),
        'metodo': recepcion.metodo,
        'sd': recepcion.sd.sigla,
        'activo': 'checked' if recepcion.estado else ""
    } for recepcion in recepciones_query]
    # Formulario recepción de información
    sd_asociadas = SdInvolucrada.query.filter(SdInvolucrada.id_convenio == id_convenio).all()
    form_recepcion = AgregarRecepcionForm(id_convenio=id_convenio)
    form_recepcion.sd_recibe.choices = [(sd.id_subdireccion, sd.subdireccion.sigla) for sd in sd_asociadas]
    form_recepcion.sd_recibe.choices.sort(key=lambda tup: tup[1])
    form_recepcion.sd_recibe.choices.insert(0, (0, 'Seleccione Subdirección'))

    if 'agregar_recepcion' in request.form and form_recepcion.validate_on_submit():
        periodicidad = request.form.getlist('periodicidad_checkbox')
        # Comprobar que se elegió periodicidad correctamente
        if not periodicidad:
            flash('Debe seleccionar la periodicidad de la recepción.', 'danger')
            return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))
        elif any(item in ['En línea', 'Diario', 'Semanal', 'Mensual'] for item in periodicidad) and len(
                periodicidad) > 1:
            flash('No puede eligir más de una periodicidad.', 'danger')
            return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))
        # Agregar recepción
        nueva_recepcion = RecepcionConvenio(
            id_convenio=id_convenio,
            id_sd=form_recepcion.sd_recibe.data,
            nombre=form_recepcion.nombre.data,
            archivo=form_recepcion.archivo.data,
            periodicidad='-'.join(periodicidad),
            metodo=form_recepcion.metodo.data,
            estado=0
        )
        db.session.add(nueva_recepcion)
        db.session.commit()
        flash('Se ha agregado nueva recepción de información.', 'success')
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

    # ENTREGAS
    # Entregas registradas
    entregas_query = EntregaConvenio.query.filter(EntregaConvenio.id_convenio == id_convenio).all()
    entregas_registradas = [{
        'id_entrega': entrega.id,
        'nombre': entrega.nombre,
        'archivo': entrega.archivo if entrega.archivo else "",
        'periodo': formato_periodicidad(entrega.periodicidad),
        'metodo': entrega.metodo,
        'sd': f'{entrega.sd_prepara.sigla}/{entrega.sd_envia.sigla}',
        'nomina': 'Sí' if entrega.nomina else 'No',
        'activo': 'checked' if entrega.estado else ''
    } for entrega in entregas_query]
    # Formulario entrega de información
    form_entrega = AgregarEntregaForm(id_convenio_entrega=id_convenio)
    form_entrega.sd_prepara.choices = [(sd.id_subdireccion, sd.subdireccion.sigla) for sd in sd_asociadas]
    form_entrega.sd_prepara.choices.sort(key=lambda tup: tup[1])
    form_entrega.sd_prepara.choices.insert(0, (0, 'Seleccione Subidirección'))
    form_entrega.sd_envia.choices = form_entrega.sd_prepara.choices
    # Obtener nóminas registradas en la institución y añadir al select
    nominas_registradas_lista = [(0, 'Seleccione nómina existente o deje en blanco para agregar nueva')]
    nominas_registradas_query = NominaEntrega.query.filter(NominaEntrega.id_institucion == convenio.id_institucion).all()
    for nomina in nominas_registradas_query:
        nominas_registradas_lista.append((nomina.id, nomina.archivo))
    form_entrega.nomina_registrada.choices = nominas_registradas_lista

    if 'agregar_entrega' in request.form and form_entrega.validate_on_submit():
        # Comprobar que se seleccionó una periodicidad
        periodicidad_entrega = request.form.getlist('periodicidad_entrega_checkbox')
        if not periodicidad_entrega:
            flash('Debe seleccionar la periodicidad de la entrega.', 'danger')
            return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))
        elif any(item in ['En línea', 'Diario', 'Semanal', 'Mensual'] for item in periodicidad_entrega) and len(periodicidad_entrega) > 1:
            flash('No puede elegir más de una periodicidad para la entrega..', 'danger')
            return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio)) 

        # Agregar nómina si corresponde
        if form_entrega.requiere_nomina.data == 'Sí' and int(form_entrega.nomina_registrada.data) == 0:
                # Comprobar la periodicidad de la nómina
                periodicidad_nomina = request.form.getlist('periodicidad_nomina_checkbox')
                if not periodicidad_nomina:
                    flash('Debe seleccionar la periodicidad de la nómina', 'danger')
                    return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))
                elif any(item in ['En línea', 'Diario', 'Semanal', 'Mensual'] for item in periodicidad_nomina) and len(periodicidad_nomina) > 1:
                    flash('Np puede elegir más de una periodicidad para la nómina.', 'danger')
                    return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

                # Añadir nómina la BBDD
                nueva_nomina = NominaEntrega(
                   archivo=form_entrega.nomina_archivo.data,
                   metodo=form_entrega.nomina_metodo.data,
                   periodicidad='-'.join(periodicidad_entrega),
                   id_institucion=convenio.id_institucion
                )
                db.session.add(nueva_nomina)
                db.session.commit()

        # Agregar entrega
        nueva_entrega = EntregaConvenio(
            id_convenio=id_convenio,
            nombre=form_entrega.nombre_entrega.data,
            archivo=form_entrega.archivo_entrega.data,
            periodicidad='-'.join(periodicidad_entrega),
            metodo=form_entrega.metodo_entrega.data,
            estado=0,
            id_sd_prepara=form_entrega.sd_prepara.data,
            id_sd_envia=form_entrega.sd_envia.data
        )
        # Vincular nómina con la entrega
        if form_entrega.requiere_nomina.data == 'Sí':
            if int(form_entrega.nomina_registrada.data) == 0:
                nueva_entrega.id_nomina = nueva_nomina.id
            else: 
                nueva_entrega.id_nomina = form_entrega.nomina_registrada.data
        
        db.session.add(nueva_entrega)
        db.session.commit()
        
        flash('Se ha agregado nueva entrega de información.', 'success')
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

    # HITOS
    # Ver hitos registrados
    hitos_registrados_query = HitosConvenio.query.filter(HitosConvenio.id_convenio == id_convenio).all()
    hitos_registrados = [{'id_registro': hito.id,
                          'hito': hito.hito.nombre,
                          'fecha': datetime.strftime(hito.fecha, "%d-%m-%Y"),
                          'minuta': hito.minuta,
                          'grabacion': hito.grabacion
                          }
                         for hito in hitos_registrados_query]
    # Formulario registro de hitos
    id_hitos_registrados = [hito.id_hito for hito in hitos_registrados_query]
    hitos_faltantes = [(hito.id, hito.nombre) for hito in HITOS if hito.id not in id_hitos_registrados]
    form_hitos = RegistrarHitoForm(id_convenio=id_convenio)
    form_hitos.hito.choices = hitos_faltantes
    form_hitos.hito.choices.insert(0, (0, 'Seleccionar hito'))

    if 'nuevo_hito' in request.form and form_hitos.validate_on_submit():
        choices = dict(form_hitos.hito.choices)
        registar_hito = HitosConvenio(
            id_convenio=id_convenio,
            id_hito=form_hitos.hito.data,
            fecha=form_hitos.fecha.data,
            timestamp=datetime.today(),
            minuta=form_hitos.minuta.data,
            grabacion=form_hitos.grabacion.data
        )

        comentario_hito = BitacoraAnalista(
            id_convenio=id_convenio,
            observacion=f'Se realiza el hito {choices[int(form_hitos.hito.data)]}.',
            fecha=form_hitos.fecha.data,
            timestamp=datetime.today(),
            id_autor=current_user.id
        )

        db.session.add(registar_hito)
        db.session.add(comentario_hito)
        db.session.commit()

        flash('Se ha registrado el hito exitosamente.', 'success')
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

    # Actualizar estados del intercambio de información
    if 'estados_intercambio' in request.form:
        # Actualizar estado de las recepciones
        recepciones_form = request.form.getlist('estadoRecepcion_checkbox')
        for recepcion in recepciones_registradas:
            recepcion_por_actualizar = RecepcionConvenio.query.get(recepcion['id_recepcion'])
            if str(recepcion['id_recepcion']) in recepciones_form:
                recepcion_por_actualizar.estado = True
            else:
                recepcion_por_actualizar.estado = False

        # Actualizar estado de las entregas
        entregas_form = request.form.getlist('estadoEntrega_checkbox')
        for entrega in entregas_registradas:
            entrega_por_actualizar = EntregaConvenio.query.get(entrega['id_entrega'])
            if str(entrega['id_entrega']) in entregas_form:
                entrega_por_actualizar.estado = True
            else:
                entrega_por_actualizar.estado = False

        # Actualizar estado de los WS
        ws_form = request.form.getlist('estadoWS_checkbox')
        for ws in ws_asignados:
            ws_por_actualizar = WSConvenio.query.get(ws['id_asignado'])
            if str(ws['id_asignado']) in ws_form:
                ws_por_actualizar.estado = True
            else:
                ws_por_actualizar.estado = False
        db.session.commit()

        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

    # Editar recepción de información
    editar_recepcion_form = EditarRecepcionForm()
    if 'editar_recepcion' in request.form and editar_recepcion_form.validate_on_submit():
        recepcion_a_editar = RecepcionConvenio.query.get(editar_recepcion_form.id_recepcion_editar.data)
        recepcion_a_editar.nombre = editar_recepcion_form.nombre_editar.data
        recepcion_a_editar.archivo = editar_recepcion_form.archivo_editar.data
        recepcion_a_editar.id_sd = editar_recepcion_form.sd_recibe_editar.data
        recepcion_a_editar.metodo = editar_recepcion_form.metodo_editar.data

        periodicidad = request.form.getlist('editarPeriodicidad_checkbox')
        recepcion_a_editar.periodicidad = '-'.join(periodicidad)
        db.session.commit()

        flash(f'Se ha actualizado la información de {editar_recepcion_form.nombre_editar.data}', 'success')
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

    # Editar entrega de información
    editar_entrega_form = EditarEntregaForm()
    editar_entrega_form.sd_prepara_editar.choices = [(sd.id_subdireccion, sd.subdireccion.sigla) for sd in sd_asociadas]
    editar_entrega_form.sd_envia_editar.choices = [(sd.id_subdireccion, sd.subdireccion.sigla) for sd in sd_asociadas]
    editar_entrega_form.nomina_registrada_editar.choices =  form_entrega.nomina_registrada.choices
    if 'editar_entrega' in request.form and editar_entrega_form.validate_on_submit():
        # Actualizar datos de la entrega
        entrega_a_editar = EntregaConvenio.query.get(editar_entrega_form.id_entrega_editar.data)
        print(entrega_a_editar)
        entrega_a_editar.nombre = editar_entrega_form.nombre_entrega_editar.data
        entrega_a_editar.archivo = editar_entrega_form.archivo_entrega_editar.data
        entrega_a_editar.id_sd_prepara = int(editar_entrega_form.sd_prepara_editar.data)
        entrega_a_editar.id_sd_envia = int(editar_entrega_form.sd_envia_editar.data)
        entrega_a_editar.metodo = editar_entrega_form.metodo_entrega_editar.data

        periodicida_entrega = request.form.getlist('editar_periodicidad_entrega_checkbox')
        entrega_a_editar.periodicidad = '-'.join(periodicida_entrega)

        # Actualizar o agregar datos de nómina
        if editar_entrega_form.requiere_nomina_editar.data == 'Sí':
            periodicidad_nomina = request.form.getlist('editar_periodicidad_nomina_checkbox')
            # Si utiliza una nómina registrada
            if int(editar_entrega_form.nomina_registrada_editar.data) != 0:
                # Actualizar nómina actual
                if entrega_a_editar.id_nomina and int(entrega_a_editar.id_nomina) == int(editar_entrega_form.nomina_registrada_editar.data):
                    nomina_a_editar = NominaEntrega.query.get(editar_entrega_form.nomina_registrada_editar.data)
                    nomina_a_editar.archivo = editar_entrega_form.nomina_archivo_editar.data
                    nomina_a_editar.metodo = editar_entrega_form.nomina_metodo_editar.data
                    nomina_a_editar.periodicidad = '-'.join(periodicidad_nomina)

                else:    
                # Cambiar de nómina
                    entrega_a_editar.id_nomina = editar_entrega_form.nomina_registrada_editar.data
            # Si se agrega nueva nómina
            else:
                 # Añadir nómina la BBDD
                nueva_nomina = NominaEntrega(
                   archivo=editar_entrega_form.nomina_archivo_editar.data,
                   metodo=editar_entrega_form.nomina_metodo_editar.data,
                   periodicidad='-'.join(periodicidad_nomina),
                   id_institucion=convenio.id_institucion
                )
                db.session.add(nueva_nomina)
                db.session.commit()
                # Asignar nómina a la entrega
                entrega_a_editar.id_nomina = nueva_nomina.id
                
        else:
            entrega_a_editar.id_nomina = None
        db.session.commit()

        flash(f'Se ha actualizado la información de {editar_entrega_form.nombre_entrega_editar.data}', 'success')
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))

    return render_template('bitacoras/bitacora_convenio.html', convenios=convenios, id_convenio=id_convenio,
                           form_nuevo=form_nuevo, bitacora_analista=bitacora_analista, form_tarea=form_tarea,
                           tareas_pendientes=tareas_pendientes, hoy=date.today(), info_convenio=info_convenio,
                           form_info=form_info, ws_contribuyentes=ws_contribuyentes, ws_tributaria=ws_tributaria,
                           ws_bbrr=ws_bbrr, ws_pisee=ws_pisee, ws_no_disponibles=ws_no_disponibles,
                           form_recepcion=form_recepcion, form_hitos=form_hitos, hitos_registrados=hitos_registrados,
                           recepciones=recepciones_registradas, ws_asignados=ws_asignados,
                           editar_recepcion_form=editar_recepcion_form, form_entrega=form_entrega, entregas=entregas_registradas,
                           editar_entrega_form=editar_entrega_form)


@bitacoras.route('/borrar_bitacora_analista/<int:id_comentario>/<int:id_convenio>')
@login_required
@analista_only
def borrar_bitacora_analista(id_comentario, id_convenio):
    comentario = BitacoraAnalista.query.get(id_comentario)
    comentario.estado = 'Eliminado'
    db.session.commit()
    flash(f'Se ha eliminado el registro "{comentario.fecha} {comentario.observacion}"', 'warning')
    return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))


@bitacoras.route('/completar_tarea/<int:id_tarea>/<int:id_convenio>/<int:id_persona>')
@login_required
@analista_only
def completar_tarea(id_tarea, id_convenio, id_persona):
    tarea = BitacoraTarea.query.get(id_tarea)
    tarea.estado = 'Completado'

    # Dejar registro en la bitácora
    registro_bitacora = BitacoraAnalista(
        observacion=f'Completado: {tarea.tarea}',
        fecha=date.today(),
        timestamp=datetime.today(),
        id_convenio=id_convenio,
        id_autor=current_user.id
    )
    db.session.add(registro_bitacora)
    db.session.commit()

    if id_persona == 0:
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))
    else:
        flash('Se ha completado la tarea.', 'success')
        return redirect(url_for('users.mis_convenios', id_persona=id_persona))


@bitacoras.route('/borrar_tarea/<int:id_tarea>/<int:id_convenio>/<int:id_persona>')
@login_required
@analista_only
def borrar_tarea(id_tarea, id_convenio, id_persona):
    tarea = BitacoraTarea.query.get(id_tarea)
    tarea.estado = 'Eliminado'
    db.session.commit()
    # Si id_persona es 0, la solicitud viene de la bitácora, en caso contrario proviene de Mis convenios
    if id_persona == 0:
        flash(f'Se ha eliminado la tarea "{tarea.plazo} {tarea.tarea}"', 'warning')
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))
    else:
        flash(f'Se ha eliminado la tarea "{tarea.plazo} {tarea.tarea}"', 'warning')
        return redirect(url_for('users.mis_convenios', id_persona=id_persona))


@bitacoras.route('/editar_convenio/<int:id_convenio>', methods=['GET', 'POST'])
@login_required
@analista_only
def editar_convenio(id_convenio):
    # Convenio a editar
    convenio_seleccionado = Convenio.query.get(id_convenio)

    # Crear select field con convenios
    convenios = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in
                 Convenio.query.order_by(Convenio.nombre.asc()).all()]
    convenios.sort(key=lambda tup: tup[1])
    convenios.insert(0, (0, 'Agregar nuevo convenio'))
    # Crear formulario convenio
    personas_aiet = [(persona.id, persona.nombre) for persona in
                     Persona.query.filter_by(id_equipo=ID_AIET).order_by(Persona.nombre.asc()).all()]
    personas_aiet.append((6, 'SDGEET'))
    personas_aiet.insert(0, (0, 'Seleccionar'))
    personas_ie = [(persona.id, persona.nombre) for persona in
                   Persona.query.filter_by(id_institucion=convenio_seleccionado.id_institucion).all()]
    personas_ie.insert(0, (0, 'Seleccionar'))
    subdirecciones = [(str(subdireccion.id), subdireccion.sigla) for subdireccion in Equipo.query.filter(
        and_(Equipo.sigla != 'AIET', Equipo.sigla != 'IE', Equipo.sigla != 'GDIR')).order_by(Equipo.sigla.asc()).all()]
    convenios_reemplazo = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in
                           Convenio.query.filter(and_(Convenio.id_institucion == convenio_seleccionado.id_institucion,
                                                      or_(Convenio.estado == 'En producción',
                                                          Convenio.estado == 'En proceso'),
                                                      Convenio.id != convenio_seleccionado.id)).order_by(
                               Convenio.nombre.asc()).all()]
    convenios_reemplazo.insert(0, (0, 'Seleccionar'))
    
    form_editar_convenio = EditarConvenioForm()
    query = Convenio.query.filter(
        and_(Convenio.tipo == 'Convenio', Convenio.id_institucion == convenio_seleccionado.id_institucion)).all()
    convenios_institucion = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in query if
                             convenio.estado == 'En proceso' or convenio.estado == 'En producción']
    convenios_institucion.insert(0, (0, 'Seleccionar'))
    form_editar_convenio.convenio_padre.choices = convenios_institucion
    form_editar_convenio.coord_sii.choices = personas_aiet
    form_editar_convenio.sup_sii.choices = personas_aiet
    form_editar_convenio.coord_ie.choices = personas_ie
    form_editar_convenio.sup_ie.choices = personas_ie
    form_editar_convenio.responsable_convenio_ie.choices = personas_ie
    query_sd = SdInvolucrada.query.filter_by(id_convenio=id_convenio).all()
    sd_involucradas = [str(subdireccion.id_subdireccion) for subdireccion in query_sd]
    form_editar_convenio.convenio_reemplazo.choices = convenios_reemplazo
    form_editar_convenio.institucion.render_kw = {'disabled': 'disabled'}

    

    info_convenio = {
        'id_convenio': convenio_seleccionado.id,
        'id_institucion': convenio_seleccionado.id_institucion,
        'institucion': generar_nombre_institucion(convenio_seleccionado.institucion),
        'nombre': convenio_seleccionado.nombre,
        'tipo': convenio_seleccionado.tipo,
        'convenio_padre': (lambda convenio: 0 if not convenio.id_convenio_padre else convenio.id_convenio_padre)(
            convenio_seleccionado),
        'coord_sii': convenio_seleccionado.id_coord_sii,
        'sup_sii': (lambda sup_sii: 0 if not sup_sii.id_sup_sii else sup_sii.id_sup_sii)(convenio_seleccionado),
        'coord_ie': (lambda coord_ie: 0 if not coord_ie.id_coord_ie else coord_ie.id_coord_ie)(convenio_seleccionado),
        'sup_ie': (lambda sup_ie: 0 if not sup_ie.id_sup_ie else sup_ie.id_sup_ie)(convenio_seleccionado),
        'responsable_convenio_ie': (
            lambda resp_ie: 0 if not resp_ie.id_responsable_convenio_ie else resp_ie.id_responsable_convenio_ie)(
            convenio_seleccionado),
        'sd_involucradas': sd_involucradas,
        'gabinete_electronico': (
            lambda convenio: "" if not convenio.gabinete_electronico else convenio.gabinete_electronico)(
            convenio_seleccionado),
        'estado': convenio_seleccionado.estado,
        'convenio_reemplazo': (
            lambda convenio: 0 if not convenio.id_convenio_reemplazo else convenio.id_convenio_reemplazo)(
            convenio_seleccionado)
    }

    if form_editar_convenio.validate_on_submit():
        respuesta = actualizar_convenio(convenio=convenio_seleccionado, form=form_editar_convenio,
                                        sd_actuales=sd_involucradas, query_sd=query_sd,
                                        sd_seleccionadas=request.form.getlist('sd_checkbox'))
        flash(f'Se ha actualizado {generar_nombre_convenio(convenio_seleccionado)}', 'success')
        if respuesta == 'reabierto':
            return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))
        elif respuesta == 'adendum':
            flash(f'El {convenio_seleccionado.tipo} tiene asociado adendum. Por favor, actualizar.', 'warning')
            return redirect(url_for('bitacoras.editar_convenio', id_convenio=id_convenio))
        return redirect(url_for('bitacoras.editar_convenio', id_convenio=id_convenio))

    return render_template('bitacoras/editar_convenio.html', id_convenio=id_convenio, convenios=convenios,
                           form_editar_convenio=form_editar_convenio, info_convenio=info_convenio)


@bitacoras.route('/nuevo_convenio', methods=['GET', 'POST'])
@login_required
@analista_only
def agregar_convenio():
    # Crear select field con convenios
    convenios = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in
                 Convenio.query.order_by(Convenio.nombre.asc()).all()]
    convenios.sort(key=lambda tup: tup[1])
    convenios.insert(0, (0, 'Seleccione convenio para editar'))

    # Crear formulario convenio
    instituciones = [(institucion.id, generar_nombre_institucion(institucion)) for institucion in
                     Institucion.query.order_by(Institucion.nombre.asc()).all()]
    instituciones.insert(0, (0, 'Seleccionar'))
    personas_aiet = [(persona.id, persona.nombre) for persona in
                     Persona.query.filter_by(id_equipo=ID_AIET).order_by(Persona.nombre.asc()).all()]
    personas_aiet.append((6, 'SDGEET'))
    personas_aiet.insert(0, (0, 'Seleccionar'))
    subdirecciones = [(str(subdireccion.id), subdireccion.sigla) for subdireccion in Equipo.query.filter(
        and_(Equipo.sigla != 'AIET', Equipo.sigla != 'IE', Equipo.sigla != 'GDIR')).order_by(Equipo.sigla.asc()).all()]

    form_convenio = NuevoConvenioForm()
    form_convenio.institucion.choices = instituciones
    form_convenio.coord_sii.choices = personas_aiet
    form_convenio.sup_sii.choices = personas_aiet

    # Agregar nuevo convenio
    if form_convenio.validate_on_submit():
        # Crear objeto convenio
        nuevo_convenio = Convenio(
            nombre=formato_nombre(form_convenio.nombre.data),
            tipo=form_convenio.tipo.data,
            estado='En proceso',
            id_institucion=form_convenio.institucion.data,
            id_coord_sii=form_convenio.coord_sii.data
        )
        # Agregar convenio padre si es adendum
        if form_convenio.tipo.data == 'Adendum':
            nuevo_convenio.id_convenio_padre = form_convenio.convenio_padre.data
        # Agregar personas si existen
        if int(form_convenio.sup_sii.data) != 0:
            nuevo_convenio.id_sup_sii = form_convenio.sup_sii.data
        if int(form_convenio.coord_ie.data) != 0:
            nuevo_convenio.id_coord_ie = form_convenio.coord_ie.data
        if int(form_convenio.sup_ie.data) != 0:
            nuevo_convenio.id_sup_ie = form_convenio.sup_ie.data
        if int(form_convenio.responsable_convenio_ie.data) != 0:
            nuevo_convenio.id_responsable_convenio_ie = form_convenio.responsable_convenio_ie.data
        # Agregar a la base de datos
        db.session.add(nuevo_convenio)
        db.session.commit()
        # Agregar primer registro de bitácora TODO: agregar tareas
        primera_observacion = BitacoraAnalista(
            observacion=(lambda tipo: 'Ingresa convenio a la base de datos.'
            if tipo == 'Convenio' else 'Ingresa adendum a la base de datos.')(form_convenio.tipo.data),
            fecha=date.today(),
            timestamp=datetime.today(),
            id_convenio=nuevo_convenio.id,
            id_autor=current_user.id
        )
        db.session.add(primera_observacion)

        # Agregar etapa inicial
        primera_etapa = TrayectoriaEtapa(
            id_convenio=nuevo_convenio.id,
            id_etapa=1,
            ingreso=date.today(),
            timestamp_ingreso=datetime.today()
        )
        db.session.add(primera_etapa)

        # Asignar AIET como equipo inicial
        primer_equipo = TrayectoriaEquipo(
            id_convenio=nuevo_convenio.id,
            id_equipo=1,
            ingreso=date.today(),
            timestamp_ingreso=datetime.today()
        )
        db.session.add(primer_equipo)

        # Agregar subdirecciones involucradas
        convenio_recien_agregado = Convenio.query.filter(and_(Convenio.nombre == nuevo_convenio.nombre,
                                                              Convenio.id_institucion == nuevo_convenio.id_institucion)).first()
        sd_seleccionadas = request.form.getlist('sd_checkbox')
        for subdireccion in sd_seleccionadas:
            nueva_sd_involucrada = SdInvolucrada(
                id_convenio=convenio_recien_agregado.id,
                id_subdireccion=subdireccion
            )
            db.session.add(nueva_sd_involucrada)
        db.session.commit()
        flash(f'Se ha agregado {generar_nombre_convenio(nuevo_convenio)} correctamente.', 'success')
        return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=convenio_recien_agregado.id))

    return render_template('bitacoras/nuevo_convenio.html', convenios=convenios, form_convenio=form_convenio)


@bitacoras.route('/obtener_personas_ie/<int:id_institucion>')
@login_required
@analista_only
def obtener_personas_ie(id_institucion):
    lista_personas = [{'nombre': persona.nombre,
                       'id': persona.id} for persona in Persona.query.filter_by(id_institucion=id_institucion).all()]
    return jsonify(lista_personas)


@bitacoras.route('/obtener_convenios_institucion/<int:id_institucion>')
@login_required
@analista_only
def obtener_convenios_institucion(id_institucion):
    query = Convenio.query.filter(and_(Convenio.tipo == 'Convenio', Convenio.id_institucion == id_institucion)).all()
    convenios = [{'nombre': generar_nombre_convenio(convenio),
                  'id': convenio.id} for convenio in query if
                 convenio.estado == 'En proceso' or convenio.estado == 'En producción']
    return jsonify(convenios)


@bitacoras.route('/eliminar_hito/<int:id_hito>')
@login_required
@analista_only
def eliminar_hito(id_hito):
    hito = HitosConvenio.query.get(id_hito)
    nombre_hito = hito.hito.nombre
    id_convenio = hito.id_convenio
    db.session.delete(hito)
    db.session.commit()
    flash(f'Se ha eliminado el hito {nombre_hito}', 'success')
    return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))


@bitacoras.route('/eliminar_ws/<int:id_asignado>')
@login_required
@analista_only
def eliminar_ws(id_asignado):
    ws_asignado = WSConvenio.query.get(id_asignado)
    ws = ws_asignado.ws.nombre_aiet
    id_convenio = ws_asignado.convenio.id
    db.session.delete(ws_asignado)
    db.session.commit()
    flash(f'Se ha eliminado el WS {ws}', 'success')
    return redirect(url_for('bitacoras.bitacora_convenio', id_convenio=id_convenio))


@bitacoras.route('/obtener_info_recepcion/<int:id_recepcion>')
@login_required
@analista_only
def obtener_info_recepcion(id_recepcion):
    recepcion_query = RecepcionConvenio.query.get(id_recepcion)

    # Choices del select SD
    choices_sd = {sd.subdireccion.sigla: sd.id_subdireccion for sd in SdInvolucrada.query.filter(SdInvolucrada.id_convenio == recepcion_query.id_convenio).all()}

    recepcion = {
        'id_recepcion': recepcion_query.id,
        'nombre': recepcion_query.nombre,
        'carpeta': recepcion_query.carpeta if recepcion_query.carpeta else "",
        'archivo': recepcion_query.archivo if recepcion_query.archivo else "",
        'metodo': recepcion_query.metodo,
        'sd': recepcion_query.id_sd,
        'choices_sd': choices_sd
    }
    # Periodicidad de la recepción
    if '-' in recepcion_query.periodicidad:
        recepcion['periodo'] = recepcion_query.periodicidad.split('-')
    else:
        recepcion['periodo'] = [recepcion_query.periodicidad]

    return recepcion


@bitacoras.route('/obtener_info_entrega/<int:id_entrega>')
@login_required
@analista_only
def obtener_info_entrega(id_entrega):
    entrega_query = EntregaConvenio.query.get(id_entrega)

    entrega = {
        'id_entrega': id_entrega,
        'nombre': entrega_query.nombre,
        'archivo': entrega_query.archivo if entrega_query.archivo else "",
        'metodo': entrega_query.metodo,
        'sd_prepara': entrega_query.id_sd_prepara,
        'sd_envia': entrega_query.id_sd_envia,
        'requiere_nomina': 'Sí' if entrega_query.id_nomina else 'No'
    }

    # Periodicida de la entrega
    if '-' in entrega_query.periodicidad: 
        entrega['periodo'] = entrega_query.periodicidad.split('-')
    else:
        entrega['periodo'] = [entrega_query.periodicidad]
    
    # Información de nómina si existe
    if entrega_query.id_nomina:
        nomina_query = NominaEntrega.query.get(entrega_query.id_nomina)
        entrega['id_nomina'] = nomina_query.id
        entrega['archivo_nomina'] = nomina_query.archivo
        entrega['metodo_nomina'] = nomina_query.metodo

        if '-' in nomina_query.periodicidad:
            entrega['periodo_nomina'] = nomina_query.periodicidad.split('-')
        else:
            entrega['periodo_nomina'] = [nomina_query.periodicidad]

    return entrega


@bitacoras.route('/obtener_info_nomina/<int:id_nomina>')
@login_required
@analista_only
def obtener_info_nomina(id_nomina):
    nomina_query = NominaEntrega.query.get(id_nomina)
    nomina = {
        'id_nomina': nomina_query.id,
        'archivo_nomina': nomina_query.archivo,
        'metodo_nomina': nomina_query.metodo
    }

    if '-' in nomina_query.periodicidad:
        nomina['periodo_nomina'] = nomina_query.periodicidad.split('-')
    else:
         nomina['periodo_nomina'] = [nomina_query.periodicidad]

    return nomina