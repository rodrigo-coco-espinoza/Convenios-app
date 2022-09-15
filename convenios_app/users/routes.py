from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify
from convenios_app.models import (Institucion, Equipo, Persona, Convenio, SdInvolucrada, BitacoraAnalista,
                                  BitacoraTarea, TrayectoriaEtapa, TrayectoriaEquipo, User)
from convenios_app.users.forms import RegistrationForm, LoginForm
from convenios_app.bitacoras.forms import ETAPAS
from convenios_app.informes.forms import MisConveniosInfoConvenioForm, MisConveniosBitacoraForm, MisConveniosTareaForm
from convenios_app import db, bcrypt
from convenios_app.users.utils import admin_only, analista_only
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import actualizar_trayectoria_equipo, obtener_iniciales, dias_habiles
from convenios_app.main.utils import generar_nombre_institucion, generar_nombre_convenio, formato_nombre
from convenios_app.informes.utils import obtener_etapa_actual_dias, obtener_equipos_actual_dias
from datetime import datetime, date
from pprint import pprint

users = Blueprint('users', __name__)


@users.route('/convenios_sd/<int:id_persona>', methods=['GET', 'POST'])
@login_required
#@sd_only
def convenios_sd(id_persona):
    # Permitir acceso solo a la SD (o admin)
    if current_user.permisos != 'Admin':
        persona = Persona.query.get_or_404(id_persona)
        if persona.id != current_user.id_persona:
            abort(403)

    equipo = Persona.query.get(id_persona).equipo

    # Convenios asignados
    ids_convenios_asignados = [trayecto.id_convenio for trayecto in TrayectoriaEquipo.query.filter(and_(TrayectoriaEquipo.id_equipo == equipo.id,
                                                                    TrayectoriaEquipo.salida == None)).all()]
    convenios_asignados = [
        {'id': convenio.id,
         'nombre': generar_nombre_convenio(convenio),
         'dias_area': dias_habiles(TrayectoriaEquipo.query.filter(and_(TrayectoriaEquipo.id_convenio == convenio.id,
                                                  TrayectoriaEquipo.salida == None, TrayectoriaEquipo.id_equipo == equipo.id)).first().ingreso,
                                   date.today()),
         'etapa': obtener_etapa_actual_dias(convenio)}
        for convenio in Convenio.query.filter(Convenio.id.in_(ids_convenios_asignados))]

    convenios_asignados.sort(key=lambda dict: dict['nombre'])

    # Convenios asociados
    lista_convenios_asociados = [convenio.id_convenio for convenio in SdInvolucrada.query.filter(SdInvolucrada.id_subdireccion == equipo.id).all()]
    convenios_asociados_query = Convenio.query.filter(Convenio.id.in_(lista_convenios_asociados)).all()

    tabla_convenios_asociados = []
    for convenio in convenios_asociados_query:
        nombre = generar_nombre_convenio(convenio)
        observacion_query = BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == convenio.id,
                                                               BitacoraAnalista.estado != 'Eliminado')).order_by(
            BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).first()
        ultima_observacion = f'({datetime.strftime(observacion_query.fecha, "%d-%m-%Y")}) {observacion_query.observacion}'
        estado = convenio.estado
        coordinador = f'<p align="center">{obtener_iniciales(convenio.coord_sii.nombre)}<br>' \
                      f'{(lambda sup: f"({obtener_iniciales(sup.nombre)})" if sup else "")(convenio.sup_sii)}</p>'
        link_resolucion = (lambda
                               link: f'<a target="_blank" class="text-center" style="text-decoration: none; color: #000;" href="{link}">'
                                     f'<i class="fas fa-eye pt-2 text-center btn-lg"></i></a>' if link else
        '<div class="text-center"><i class="fas fa-eye-slash pt-2 text-center text-muted btn-lg"></i></div>')(
            convenio.link_resolucion)
        tabla_convenios_asociados.append([nombre, estado, ultima_observacion, coordinador, link_resolucion, convenio.id])

    # Ordenar tabla
    tabla_convenios_asociados.sort(key=lambda lista: lista[0])
    # Agregar link al nombre del convenio y botar el id
    for convenio in tabla_convenios_asociados:
        if convenio[1] == 'En proceso':
            convenio[0] = f'<a style="text-decoration: none; color: #000;" href={url_for("informes.detalle_convenio_en_proceso", id_convenio=convenio[5])}>{convenio[0]} <i class="fas fa-search btn-sm"></i></a>'
        elif convenio[1] == 'En producción':
            convenio[0] = f'<a style="text-decoration: none; color: #000;" href={url_for("informes.detalle_convenio_en_produccion", id_convenio=convenio[5])}>{convenio[0]} <i class="fas fa-search btn-sm"></i></a>'
        else:
            convenio[0] = f'<a style="text-decoration: none; color: #000;" href={url_for("informes.detalle_otros_convenios", id_convenio=convenio[5])}>{convenio[0]} <i class="fas fa-search btn-sm"></i></a>'
        convenio.pop()

    return render_template('users/convenios_sd.html', equipo=equipo, convenios_asignados=convenios_asignados,
                           tabla_convenios_asociados=tabla_convenios_asociados)


@users.route('/mis_convenios/<int:id_persona>', methods=['GET', 'POST'])
@login_required
@analista_only
def mis_convenios(id_persona):
    # Permitir acceso solo al analista (o admin)
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
        return redirect(url_for('users.mis_convenios', id_persona=id_persona))

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
        return redirect(url_for('users.mis_convenios', id_persona=id_persona))

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
        return redirect(url_for('users.mis_convenios', id_persona=id_persona))


    # Estado actual de mis convenios
    tabla_estado_actual = []
    for convenio in convenios_analista_query:
        nombre = generar_nombre_convenio(convenio)
        observacion_query = BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == convenio.id,
                                                               BitacoraAnalista.estado != 'Eliminado')).order_by(
            BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).first()
        ultima_observacion = f'({datetime.strftime(observacion_query.fecha, "%d-%m-%Y")}) {observacion_query.observacion}'
        estado = convenio.estado
        suplente = f'<p align="center">{(lambda sup: obtener_iniciales(sup.nombre) if sup else "")(convenio.sup_sii)}</p>'
        link_resolucion = (lambda
                               link: f'<a target="_blank" class="text-center" style="text-decoration: none; color: #000;" href="{link}">'
                                     f'<i class="fas fa-eye pt-2 text-center btn-lg"></i></a>' if link else
        '<div class="text-center"><i class="fas fa-eye-slash pt-2 text-center text-muted btn-lg"></i></div>')(
            convenio.link_resolucion)
        link_project = (lambda
                               link: f'<div class="text-center"><a target="_blank" style="text-decoration: none; color: #000;" href="{link}">'
                                     f'<img class="text-center btn-lg" src="{url_for("static", filename="project.png")}"></a></div>' if link else
        f'<div class="text-center"><img class=" text-muted btn-lg" src="{url_for("static", filename="project_gray.png")}"></div>')(
            convenio.link_project)
        tabla_estado_actual.append([nombre, estado, ultima_observacion, suplente, link_project, link_resolucion, convenio.id])
    # Ordenar tabla
    tabla_estado_actual.sort(key=lambda lista: lista[0])
    # Agregar link al nombre del convenio y botar el id
    for convenio in tabla_estado_actual:
        convenio[0] = f'<a style="text-decoration: none; color: #000;" href={url_for("bitacoras.bitacora_convenio", id_convenio=convenio[6])}>' \
                 f'{convenio[0]} <i class="fa-solid fa-keyboard fa-fw"></i></a>'
        convenio.pop()

    # Estado actual mis suplencias
    suplencias_query = Convenio.query.filter(Convenio.id_sup_sii == id_persona).all()
    tabla_suplencias = []
    for convenio in suplencias_query:
        nombre = generar_nombre_convenio(convenio)
        estado = convenio.estado
        observacion_query = BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == convenio.id,
            BitacoraAnalista.estado != 'Eliminado')).order_by(BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).first()
        ultima_observacion = f'({datetime.strftime(observacion_query.fecha, "%d-%m-%Y")}) {observacion_query.observacion}'
        tarea_query = BitacoraTarea.query.filter(and_(BitacoraTarea.id_convenio == convenio.id,
                                              BitacoraTarea.estado == 'Pendiente')).order_by(BitacoraTarea.plazo.asc()).first()
        if tarea_query is None:
            proxima_tarea = 'Sin tareas pendientes'
        elif tarea_query.plazo <= date.today():
            proxima_tarea = f'<p style="display:inline" class="text-danger">({datetime.strftime(tarea_query.plazo, "%d-%m-%Y")})</p> {tarea_query.tarea}'
        else:
            proxima_tarea = f'({datetime.strftime(tarea_query.plazo, "%d-%m-%Y")}) {tarea_query.tarea}'
        coordinador = f'<p align="center">{(lambda coord: obtener_iniciales(coord.nombre) if coord else "")(convenio.coord_sii)}</p>'
        tabla_suplencias.append([nombre, estado, ultima_observacion, proxima_tarea, coordinador, convenio.id])
    # Ordernar tabla
    tabla_suplencias.sort(key=lambda lista: lista[0])
    # Agregar link al nombre del convenio
    for convenio in tabla_suplencias:
        convenio[0] = f'<a style="text-decoration: none; color: #000;" href={url_for("bitacoras.bitacora_convenio", id_convenio=convenio[5])}>' \
                 f'{convenio[0]} <i class="fa-solid fa-keyboard fa-fw"></i></a>'
        convenio.pop()

    return render_template('users/mis_convenios.html', tareas_pendientes=tareas_pendientes, hoy=date.today(),
                           id_persona=id_persona, convenios_select=convenios_select, form_info=form_info_convenio,
                           form_bitacora=form_bitacora, form_tarea=form_tarea, tabla_estado_actual=tabla_estado_actual, tabla_suplencias=tabla_suplencias)


@users.route('/obtener_info_convenio/<int:id_convenio>')
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
        dias_proceso += dias_habiles(trayectoEtapa.ingreso, salida_etapa)

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
            'dias_equipo': dias_habiles(trayectoEquipo.ingreso, date.today())
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
            'dias_etapa': (lambda etapa: dias_habiles(etapa_query.ingreso, date.today()) if etapa != 5 else '')(etapa_query.id_etapa)
        },
        'equipos': equipos

    }
    return jsonify(info_convenio)


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

