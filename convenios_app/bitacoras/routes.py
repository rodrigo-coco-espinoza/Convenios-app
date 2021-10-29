from flask import render_template, request, Blueprint, url_for, redirect, flash, abort, jsonify
from convenios_app.models import Ministerio, Institucion, Equipo, Persona, Convenio, SdInvolucrada
from convenios_app.bitacoras.forms import ConvenioForm
from convenios_app import db
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import generar_nombre_convenio, formato_nombre
from convenios_app.main.utils import generar_nombre_institucion

bitacoras = Blueprint('bitacoras', __name__)

#TODO: actualizar ID en tabla final
ID_AIET = 5
ID_IE = 0
ID_GDIR = 0




@bitacoras.route('/nuevo_convenio', methods=['GET', 'POST'])
def agregar_convenio():
    # Crear select field con convenios
    convenios = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in Convenio.query.order_by(Convenio.nombre.asc()).all()]
    convenios.insert(0, (0, 'Seleccione convenio para editar'))

    # Crear formulario convenio
    instituciones = [(institucion.id, generar_nombre_institucion(institucion)) for institucion in Institucion.query.order_by(Institucion.nombre.asc()).all()]
    instituciones.insert(0, (0, 'Seleccionar'))
    #TODO: GENERAR ESTA LISTA CON JS PARA QUE SOLO MUESTRE LOS CONVENIOS DE LA ISNTITUCION
    #convenio_padre = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in Convenio.query.filter(and_(Convenio.tipo == 'Convenio', or_(Convenio.estado == 'En producción', Convenio.estado == 'En proceso'))).order_by(Convenio.nombre.asc()).all()]
    #convenio_padre.insert(0, (0, 'Seleccionar'))
    personas_aiet = [(persona.id, persona.nombre) for persona in Persona.query.filter_by(id_equipo=ID_AIET).order_by(Persona.nombre.asc()).all()]
    personas_aiet.insert(0, (0, 'Seleccionar'))
    subdirecciones = [(str(subdireccion.id), subdireccion.sigla) for subdireccion in Equipo.query.filter(and_(Equipo.sigla != 'AIET', Equipo.sigla != 'IE', Equipo.sigla != 'GDIR')).order_by(Equipo.sigla.asc()).all()]
    convenio_reemplazo = [(convenio.id, generar_nombre_convenio(convenio)) for convenio in Convenio.query.filter(or_(Convenio.estado == 'En proceso', Convenio.estado == 'En producción')).order_by(Convenio.nombre.asc()).all()]
    convenio_reemplazo.insert(0, (0, 'Seleccionar'))

    form_convenio = ConvenioForm()
    form_convenio.institucion.choices = instituciones
    #form_convenio.convenio_padre.choices = convenio_padre
    form_convenio.coord_sii.choices = personas_aiet
    form_convenio.sup_sii.choices = personas_aiet
    form_convenio.sd_involucradas.choices = subdirecciones
    form_convenio.convenio_reemplazo.choices = convenio_reemplazo
    ultimo_proyecto = (lambda convenio: convenio.proyecto if convenio else 0)(Convenio.query.order_by(Convenio.proyecto.desc()).first())
    form_convenio.proyecto.render_kw = {'placeholder': f'Último proyecto registrado: {ultimo_proyecto}'}

    if form_convenio.validate_on_submit():
        if int(form_convenio.id_convenio.data) == 0:
            # NUEVO CONVENIO
            # Crear objeto convenio
            nuevo_convenio = Convenio(
                nombre=formato_nombre(form_convenio.nombre.data),
                tipo=form_convenio.tipo.data,
                estado=form_convenio.estado.data,
                id_institucion=form_convenio.institucion.data,
                id_coord_sii=form_convenio.coord_sii.data
            )
            # Agregar convenio padre si es adendum
            if form_convenio.tipo == 'Adendum':
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

            # Agregar subdirecciones involucradas
            convenio_recien_agregado = Convenio.query.filter(and_(Convenio.nombre == nuevo_convenio.nombre),
                                                             Convenio.id_institucion == nuevo_convenio.id_institucion).first()
            for subdireccion in form_convenio.sd_involucradas.data:
                nueva_sd_involucrada = SdInvolucrada(
                    id_convenio=convenio_recien_agregado.id,
                    id_subdireccion=subdireccion
                )
                db.session.add(nueva_sd_involucrada)
            db.session.commit()

            flash(f'Se ha agregado {generar_nombre_convenio(nuevo_convenio)} correctamente.', 'success')
            return redirect(url_for('bitacoras.agregar_convenio'))

        else:
            # EDITAR CONVENIO
            editar_convenio = Convenio.query.get(int(form_convenio.id_convenio.data))
            editar_convenio.actualizar_convenio(form_convenio)

            # EDITAR SUBDIRECCIONES INVOLUCRADAS
            # Agregar subdirecciones nuevas involucradas
            sd_actuales = SdInvolucrada.query.filter_by(id_convenio=int(form_convenio.id_convenio.data)).all()
            sd_actuales_lista = [subdireccion.id_subdireccion for subdireccion in sd_actuales]
            for sd_form in form_convenio.sd_involucradas.data:
                if int(sd_form) not in sd_actuales_lista:
                    nueva_sd_involucrada = SdInvolucrada(
                        id_convenio=editar_convenio.id,
                        id_subdireccion=sd_form
                    )
                    db.session.add(nueva_sd_involucrada)
            # Eliminar subdirecciones que ya no estén involucradas
            for sd_actual in sd_actuales:
                if str(sd_actual.id_subdireccion) not in form_convenio.sd_involucradas.data:
                    db.session.delete(sd_actual)
            db.session.commit()

            flash(f'Se ha actualizado {generar_nombre_convenio(editar_convenio)}', 'success')
            return redirect(url_for('bitacoras.agregar_convenio'))
            #TODO: ingresar registro en bitacora
            #TODO: finalizar convenio si se cambia de estado (y los adendum de ese convenio también?)

    return render_template('bitacoras/nuevo_convenio.html', convenios=convenios, form_convenio=form_convenio)


@bitacoras.route('/obtener_personas_ie/<int:id_institucion>')
def obtener_personas_ie(id_institucion):
    lista_personas = [{'nombre': persona.nombre,
                       'id': persona.id} for persona in Persona.query.filter_by(id_institucion=id_institucion).all()]
    return jsonify(lista_personas)


@bitacoras.route('/obtener_convenio/<int:id_convenio>')
def obtener_convenio(id_convenio):
    # Buscar convenio a editar
    query = Convenio.query.get(id_convenio)
    #TODO: sd involucradas
    convenio = {
        'id': query.id,
        'nombre': query.nombre,
        'estado': query.estado,
        'tipo': query.tipo,
        'id_convenio_padre': (lambda convenio: 0 if not convenio.id_convenio_padre else convenio.id_convenio_padre)(query),
        'id_convenio_reemplazo': (lambda convenio: 0 if not convenio.id_convenio_reemplazo else convenio.id_convenio_reemplazo)(query),
        'gabinete_electronico': query.gabinete_electronico,
        'proyecto': query.proyecto,
        'id_institucion': query.id_institucion,
        'id_coord_sii': query.id_coord_sii,
        'id_sup_sii': (lambda sup_sii: 0 if not sup_sii.id_sup_sii else sup_sii.id_sup_sii)(query)
    }

    return jsonify(convenio)


@bitacoras.route('/obtener_personas_convenio/<int:id_convenio>')
def obtener_personas_convenio(id_convenio):
    # Buscar convenio a editar
    query = Convenio.query.get(id_convenio)
    personas = {
        'coord_ie': (lambda coord_ie: 0 if not coord_ie.id_coord_ie else coord_ie.id_coord_ie)(query),
        'sup_ie': (lambda sup_ie: 0 if not sup_ie.id_sup_ie else sup_ie.id_sup_ie)(query),
        'responsable_convenio_ie': (lambda resp_ie: 0 if not resp_ie.id_responsable_convenio_ie else resp_ie.id_responsable_convenio_ie)(query)
    }
    return jsonify(personas)


@bitacoras.route('/obtener_sds_convenio/<int:id_convenio>')
def obtener_sds_convenio(id_convenio):
    query = SdInvolucrada.query.filter_by(id_convenio=id_convenio).all()
    subdirecciones = [str(subdireccion.id_subdireccion) for subdireccion in query]
    return jsonify(subdirecciones)


@bitacoras.route('/obtener_convenios_institucion/<int:id_institucion>')
def obtener_convenios_institucion(id_institucion):
    query = Convenio.query.filter(and_(Convenio.tipo == 'Convenio', Convenio.id_institucion == id_institucion)).all()
    convenios = [{'nombre': generar_nombre_convenio(convenio),
                  'id': convenio.id} for convenio in query]
    return jsonify(convenios)


@bitacoras.route('/obtener_convenio_padre/<int:id_convenio>')
def obtener_convenio_padre(id_convenio):
    id_convenio_padre = (lambda convenio: convenio.id_convenio_padre if id_convenio != 0 else 0)(Convenio.query.get(id_convenio))

    convenio_padre = {'id_convenio_padre': id_convenio_padre}
    return jsonify(convenio_padre)



# @bitacoras.route('/eliminar_convenio/<int:id_convenio>')
# def eliminar_convenio(id_convenio):
#     return f'algun día se podrá eliminar el convenio {id_convenio}'
