from flask import current_app
from convenios_app import db, login_manager
from convenios_app.main.utils import generar_nombre_convenio, formato_nombre
from datetime import datetime
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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
    equipos = db.relationship('TrayectoriaEquipo', backref='equipo')
    encargados = db.relationship('CatalogoWS', backref='encargado')
    recepciones = db.relationship('RecepcionConvenio', backref='sd')

    def __repr__(self):
        return f'{self.id} - {self.sigla} - {self.nombre}'


class CatalogoWS(db.Model):
    """
    Representa todos los Web Services que existen en el SII.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre_aiet = db.Column(db.String(100), nullable=False)
    nombre_sdi = db.Column(db.String(50), nullable=True)
    metodo = db.Column(db.String(50), nullable=True)
    estado = db.Column(db.Boolean(), nullable=False)
    descripcion = db.Column(db.String(), nullable=True)
    observacion = db.Column(db.String(), nullable=True)
    categoria = db.Column(db.String(50), nullable=False)
    url = db.Column(db.String(50), nullable=True)
    reservado = db.Column(db.Boolean(), nullable=True)
    pisee = db.Column(db.Boolean(), nullable=True)

    # Llaves foráneas
    id_encargado = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=True)
    # Relaciones -> es llave foránea en:
    detalle = db.relationship('DetalleWS', backref='ws')

    def __repr__(self):
        return f'<{self.nombre_aiet} - {self.nombre_sdi} - {self.metodo}: {self.estado}>'


class WSConvenio(db.Model):
    """
    Relaciona los Web Services del catálogo con los convenios en los que se otorgan a las IE.
    """
    id = db.Column(db.Integer, primary_key=True)
    #TODO: cambiar a false cuando se tenga formulario para habilitar los WS
    estado = db.Column(db.Boolean(), nullable=True)
    id_convenio = db.Column(db.Integer, db.ForeignKey('convenio.id'), nullable=False)
    convenio = db.relationship('Convenio', foreign_keys=[id_convenio])
    id_ws = db.Column(db.Integer, db.ForeignKey('catalogoWS.id'), nullable=False)
    ws = db.relationship('CatalogoWS', foreign_keys=[id_ws])

    def __repr__(self):
        return f'<{self.id} - {self.convenio.institucion.sigla} - {self.ws.nombre_aiet}: {self.estado}>'


class DetalleWS(db.Model):
    """
    Contiene el detalle de campos de entrada y salida de cada WS.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre_campo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(150), nullable=True)
    observacion = db.Column(db.String(), nullable=True)
    tipo = db.Column(db.String(10), nullable=False)

    # LLaves foráneas
    id_ws = db.Column(db.Integer, db.ForeignKey('catalogoWS.id'), nullable=False)

    def __repr__(self):
        return f'<Campo:{self.nombre_campo} - {self.tipo}>'


class RecepcionConvenio(db.Model):
    """
    Representa las recepciones de información comprometidas para cada convenio.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(), nullable=False)
    carpeta = db.Column(db.String(50), nullable=True)
    archivo = db.Column(db.String(50), nullable=True)
    periodicidad = db.Column(db.String(), nullable=False)
    estado = db.Column(db.Boolean(), nullable=True)
    metodo = db.Column(db.String(), nullable=False)

    # Llaves foráneas
    id_convenio = db.Column(db.Integer, db.ForeignKey('convenio.id'), nullable=False)
    convenio = db.relationship('Convenio', foreign_keys=[id_convenio])
    id_sd = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=False)

    def __repr__(self):
        return f'<{self.nombre}: {self.convenio.institucion.sigla}>'


class HitosConvenio(db.Model):
    """
    Registra los del proceso convenio
    """
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    minuta = db.Column(db.String, nullable=True)
    grabacion = db.Column(db.String, nullable=True)
    # Llaves foráneas
    id_convenio = db.Column(db.Integer, db.ForeignKey('convenio.id'), nullable=False)
    convenio = db.relationship('Convenio', foreign_keys=[id_convenio])
    id_hito = db.Column(db.Integer, db.ForeignKey('hito.id'), nullable=False)
    hito = db.relationship('Hito', foreign_keys=[id_hito])


class Hito(db.Model):
    """
    Contiene los hitos del proceso de convenios.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

    # Llaves foráneas
    id_etapa = db.Column(db.Integer, db.ForeignKey('etapa.id'), nullable=False)


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
    link_protocolo = db.Column(db.String(), nullable=True)
    link_repositorio = db.Column(db.String(), nullable=True)
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
    user = db.relationship('User', backref='persona')

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
    fecha_documento = db.Column(db.Date, nullable=True)
    fecha_resolucion = db.Column(db.Date, nullable=True)
    nro_resolucion = db.Column(db.Integer, nullable=True)
    link_resolucion = db.Column(db.String(100), nullable=True)
    link_project = db.Column(db.String(100), nullable=True)

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
    bitacoras_analista = db.relationship('BitacoraAnalista', backref='convenio')
    tareas = db.relationship('BitacoraTarea', backref='convenio')
    etapas = db.relationship('TrayectoriaEtapa', backref='convenio')
    equipos = db.relationship('TrayectoriaEquipo', backref='convenio')

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


class BitacoraAnalista(db.Model):
    """
    Contiene las observaciones del analista del convenio
    """
    id = db.Column(db.Integer, primary_key=True)
    observacion = db.Column(db.String, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    estado = db.Column(db.String, nullable=False, default='Creado')
    # Llaves foráneas
    id_convenio = db.Column(db.Integer, db.ForeignKey('convenio.id'), nullable=False)
    id_autor = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)


class BitacoraTarea(db.Model):
    """
    Contiene las tareas de cada convenio
    """
    id = db.Column(db.Integer, primary_key=True)
    tarea = db.Column(db.String, nullable=False)
    plazo = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String, nullable=False, default='Pendiente')
    timestamp = db.Column(db.DateTime, nullable=False)

    # Llaves foráneas
    id_convenio = db.Column(db.Integer, db.ForeignKey('convenio.id'), nullable=False)
    id_autor = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)


class Etapa(db.Model):
    """
    Contiene las etapas del proceso de convenio
    """
    id = db.Column(db.Integer, primary_key=True)
    etapa = db.Column(db.String, nullable=False)
    #plazo

    # Relaciones -> es llave foránea en:
    trayectoria_etapas = db.relationship('TrayectoriaEtapa', backref='etapa')
    etapa_hito = db.relationship('Hito', backref='etapa')

    def __repr__(self):
        return f'<{self.id} - {self.etapa}>'


class TrayectoriaEtapa(db.Model):
    """
    Contiene las fechas de ingreso y salida de los convenios en las diferentes etapas del proceso.
    """
    id = db.Column(db.Integer, primary_key=True)
    ingreso = db.Column(db.Date, nullable=False)
    timestamp_ingreso = db.Column(db.DateTime, nullable=False)
    salida = db.Column(db.Date, nullable=True)
    timestamp_salida = db.Column(db.DateTime, nullable=True)

    # LLaves foráneas
    id_convenio = db.Column(db.Integer, db.ForeignKey('convenio.id'), nullable=False)
    id_etapa = db.Column(db.Integer, db.ForeignKey('etapa.id'), nullable=False)

    def __repr__(self):
        return f'<{self.etapa.etapa} - {self.ingreso} - {self.salida}>'

    def actualizar_trayectoria_etapa(self, form):
        # Actualizar fecha salida etapa actual
        self.salida = form.fecha_etapa.data
        self.timestamp_salida = datetime.today()
        # Ingresar nueva etapa
        nueva_etapa = TrayectoriaEtapa(
            ingreso=form.fecha_etapa.data,
            timestamp_ingreso=datetime.today(),
            id_convenio=self.id_convenio,
            id_etapa=form.etapa.data
        )
        db.session.add(nueva_etapa)
        db.session.commit()


class TrayectoriaEquipo(db.Model):
    """
    Contiene las fechas de ingreso y salida de las equipos de trabajo por los que ha pasado un convenio.
    """
    id = db.Column(db.Integer, primary_key=True)
    ingreso = db.Column(db.Date, nullable=False)
    timestamp_ingreso = db.Column(db.DateTime, nullable=False)
    salida = db.Column(db.Date, nullable=True)
    timestamp_salida = db.Column(db.DateTime, nullable=True)

    # Llaves foráneas
    id_convenio = db.Column(db.Integer, db.ForeignKey('convenio.id'), nullable=False)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=False)

    def __repr__(self):
        return f'<Convenio: {self.id_convenio} - Equipo: {self.equipo.sigla} - Ingreso: {self.ingreso}>'


class User(db.Model, UserMixin):
    """
    Contiene a los usuarios, el tipo de cuenta y la persona asociada.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    permisos = db.Column(db.String(60), nullable=False)

    # Laves foráneas
    id_persona = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=False)
    # Relaciones -> es llave foránea en:
    bitacoras_analista = db.relationship('BitacoraAnalista', backref='autor')
    tareas = db.relationship('BitacoraTarea', backref='autor')

    def __repr__(self):
        return f'<{self.persona.nombre} - {self.username} - {self.permisos}>'