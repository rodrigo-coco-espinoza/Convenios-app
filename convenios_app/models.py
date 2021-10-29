from flask import current_app
from convenios_app import db, login_manager
from convenios_app.bitacoras.utils import generar_nombre_convenio, formato_nombre

#TODO: Obtener los registgros que tengan campos en blanco (Instituciones, personas)

class Ministerio(db.Model):
    """
    Representa los Ministerios a los cuales pertenencen las instituciones cuando corresponde)
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    sigla = db.Column(db.String(10), unique=True, nullable=False)
    rut = db.Column(db.String(20), unique=True, nullable=True)
    direccion = db.Column(db.String(150), nullable=True)
    # Relaciones -> es llave foránea en:
    instituciones = db.relationship('Institucion', backref='ministerio')

    def __repr__(self):
        return f'<{self.id} - {self.sigla} - {self.nombre}>'


class Equipo(db.Model):
    """
    Representa los equipos de trabajo que participan en el proceso de convenio.
    El equipo Intitución Externa agrupa a toda las contrapartes fuera del SII.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    sigla = db.Column(db.String(10), unique=True, nullable=False)
    # Relaciones -> es llave foránea en:
    personas = db.relationship('Persona', backref='equipo')

    def __repr__(self):
        return f'{self.id} - {self.sigla} - {self.nombre}'


class Institucion(db.Model):
    """
    Representa las instituciones con las cuales el SII firma los convenios.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    sigla = db.Column(db.String(10), unique=True, nullable=False)
    rut = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(150), nullable=True)
    tipo = db.Column(db.String(20), nullable=False)
    # Llaves foráneas
    id_ministerio = db.Column(db.Integer, db.ForeignKey('ministerio.id'), nullable=True)
    # Relaciones -> es llave foránea en:
    personas = db.relationship('Persona', backref='institucion')
    convenios = db.relationship('Convenio', backref='institucion')

    def actualizar_institucion(self, form):
        """
        Actualiza la base de datos con el formulario de /ver_institucion.
        :param form: información ingresada por el usuario en el formulario para editar.
        :return: cambia los parámetros en la base datos.
        """
        self.nombre = formato_nombre(form.nombre.data)
        self.sigla = form.sigla.data.upper()
        self.rut = form.rut.data
        self.direccion = form.direccion.data
        self.tipo = form.tipo.data

        if int(form.ministerio.data) > 0:
            self.id_ministerio = int(form.ministerio.data)

        db.session.commit()

    def __repr__(self):
        return f'<{self.id} - {self.sigla} - {self.nombre}>'


class Persona(db.Model):
    """
    Representa a las personas que pertenecen a las distintas instituciones y equipos de trabajo.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), nullable=True)
    telefono = db.Column(db.String(100), nullable=True)
    cargo = db.Column(db.String(100), nullable=True)
    area = db.Column(db.String(100), nullable=True)
    # Llaves foráneas
    id_institucion = db.Column(db.Integer, db.ForeignKey('institucion.id'), nullable=False)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=False)
    # Relaciones -> es llave foránea en:

    def actualizar_persona(self, form):
        """
        Actualiza la base de datos con el formulario de /ver_persona.
        :param form: información ingresada por el usuario en el formulario para editar.
        :return: cambia los parámetros en la base datos.
        """
        self.nombre = formato_nombre(form.nombre.data)
        self.correo = form.correo.data
        self.telefono = form.telefono.data
        self.cargo = formato_nombre(form.cargo.data)
        self.area = formato_nombre(form.area.data)
        self.id_institucion = int(form.institucion.data)
        self.id_equipo = int(form.equipo.data)
        db.session.commit()

    def __repr__(self):
        return f'{self.id} - {self.nombre} - {self.institucion.nombre}'


class Convenio(db.Model):
    """
    Representa cada uno de los convenios que ha gestionado el SII.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    id_convenio_padre = db.Column(db.Integer, nullable=True)
    id_convenio_reemplazo = db.Column(db.Integer, nullable=True)
    gabinete_electronico = db.Column(db.Integer, nullable=True)
    proyecto = db.Column(db.Integer, nullable=True)
    resolucion = db.Column(db.Integer, nullable=True)
    link_resolucion = db.Column(db.String(100), nullable=True)
    # Llaves foráneas
    id_institucion = db.Column(db.Integer, db.ForeignKey('institucion.id'), nullable=False)
    id_coord_sii = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=False)
    coord_sii = db.relationship('Persona', foreign_keys=[id_coord_sii])
    id_sup_sii = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=True)
    sup_sii = db.relationship('Persona', foreign_keys=[id_sup_sii])
    id_coord_ie = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=True)
    coord_ie = db.relationship('Persona', foreign_keys=[id_coord_ie])
    id_sup_ie = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=True)
    sup_ie = db.relationship('Persona', foreign_keys=[id_sup_ie])
    id_responsable_convenio_ie = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=True)
    responsable_convenio_ie = db.relationship('Persona', foreign_keys=[id_responsable_convenio_ie])
    # Relaciones -> es llave foránea en:

    def actualizar_convenio(self, form):
        """
        Actualiza la base de datos con el formulario de /nuevo_convenio.
        :param form: información ingresada por el usuario en el formulario para editar.
        :return: cambia los parámetros en la base datos.
        """
        self.nombre = formato_nombre(form.nombre.data)
        self.estado = form.estado.data
        if form.estado.data == 'Reemplazado':
          self.id_convenio_reemplazo = form.convenio_reemplazo.data
        self.tipo = form.tipo.data
        if form.tipo.data == 'Adendum':
            self.id_convenio_padre = form.convenio_padre.data
        self.gabinete_electronico = form.gabinete_electronico.data
        self.proyecto = form.proyecto.data
        self.id_institucion = form.institucion.data
        self.id_coord_sii = form.coord_sii.data
        if int(form.sup_sii.data) != 0:
            self.id_sup_sii = form.sup_sii.data
        if int(form.coord_ie.data) != 0:
            self.id_coord_ie = form.coord_ie.data
        if int(form.sup_ie.data) != 0:
            self.id_sup_ie = form.sup_ie.data
        if int(form.responsable_convenio_ie.data) != 0:
            self.id_responsable_convenio_ie = form.responsable_convenio_ie.data

        db.session.commit()

    def __repr__(self):
        return f'{self.id} - {self.institucion.sigla} {self.nombre} - {self.estado}'


class SdInvolucrada(db.Model):
    """
    Contiene todas las subdireciones involucradas para cada convenio.
    """
    id = db.Column(db.Integer, primary_key=True)
    id_convenio = db.Column(db.Integer, db.ForeignKey('convenio.id'), nullable=False)
    convenio = db.relationship('Convenio', foreign_keys=[id_convenio])
    id_subdireccion = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=False)
    subdireccion = db.relationship('Equipo', foreign_keys=[id_subdireccion])

    def __repr__(self):
        return f'{self.id} - {generar_nombre_convenio(self.convenio)} - {self.subdireccion}'

