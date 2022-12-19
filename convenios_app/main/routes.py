import json
from datetime import datetime, date
import time
from pprint import pprint

from flask import render_template, Blueprint, url_for, redirect, flash, jsonify
from flask_login import current_user, login_required
from convenios_app.users.utils import admin_only, analista_only
from sqlalchemy import and_, or_, distinct, func

from convenios_app import db
from convenios_app.main.forms import InstitucionForm, PersonaForm, EditarPersonaForm
from convenios_app.main.utils import generar_nombre_institucion, formato_nombre, generar_nombre_convenio
from convenios_app.models import Ministerio, Institucion, Equipo, Persona, Convenio, TrayectoriaEtapa
from convenios_app.bitacoras.forms import ETAPAS

main = Blueprint('main', __name__)

# TODO: race condition


@main.route('/')
def home():
    # Datos números
    convenios_firmados = Convenio.query.filter(and_(Convenio.fecha_documento != None,
                                                    or_(Convenio.estado == 'En proceso', Convenio.estado == 'En producción'))).count()
    instituciones_firmantes = db.session.query(func.count(distinct(Convenio.id_institucion))).filter(or_(Convenio.estado == 'En producción', Convenio.estado == 'En proceso')).first()[0]
    count_convenios_por_firmar = Convenio.query.filter(and_(Convenio.estado == 'En proceso', Convenio.fecha_documento == None)).count()
    count_convenios_en_proceso = Convenio.query.filter(Convenio.estado == 'En proceso').count()
    count_convenios_en_produccion = Convenio.query.filter(Convenio.estado == 'En producción').count()
    data = {
        'firmados': convenios_firmados,
        'por_firmar': count_convenios_por_firmar,
        'en_produccion': count_convenios_en_produccion,
        'instituciones': instituciones_firmantes,
        'en_proceso': count_convenios_en_proceso
    }

    # Datos gráfico convenios por etapas
    query_convenios_en_proceso = Convenio.query.filter(Convenio.estado == 'En proceso').all()
    data_etapas = [[ETAPAS[0][1], 0],
                   [ETAPAS[1][1], 0],
                   [ETAPAS[2][1], 0],
                   [ETAPAS[3][1], 0]]

    for convenio in query_convenios_en_proceso:
        etapa_actual = TrayectoriaEtapa.query.filter(
            and_(TrayectoriaEtapa.id_convenio == convenio.id, TrayectoriaEtapa.salida == None)).first()
        if etapa_actual.etapa.etapa == ETAPAS[0][1]:
            data_etapas[0][1] += 1
        elif etapa_actual.etapa.etapa == ETAPAS[1][1]:
            data_etapas[1][1] += 1
        elif etapa_actual.etapa.etapa == ETAPAS[2][1]:
            data_etapas[2][1] += 1
        elif etapa_actual.etapa.etapa == ETAPAS[3][1]:
            data_etapas[3][1] += 1

    # Datos gráfico Convenios firmados último 12 meses
    now = time.localtime()
    meses = [time.localtime(time.mktime((now.tm_year, now.tm_mon - n, 1, 0, 0, 0, 0, 0, 0)))[:2] for n in range(12)]
    ultimos_doce_meses = [date(year=mes[0], month=mes[1], day=1) for mes in meses]
    ultimos_doce_meses.sort()
    query_ultimo_año = Convenio.query.filter(Convenio.fecha_documento >= ultimos_doce_meses[0]).order_by(Convenio.fecha_documento.asc()).all()
    dict_ultimo_año = {datetime.strftime(fecha, "%m-%Y"): [] for fecha in ultimos_doce_meses}

    for convenio in query_ultimo_año:
        dict_ultimo_año[datetime.strftime(convenio.fecha_documento, "%m-%Y")].append(f'{generar_nombre_convenio(convenio)}')

    lista_firmados_mes = {}
    for mes, convenios in dict_ultimo_año.items():
        tooltip = '<ul style="text-align: left;">'
        for convenio in convenios:
            tooltip += f'<li>{convenio}</li>'
        tooltip += '</u>'
        lista_firmados_mes[mes] = tooltip

    data_ultimo_año = [[mes, len(convenios)] for mes, convenios in dict_ultimo_año.items()]
    for i, datos in enumerate(data_ultimo_año):
        if i % 2 > 0:
            datos.append("#E6500A")
        else:
            datos.append('#0064A0')
        datos.append(lista_firmados_mes[datos[0]])
    data_ultimo_año.insert(0, ['Mes', 'Convenios firmados'])

    # Datos gráfico Convenios firmados total
    query_firmados_total = Convenio.query.filter(Convenio.fecha_documento != None).order_by(Convenio.fecha_documento.asc()).all()
    años_firmados = [datetime.strftime(convenio.fecha_documento, "%Y") for convenio in query_firmados_total]
    años_firmados = list(dict.fromkeys(años_firmados))

    dict_firmados_total = {año: [] for año in años_firmados}
    for convenio in query_firmados_total:
        dict_firmados_total[datetime.strftime(convenio.fecha_documento, "%Y")].append(
            f'{generar_nombre_convenio(convenio)}')

    lista_firmados_año = {}
    for año, convenios in dict_firmados_total.items():
        tooltip = '<ul style="text-align: left;">'
        for convenio in convenios:
            tooltip += f'<li>{convenio}</li>'
        tooltip += '</u>'
        lista_firmados_año[año] = tooltip

    data_años_total = [[año, len(convenios)] for año, convenios in dict_firmados_total.items()]
    for i, datos in enumerate(data_años_total):
        if i % 2 > 0:
            datos.append("#E6500A")
        else:
            datos.append('#0064A0')
        datos.append(lista_firmados_año[datos[0]])
    data_años_total.insert(0, ['Año', 'Convenios firmados'])

    return render_template('main/home.html', data=data, data_ultimo_año=data_ultimo_año, data_etapas=data_etapas,
                           data_años_total=data_años_total)


@main.route('/personas', methods=['GET', 'POST'])
@login_required
@analista_only
def ver_persona():
    # Crear select field con personas
    personas = [(persona.id, persona.nombre) for persona in Persona.query.order_by(Persona.nombre.asc()).all()]
    personas.insert(0, (0, 'Seleccione persona para editar'))

    # Crear formulario persona
    instituciones = [(institucion.id, generar_nombre_institucion(institucion)) for institucion in Institucion.query.order_by(Institucion.nombre.asc()).all()]
    instituciones.insert(0, (0, 'Seleccionar'))
    equipos = [(equipo.id, equipo.sigla) for equipo in Equipo.query.order_by(Equipo.sigla.asc()).all()]
    equipos.insert(0, (0, 'Seleccionar'))
    form_persona = PersonaForm()
    form_persona.institucion.choices = instituciones
    form_persona.equipo.choices = equipos

    if form_persona.validate_on_submit():
        if int(form_persona.id_persona.data) == 0:
            # NUEVA PERSONA
            # Crear objeto persona
            nueva_persona = Persona(
                nombre=formato_nombre(form_persona.nombre.data),
                correo=form_persona.correo.data,
                telefono=form_persona.telefono.data,
                cargo=formato_nombre(form_persona.cargo.data),
                area=formato_nombre(form_persona.area.data),
                id_institucion=form_persona.institucion.data,
                id_equipo=form_persona.equipo.data,
            )
            # Agregar a la base de datos
            db.session.add(nueva_persona)
            db.session.commit()
            flash(f'Se ha agregado {nueva_persona.nombre} correctamente.', 'success')
            return redirect(url_for('main.ver_persona'))



    return render_template('main/personas.html', form_persona=form_persona, personas=personas)


@main.route('/editar_persona/<int:id_persona>', methods=['GET', 'POST'])
@login_required
@analista_only
def editar_persona(id_persona):
    # Persona a editar
    persona_seleccionada = Persona.query.get(id_persona)

    # Crear select field con personas
    personas = [(persona.id, persona.nombre) for persona in Persona.query.order_by(Persona.nombre.asc()).all()]
    personas.insert(0, (0, 'Agregar nueva persona'))

    # Crear formulario editar persona
    instituciones = [(institucion.id, generar_nombre_institucion(institucion)) for institucion in Institucion.query.order_by(Institucion.nombre.asc()).all()]
    instituciones.insert(0, (0, 'Seleccionar'))
    equipos = [(equipo.id, equipo.sigla) for equipo in Equipo.query.order_by(Equipo.sigla.asc()).all()]
    equipos.insert(0, (0, 'Seleccionar'))
    form_editar_persona = EditarPersonaForm()
    form_editar_persona.institucion.choices = instituciones
    form_editar_persona.equipo.choices = equipos

    # Datos persona para rellenar el formulario
    info_persona = {
        'id_persona': persona_seleccionada.id,
        'nombre': persona_seleccionada.nombre,
        'correo': persona_seleccionada.correo,
        'telefono': persona_seleccionada.telefono,
        'cargo': persona_seleccionada.cargo,
        'area': persona_seleccionada.area,
        'id_institucion': persona_seleccionada.id_institucion,
        'id_equipo': persona_seleccionada.id_equipo
    }
    
    if form_editar_persona.validate_on_submit():
        persona_seleccionada.actualizar_persona(form=form_editar_persona)
        flash(f'Se ha editado {persona_seleccionada.nombre} correctamente.', 'success')
        return redirect(url_for('main.editar_persona', id_persona=id_persona))

    return render_template('main/editar_persona.html', form_editar_persona=form_editar_persona, 
                            personas=personas, info_persona=info_persona)


@main.route('/info_persona/<int:id>', methods=['GET', 'POST'])
@login_required
@analista_only
def obtener_persona(id):
    # Buscar persona a editar
    query = Persona.query.get(id)
    persona = {
        'id': query.id,
        'nombre': query.nombre,
        'correo': query.correo,
        'telefono': query.telefono,
        'equipo': query.id_equipo,
        'institucion': query.id_institucion,
        'area': query.area,
        'cargo': query.cargo,
    }
    return jsonify(persona)


@main.route('/instituciones', methods=['GET', 'POST'])
@login_required
@analista_only
def ver_institucion():
    # Crear select field con instituciones
    instituciones = [(institucion.id, generar_nombre_institucion(institucion)) for institucion in Institucion.query.order_by(Institucion.nombre.asc()).all()]
    instituciones.insert(0, (0, 'Seleccione institución para editar'))

    # Crear formulario nueva institución
    ministerios = [(ministerio.id, generar_nombre_institucion(ministerio)) for ministerio in Ministerio.query.order_by(Ministerio.nombre.asc()).all()]
    ministerios.insert(0, (0, 'Seleccionar o dejar en blanco'))
    form_institucion = InstitucionForm()
    form_institucion.ministerio.choices = ministerios

    if form_institucion.validate_on_submit():
        if int(form_institucion.id_institucion.data) == 0:
            # NUEVA INSTITUCIÓN
            # Crear objeto institución
            nueva_institucion = Institucion(
                nombre=formato_nombre(form_institucion.nombre.data),
                sigla=form_institucion.sigla.data.upper(),
                rut=form_institucion.rut.data,
                direccion=form_institucion.direccion.data,
                tipo=form_institucion.tipo.data
            )
            if int(form_institucion.ministerio.data) > 0:
                nueva_institucion.id_ministerio = int(form_institucion.ministerio.data)
            # Agregar a la base de datos
            db.session.add(nueva_institucion)
            db.session.commit()
            flash(f'Se ha agregado {nueva_institucion.nombre} correctamente.', 'success')
            return redirect(url_for('main.ver_institucion'))

        else:
            # EDITAR INSTITUCIÓN
            editar_institucion = Institucion.query.get(int(form_institucion.id_institucion.data))
            editar_institucion.actualizar_institucion(form=form_institucion)
            flash(f'Se ha actualizado {editar_institucion.nombre}', 'success')
            return redirect(url_for('main.ver_institucion'))

    return render_template('main/instituciones.html', form_institucion=form_institucion, instituciones=instituciones)


@main.route('/info_institucion/<int:id>', methods=['GET', 'POST'])
@login_required
@analista_only
def obtener_institucion(id):
    # Buscar institución a editar
    query = Institucion.query.get(id)
    institucion = {
        'id': query.id,
        'nombre': query.nombre,
        'sigla': query.sigla,
        'rut': query.rut,
        'direccion': query.direccion,
        'tipo': query.tipo,
        'ministerio': (lambda inst: 0 if not inst.id_ministerio else inst.id_ministerio)(query)
    }
    return jsonify(institucion)


@main.route('/obtener_convnios_todos')
@login_required
@analista_only
def obtener_convenios_todos():
    # Buscar todos los convenios
    convenios_query = Convenio.query.all()
    convenios = {generar_nombre_convenio(convenio): convenio.id  for convenio in convenios_query}

    return jsonify(convenios)