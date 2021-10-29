from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify
from convenios_app.models import Ministerio, Institucion, Equipo, Persona
from convenios_app.main.forms import InstitucionForm, PersonaForm
from convenios_app import db
from convenios_app.main.utils import generar_nombre_institucion
from convenios_app.bitacoras.utils import formato_nombre
from sqlalchemy import desc, asc

main = Blueprint('main', __name__)

# TODO: race condition




@main.route('/')
def home():
    return render_template('main/home.html')


@main.route('/personas', methods=['GET', 'POST'])
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

        else:
            # EDITAR PERSONA
            editar_persona = Persona.query.get(int(form_persona.id_persona.data))
            editar_persona.actualizar_persona(form=form_persona)
            flash(f'Se ha actualizado {editar_persona.nombre}', 'success')
            return redirect(url_for('main.ver_persona'))

    return render_template('main/personas.html', form_persona=form_persona, personas=personas)


@main.route('/info_persona/<int:id>', methods=['GET', 'POST'])
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


# @main.route('/eliminar_persona/<int:id_persona>')
# def eliminar_persona(id_persona):
#     persona = Persona.query.get(id_persona)
#     db.session.delete(persona)
#     db.session.commit()
#     flash(f'Se ha eliminado {persona.nombre}', 'success')
#     return redirect(url_for('main.ver_persona'))


@main.route('/instituciones', methods=['GET', 'POST'])
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


# @main.route('/eliminar_institucion/<int:id_institucion>')
# def eliminar_institucion(id_institucion):
#     institucion = Institucion.query.get(id_institucion)
#     db.session.delete(institucion)
#     db.session.commit()
#     flash(f'Se ha eliminado {institucion.nombre}', 'success')
#     return redirect(url_for('main.ver_institucion'))
