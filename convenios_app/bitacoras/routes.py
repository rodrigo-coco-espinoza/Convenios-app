from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify
from convenios_app.models import Ministerio, Institucion, Equipo, Persona, Convenio
from convenios_app.bitacoras.forms import ConvenioForm
from convenios_app import db
from sqlalchemy import and_, or_

bitacoras = Blueprint('bitacoras', __name__)

ID_AIET = 5
ID_IE = 0
ID_GDIR = 0

def generar_nombre_convenio(convenio):
    """
    Genera el nombre del convenio con la sigla de la institución
    :param convenio: objeto de la clase Convenio
    :return: str(SIGLA Nombre)
    """
    if convenio.tipo == 'Convenio':
        return f'{convenio.institucion.sigla} {convenio.nombre}'
    else:
        return f'{convenio.institucion.sigla} (Ad) {convenio.nombre}'


@bitacoras.route('/nuevo_convenio', methods=['GET', 'POST'])
def agregar_convenio():
    # Crear select field con convenios
    convenios = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in Convenio.query.order_by(Convenio.nombre.asc()).all()]
    convenios.insert(0, (0, 'Seleccione convenio para editar'))

    # Crear formulario convenio
    instituciones = [(institucion.id, institucion.nombre) for institucion in Institucion.query.order_by(Institucion.nombre.asc()).all()]
    instituciones.insert(0, (0, 'Seleccionar'))
    convenio_padre = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in Convenio.query.filter(and_(Convenio.tipo == 'Convenio', or_(Convenio.estado == 'En producción', Convenio.estado == 'En proceso'))).order_by(Convenio.nombre.asc()).all()]
    convenio_padre.insert(0, (0, 'Seleccionar'))
    personas_aiet = [(persona.id, persona.nombre) for persona in Persona.query.filter_by(id_equipo=ID_AIET).order_by(Persona.nombre.asc()).all()]
    personas_aiet.insert(0, (0, 'Seleccionar'))
    subdirecciones = [(str(subdireccion.id), subdireccion.sigla) for subdireccion in Equipo.query.filter(and_(Equipo.sigla != 'AIET', Equipo.sigla != 'IE', Equipo.sigla != 'GDIR')).order_by(Equipo.sigla.asc()).all()]
    convenio_reemplazo = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in Convenio.query.filter(or_(Convenio.estado == 'En proceso', Convenio.estado == 'En producción')).order_by(Convenio.nombre.asc()).all()]
    convenio_reemplazo.insert(0, (0, 'Seleccionar'))

    form_convenio = ConvenioForm()
    form_convenio.institucion.choices = instituciones
    form_convenio.convenio_padre.choices = convenio_padre
    form_convenio.coord_sii.choices = personas_aiet
    form_convenio.sup_sii.choices = personas_aiet
    form_convenio.sd_involucradas.choices = subdirecciones
    form_convenio.convenio_reemplazo.choices = convenio_reemplazo

    if form_convenio.validate_on_submit():
        print(form_convenio.sd_involucradas.data)
        print(form_convenio.convenio_padre.data)

        #TODO: ingresar registro en bitacora
        #TODO: finalizar convenio si se cambia de estado


    return render_template('bitacoras/nuevo_convenio.html', convenios=convenios, form_convenio=form_convenio)


@bitacoras.route('/obtener_personas_ie/<int:id_institucion>')
def obtener_personas_ie(id_institucion):
    lista_personas = [{'nombre': persona.nombre,
                       'id': persona.id} for persona in Persona.query.filter_by(id_institucion=id_institucion).all()]
    return jsonify(lista_personas)

@bitacoras.route('/eliminar_convenio/<int:id_convenio>')
def eliminar_convenio(id_convenio):
    return f'algun día se podrá eliminar el convenio {id_convenio}'
