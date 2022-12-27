from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField, IntegerField, SelectMultipleField, validators
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Length, ValidationError, Email
from convenios_app.models import Institucion, Convenio, TrayectoriaEtapa, TrayectoriaEquipo, RecepcionConvenio, EntregaConvenio, NominaEntrega
from sqlalchemy import and_
from convenios_app.main.utils import formato_nombre, generar_nombre_convenio
from wtforms.widgets import TextArea
from wtforms.widgets import DateInput
from datetime import date, datetime

ETAPAS = [(1, 'Definición de Alcance del Convenio'), (2, 'Confección de Documento de Convenio'),
          (3, 'Gestión de Visto Bueno y Firmas'), (4, 'Generación de Resolución y Protocolo Técnico'), (5, 'Finalizado')]
EQUIPOS = [(0, 'Sin asignar'), (1, 'AIET'), (2, 'IE'), (3, 'SDAC'), (4, 'SDAV'), (5, 'SDF'), (6, 'SDGEET'), (7, 'SDI'),
           (8, 'SDJ'), (9, 'GDIR'), (10, 'DGC'), (11, 'SDA'), (12, 'SDACORP'), (13, 'SDDP'), (14, 'SDN')]


class NuevoConvenioForm(FlaskForm):
    nombre = StringField('Nombre del convenio', render_kw={'placeholder': 'Intercambio de información'},
                         validators=[DataRequired()])
    tipo = SelectField('Tipo de documento', choices=['Seleccionar',
                                                     'Convenio',
                                                     'Adendum'])
    convenio_padre = SelectField('Convenio al cual pertenece el adendum',
                                 choices=[(0, 'Seleccione una institución para ver los convenios')],
                                 validate_choice=False)
    institucion = SelectField('Institución con la que se firma el convenio')
    coord_sii = SelectField('Coordinador SII')
    sup_sii = SelectField('Suplente SII')
    coord_ie = SelectField('Coordinador institución externa', choices=[(0, 'Seleccionar')], validate_choice=False)
    sup_ie = SelectField('Suplente institución externa', choices=[(0, 'Seleccionar')], validate_choice=False)
    responsable_convenio_ie = SelectField('Responsable del convenio IE', choices=[(0, 'Seleccionar')],
                                          validate_choice=False)
    submit = SubmitField('Agregar')

    def validate_nombre(self, nombre):
        """
        Valida que no exista otro convenio con el mismo nombre con la institución
        """
        convenio = Convenio.query.filter(and_(Convenio.nombre == formato_nombre(nombre.data),
                                              Convenio.id_institucion == int(self.institucion.data))).first()

        if convenio:
            institucion = Institucion.query.get(self.institucion.data)
            raise ValidationError(f' Ya existe {convenio.nombre} registrado en {institucion.nombre}.')

    def validate_tipo(self, tipo):
        if tipo.data == 'Seleccionar':
            raise ValidationError('Debe seleccionar el tipo de documento.')
        elif tipo.data == 'Adendum' and int(self.convenio_padre.data) == 0:
            self.tipo.data = 'Seleccionar'
            raise ValidationError('Debe seleccionar el convenio al cual pertenece este adendum.')

    def validate_coord_sii(self, coord_sii):
        if int(coord_sii.data) == 0:
            raise ValidationError('Debe seleccionar un coordinador del SII.')

    def validate_sup_sii(self, sup_sii):
        if sup_sii.data == self.coord_sii.data and int(sup_sii.data) != 0:
            raise ValidationError('Debe seleccionar un suplente distinto al coordinador del SII.')

    def validate_sup_ie(self, sup_ie):
        if sup_ie.data == self.coord_ie.data and int(sup_ie.data) != 0:
            raise ValidationError('Debe seleccionar un suplente distinto al coordinador de la IE.')

    def validate_institucion(self, institucion):
        if institucion.data == '0':
            raise ValidationError('Debe seleccionar institución.')


class EditarConvenioForm(FlaskForm):
    id_convenio = HiddenField('id_convenio', default=0)
    id_institucion = HiddenField('id_institucuion')
    nombre = StringField('Nombre del convenio', render_kw={'placeholder': 'Intercambio de información'},
                         validators=[DataRequired()])
    tipo = SelectField('Tipo de documento', choices=['Seleccionar',
                                                     'Convenio',
                                                     'Adendum'])
    convenio_padre = SelectField('Convenio al cual pertenece el adendum',
                                 choices=[(0, 'Seleccione una institución para ver los convenios')],
                                 validate_choice=False)
    convenio_reemplazo = SelectField('Convenio por el cual se reemplaza')
    estado = SelectField('Estado', choices=['En proceso',
                                    'En producción',
                                    'Pausado',
                                    'Reemplazado',
                                    'Cancelado'])
    institucion = StringField('Institución con la que se firma el convenio')
    coord_sii = SelectField('Coordinador SII')
    sup_sii = SelectField('Suplente SII')
    coord_ie = SelectField('Coordinador institución externa', choices=[(0, 'Seleccionar')], validate_choice=False)
    sup_ie = SelectField('Suplente institución externa', choices=[(0, 'Seleccionar')], validate_choice=False)
    responsable_convenio_ie = SelectField('Responsable del convenio IE', choices=[(0, 'Seleccionar')],
                                          validate_choice=False)
    submit = SubmitField('Editar')


    
    def validate_nombre(self, nombre):
        """
        Valida que no exista otro convenio con el mismo nombre con la institución
        """
        convenio = Convenio.query.filter(and_(Convenio.nombre == formato_nombre(nombre.data),
                                              Convenio.id_institucion == int(self.id_institucion.data),
                                              Convenio.id != int(self.id_convenio.data))).first()
        if convenio:
            institucion = Institucion.query.get(self.id_institucion.data)
            raise ValidationError(f' Ya existe {convenio.nombre} registrado en {institucion.nombre}.')

    def validate_tipo(self, tipo):
        if tipo.data == 'Seleccionar':
            raise ValidationError('Debe seleccionar el tipo de documento.')
        elif tipo.data == 'Adendum' and int(self.convenio_padre.data) == 0:
            self.tipo.data = 'Seleccionar'
            raise ValidationError('Debe seleccionar el convenio al cual pertenece este adendum.')

    def validate_coord_sii(self, coord_sii):
        if int(coord_sii.data) == 0:
            raise ValidationError('Debe seleccionar un coordinador del SII.')

    def validate_sup_sii(self, sup_sii):
        if sup_sii.data == self.coord_sii.data and int(sup_sii.data) != 0:
            raise ValidationError('Debe seleccionar un suplente distinto al coordinador del SII.')

    def validate_sup_ie(self, sup_ie):
        if sup_ie.data == self.coord_ie.data and int(sup_ie.data) != 0:
            raise ValidationError('Debe seleccionar un suplente distinto al coordinador de la IE.')

    def validate_estado(self, estado):
        # Verificar que se haya finalizado el convenio
        etapa_actual = TrayectoriaEtapa.query.filter(TrayectoriaEtapa.id_convenio == self.id_convenio.data).order_by(TrayectoriaEtapa.salida.asc()).first()
        if etapa_actual.salida is None and estado.data != 'En proceso':
            raise ValidationError('Debe finalizar el convenio antes de cambiar el estado.')
        # Verificar que existe convenio de reemplazo
        if estado.data == 'Reemplazado' and int(self.convenio_reemplazo.data) == 0:
            raise ValidationError('Debe seleccionar el convenio por el cual sera reemplazado. Vuelva a seleccionar el convenio para editar.')

class NuevaBitacoraAnalistaForm(FlaskForm):
    observacion = StringField('Observación', render_kw={'placeholder': 'Observación'}, widget=TextArea(),
                              validators=[DataRequired()])
    fecha = DateField('Fecha', default=date.today, widget=DateInput(), validators=[DataRequired()])


class NuevaTareaForm(FlaskForm):
    tarea = StringField('Tarea', render_kw={'placeholder': 'Tarea a realizar'}, widget=TextArea(),
                        validators=[DataRequired()])
    plazo = DateField('Fecha', default=date.today, widget=DateInput(), validators=[DataRequired()])


class InfoConvenioForm(FlaskForm):
    id_convenio = HiddenField('id_convenio', default=0)
    id_trayectoria = HiddenField('id_trayectoria_etapa')
    etapa = SelectField('Etapa actual del convenio', choices=ETAPAS)
    fecha_etapa = DateField('Fecha', widget=DateInput())
    id_trayectoria_1 = HiddenField('id_equipo_1')
    equipo_1 = SelectField('Equipo en el que se encuentra el convenio', choices=EQUIPOS)
    fecha_equipo_1 = DateField('Fecha', widget=DateInput(), validators=(validators.Optional(),))
    id_trayectoria_2 = HiddenField('id_equipo_2')
    equipo_2 = SelectField('Equipo en el que se encuentra el convenio', choices=EQUIPOS)
    fecha_equipo_2 = DateField('Fecha', widget=DateInput(), validators=(validators.Optional(),))
    id_trayectoria_3 = HiddenField('id_equipo_3')
    equipo_3 = SelectField('Equipo en el que se encuentra el convenio', choices=EQUIPOS)
    fecha_equipo_3 = DateField('Fecha', widget=DateInput(), validators=(validators.Optional(),))
    id_trayectoria_4 = HiddenField('id_equipo_4')
    equipo_4 = SelectField('Equipo en el que se encuentra el convenio', choices=EQUIPOS)
    fecha_equipo_4 = DateField('Fecha', widget=DateInput(), validators=(validators.Optional(),))
    fecha_firma_documento = DateField('Fecha firma documento', widget=DateInput(), validators=(validators.Optional(),))
    fecha_firma_resolucion = DateField('Fecha resolución', widget=DateInput(), validators=(validators.Optional(),))
    nro_resolucion = IntegerField('N° de resolución', validators=(validators.Optional(),), render_kw={"placeholder": 'N° de resolución'})
    proyecto = StringField('N° de proyecto') 
    gabinete_electronico = StringField('N° de GE')
    link_resolucion = StringField('Link resolución', render_kw={'placeholder': 'Ingrese link de la resolución'})
    link_project = StringField('Link project', render_kw={'placeholder': 'Ingrese link del Project'})
    link_protocolo = StringField('Link protocolo técnico', render_kw={'placeholder': 'Ingrese link del protocolo técnico'})
    link_repositorio = StringField('Link repositorio', render_kw={'placeholder': 'Ingrese link del repositorio'})

    def validate_fecha_etapa(self, fecha_etapa):
        etapa_actual = TrayectoriaEtapa.query.get(self.id_trayectoria.data)
        if etapa_actual.ingreso > fecha_etapa.data:
            raise ValidationError(f'No puede seleccionar una fecha anterior a {etapa_actual.ingreso}')
        if fecha_etapa.data > date.today():
            raise ValidationError('No puede seleccionar una fecha en el futuro.')

    def validate_equipo_1(self, equipo_1):
        # Validar que se asigne al menos a un equipo
        if [equipo_1.data, self.equipo_2.data, self.equipo_3.data, self.equipo_4.data].count('0') == 4:
            raise ValidationError(f'El convenio debe estar asignado a un equipo.')
        # Si se cambia de equipo, que no sea por uno que estaba asignado
        otras_etapas_actuales = [
            (lambda trayectoria_2: TrayectoriaEquipo.query.get(trayectoria_2).id_equipo if trayectoria_2 != '0' else 0)(self.id_trayectoria_2.data),
            (lambda trayectoria_3: TrayectoriaEquipo.query.get(trayectoria_3).id_equipo if trayectoria_3 != '0' else 0)(self.id_trayectoria_3.data),
            (lambda trayectoria_4: TrayectoriaEquipo.query.get(trayectoria_4).id_equipo if trayectoria_4 != '0' else 0)(self.id_trayectoria_4.data)
        ]
        if int(equipo_1.data) in otras_etapas_actuales and equipo_1.data != '0':
            raise ValidationError(f'Esta área ya estaba asiganda. Vuelva a cargar el convenio.')
        # Si se cambia de equipo (o se deja de asingar) verificar que la fecha sea mayor a la actual
        if self.id_trayectoria_1.data != '0' and TrayectoriaEquipo.query.get(self.id_trayectoria_1.data).id_equipo != int(equipo_1.data):
            equipo_actual = TrayectoriaEquipo.query.get(self.id_trayectoria_1.data)
            if self.fecha_equipo_1.data is None:
                raise ValidationError('Debe seleccionar una fecha.')
            if equipo_actual.ingreso > self.fecha_equipo_1.data:
                raise ValidationError(f'No puede seleccionar una fecha anterior a {equipo_actual.ingreso}')
            if self.fecha_equipo_1.data > date.today():
                raise ValidationError('No puede seleccionar una fecha en el futuro.')

    def validate_equipo_2(self, equipo_2):
        # Validar que el equipo no esté repetido
        if [self.equipo_1.data, equipo_2.data].count(equipo_2.data) > 1 and equipo_2.data != '0':
            raise ValidationError(f'Equipo de trabajo repetido.Vuelva a cargar el convenio.')
        # Si se cambia de equipo, que no sea por uno que estaba asignado
        otras_etapas_actuales = [
            (lambda trayectoria_1: TrayectoriaEquipo.query.get(
                trayectoria_1).id_equipo if trayectoria_1 != '0' else 0)(self.id_trayectoria_1.data),
            (lambda trayectoria_3: TrayectoriaEquipo.query.get(
                trayectoria_3).id_equipo if trayectoria_3 != '0' else 0)(self.id_trayectoria_3.data),
            (lambda trayectoria_4: TrayectoriaEquipo.query.get(
                trayectoria_4).id_equipo if trayectoria_4 != '0' else 0)(self.id_trayectoria_4.data)
        ]
        if int(equipo_2.data) in otras_etapas_actuales and equipo_2.data != '0':
            raise ValidationError(f'Esta área ya estaba asiganda. Vuelva a cargar el convenio.')

        # Si se cambia de equipo (o se deja de asingar) verificar que la fecha sea mayor a la actual
        if self.id_trayectoria_2.data != '0' and TrayectoriaEquipo.query.get(
                self.id_trayectoria_2.data).id_equipo != int(equipo_2.data):
            equipo_actual = TrayectoriaEquipo.query.get(self.id_trayectoria_2.data)
            if self.fecha_equipo_2.data is None:
                raise ValidationError('Debe seleccionar una fecha.')
            if equipo_actual.ingreso > self.fecha_equipo_2.data:
                raise ValidationError(f'No puede seleccionar una fecha anterior a {equipo_actual.ingreso}')
            if self.fecha_equipo_2.data > date.today():
                raise ValidationError('No puede seleccionar una fecha en el futuro.')

        # Si se asigna nuevo equipo verificar que se haya ingresado fecha
        if self.id_trayectoria_2.data == '0' and equipo_2.data != '0': 
            if self.fecha_equipo_2.data is None:
                raise ValidationError('Debe seleccionar una fecha.')
            if self.fecha_equipo_2.data > date.today():
                raise ValidationError('No puede seleccionar una fecha en el futuro.')

    def validate_equipo_3(self, equipo_3):
        # Validar que el equipo no esté repetido
        if [self.equipo_1.data, self.equipo_2.data, equipo_3.data].count(equipo_3.data) > 1 and equipo_3.data != '0':
            raise ValidationError(f'Equipo de trabajo repetido. Vuelva a cargar el convenio.')
        # Si se cambia de equipo, que no sea por uno que estaba asignado
        otras_etapas_actuales = [
            (lambda trayectoria_1: TrayectoriaEquipo.query.get(
                trayectoria_1).id_equipo if trayectoria_1 != '0' else 0)(self.id_trayectoria_1.data),
            (lambda trayectoria_2: TrayectoriaEquipo.query.get(
                trayectoria_2).id_equipo if trayectoria_2 != '0' else 0)(self.id_trayectoria_2.data),
            (lambda trayectoria_4: TrayectoriaEquipo.query.get(
                trayectoria_4).id_equipo if trayectoria_4 != '0' else 0)(self.id_trayectoria_4.data)
        ]
        if int(equipo_3.data) in otras_etapas_actuales and equipo_3.data != '0':
            raise ValidationError(f'Esta área ya estaba asiganda. Vuelva a cargar el convenio.')

        # Si se cambia de equipo (o se deja de asingar) verificar que la fecha sea mayor a la actual
        if self.id_trayectoria_3.data != '0' and TrayectoriaEquipo.query.get(
                self.id_trayectoria_3.data).id_equipo != int(equipo_3.data):
            equipo_actual = TrayectoriaEquipo.query.get(self.id_trayectoria_3.data)
            if self.fecha_equipo_3.data is None:
                raise ValidationError('Debe seleccionar una fecha.')
            if equipo_actual.ingreso > self.fecha_equipo_3.data:
                raise ValidationError(f'No puede seleccionar una fecha anterior a {equipo_actual.ingreso}')
            if self.fecha_equipo_3.data > date.today():
                raise ValidationError('No puede seleccionar una fecha en el futuro.')

        # Si se asigna nuevo equipo verificar que se haya ingresado fecha
        if self.id_trayectoria_3.data == '0' and equipo_3.data != '0':
            if self.fecha_equipo_3.data is None:
                raise ValidationError('Debe seleccionar una fecha.')
            if self.fecha_equipo_3.data > date.today():
                raise ValidationError('No puede seleccionar una fecha en el futuro.')

    def validate_equipo_4(self, equipo_4):
        # Validar que el equipo no esté repetido
        if ([self.equipo_1.data, self.equipo_2.data, self.equipo_3.data, equipo_4.data].count(equipo_4.data) > 1
                and equipo_4.data != '0'):
            raise ValidationError(f'Equipo de trabajo repetido. Vuelva a cargar el convenio.')
        # Si se cambia de equipo, que no sea por uno que estaba asignado
        otras_etapas_actuales = [
            (lambda trayectoria_1: TrayectoriaEquipo.query.get(
                trayectoria_1).id_equipo if trayectoria_1 != '0' else 0)(self.id_trayectoria_1.data),
            (lambda trayectoria_2: TrayectoriaEquipo.query.get(
                trayectoria_2).id_equipo if trayectoria_2 != '0' else 0)(self.id_trayectoria_2.data),
            (lambda trayectoria_3: TrayectoriaEquipo.query.get(
                trayectoria_3).id_equipo if trayectoria_3 != '0' else 0)(self.id_trayectoria_3.data)
        ]
        if int(equipo_4.data) in otras_etapas_actuales and equipo_4.data != '0':
            raise ValidationError(f'Esta área ya estaba asiganda. Vuelva a cargar el convenio.')

        # Si se cambia de equipo (o se deja de asingar) verificar que la fecha sea mayor a la actual
        if self.id_trayectoria_4.data != '0' and TrayectoriaEquipo.query.get(self.id_trayectoria_4.data).id_equipo != int(equipo_4.data):
            equipo_actual = TrayectoriaEquipo.query.get(self.id_trayectoria_4.data)
            if self.fecha_equipo_4.data is None:
                raise ValidationError('Debe seleccionar una fecha.')
            if equipo_actual.ingreso > self.fecha_equipo_4.data:
                raise ValidationError(f'No puede seleccionar una fecha anterior a {equipo_actual.ingreso}')
            if self.fecha_equipo_4.data > date.today():
                raise ValidationError('No puede seleccionar una fecha en el futuro.')

        # Si se asigna nuevo equipo verificar que se haya ingresado fecha
        if self.id_trayectoria_4.data == '0' and equipo_4.data != '0':
            if self.fecha_equipo_4.data is None:
                raise ValidationError('Debe seleccionar una fecha.')
            if self.fecha_equipo_4.data > date.today():
                raise ValidationError('No puede seleccionar una fecha en el futuro.')
    
    def validate_proyecto(self, proyecto):
        if len(str(proyecto.data)) > 0:
            try:
                int(proyecto.data)
            except:
                raise ValidationError('Debe ingresar solo números.')

        if proyecto.data != "":
            nro_proyecto = Convenio.query.filter(
                and_(Convenio.proyecto == proyecto.data, Convenio.id != int(self.id_convenio.data))).first()
            if nro_proyecto:
                raise ValidationError(
                    f'El número de proyecto {proyecto.data} ya está registrado.')

    def validate_gabinete_electronico(self, gabinete_electronico):
        if len(str(gabinete_electronico.data)) > 0:
            try:
                int(gabinete_electronico.data)
            except:
                raise ValidationError('Debe ingresar solo números.')

class AgregarRecepcionForm(FlaskForm):
    id_convenio = HiddenField('ID Convenio')
    nombre = StringField('Nombre', render_kw={"placeholder": "Nombre de la recepción según convenio"}, validators=[DataRequired(), Length(min=2)])
    archivo = StringField('Archivo', render_kw={'placeholder': 'Nombre del archivo a recibir'})
    sd_recibe = SelectField('Subdirección que recibe la información')
    #TODO: COMPLETAR MÉTODOS DE TRASPASO
    metodo = SelectField('Método de traspaso', choices=['Seleccione método',
                                                        'SFTP',
                                                        'En línea',
                                                        'WMS/WFS',
                                                        'Correo electrónico',
                                                        'Otro'])

    def validate_archivo(self, archivo):
        if archivo.data != "":
                  if RecepcionConvenio.query.filter(and_(RecepcionConvenio.id_convenio == self.id_convenio.data,
                                                      RecepcionConvenio.archivo == archivo.data)).first():
                      raise ValidationError('El nombre de archivo ya existe para este convenio.')

    def validate_sd_recibe(self, sd_recibe):
        if int(sd_recibe.data) == 0:
            raise ValidationError('Debe seleccionar una subdirección.')

    def validate_metodo(self, metodo):
        if metodo.data == 'Seleccione método':
            raise ValidationError('Debe seleccionar método de traspaso de la información.')

class EditarRecepcionForm(FlaskForm):
    id_recepcion_editar = HiddenField('ID Recepción')
    nombre_editar = StringField('Nombre', validators=[DataRequired(), Length(min=2)])
    carpeta_editar = StringField('Carpeta')
    archivo_editar = StringField('Archivo')
    sd_recibe_editar = SelectField('Subdirección', choices=[(0, '')], validate_choice=False)
    #TODO: COMPLETAR MÉTODOS DE TRASPASO
    metodo_editar = SelectField('Método de traspaso', choices=['SFTP',
                                                            'En línea',
                                                            'WMS/WFS',
                                                            'Correo electrónico',
                                                            'Otro'])

class AgregarEntregaForm(FlaskForm):
    id_convenio_entrega = HiddenField('ID Convenio')
    nombre_entrega = StringField('Nombre', render_kw={'placeholder': 'Nombre de la entrega según convenio'}, validators=[DataRequired(), Length(min=2)])
    archivo_entrega = StringField('Archivo', render_kw={'placeholder': 'Nombre del archivo a entregar'})
    sd_prepara = SelectField('Subdirección que prepara la información')
    sd_envia = SelectField('Subdirección que envía la información')
    metodo_entrega = SelectField('Método de traspaso', choices=['Seleccione método',
                                                        'Gabiente Electrónico',
                                                        'SFTP',
                                                        'En línea',
                                                        'Correo electrónico',
                                                        'Otro'])
    requiere_nomina = SelectField('¿Requiere nómina?', choices=['Escoja una',
                                                        'Sí',
                                                        'No'])
    # Datos nómina
    nomina_registrada = SelectField('Nóminas registradas')
    nomina_archivo = StringField('Archivo nómina', render_kw={'placeholder': 'Nombre de la nómina para la extracción de datos'})
    nomina_metodo = SelectField('Método de traspaso nómina', choices=['Seleccione método',
                                                        'SFTP',
                                                        'En línea',
                                                        'Correo electrónico',
                                                        'Otro'])

    def validate_archivo_entrega(self, archivo_entrega):
        if archivo_entrega.data != "":
                  if EntregaConvenio.query.filter(and_(EntregaConvenio.id_convenio == self.id_convenio_entrega.data,
                                                      EntregaConvenio.archivo == archivo_entrega.data)).first():
                      raise ValidationError('El nombre de archivo ya existe para este convenio.')

    def validate_sd_prepara(self, sd_prepara):
        if int(sd_prepara.data) == 0:
            raise ValidationError('Debe seleccionar subdirección.')

    def validate_sd_envia(self, sd_envia):
        if int(sd_envia.data) == 0:
            raise ValidationError('Debe seleccionar subdirección.')

    def validate_metodo_entrega(self, metodo_entrega):
        if metodo_entrega.data == 'Seleccione método':
            raise ValidationError('Debe seleccionar método de traspaso de la información.')

    def validate_requiere_nomina(self, requiere_nomina):
        if requiere_nomina.data == 'Escoja una':
            raise ValidationError('Debe seleccionar si requiere o no nómina.')

    def validate_nomina_archivo(self, nomina_archivo):
        if self.requiere_nomina.data == 'Sí' and int(self.nomina_registrada.data) == 0:
            institucion = Convenio.query.get(self.id_convenio_entrega.data).id_institucion
            if nomina_archivo.data != "" and NominaEntrega.query.filter(and_(NominaEntrega.id_institucion == institucion,
                                                                            NominaEntrega.archivo == nomina_archivo.data)).first():
                 raise ValidationError('El nombre de archivo ya existe para esta nómina.')


    def validate_nomina_metodo(self, nomina_metodo):
        if self.requiere_nomina.data == 'Sí' and nomina_metodo.data == 'Seleccione método':
            raise ValidationError('Debe seleccionar método de traspaso de la nómina.')

class EditarEntregaForm(FlaskForm):
    id_entrega_editar = HiddenField('ID Entrega')
    id_nomina_editar = HiddenField('ID Nómina')
    nombre_entrega_editar = StringField('Nombre', render_kw={'placeholder': 'Nombre de la entrega según convenio'})
    archivo_entrega_editar = StringField('Archivo', render_kw={'placeholder': 'Nombre del archivo a entregar'})
    sd_prepara_editar = SelectField('Subdirección que prepara la información', validate_choice=False)
    sd_envia_editar = SelectField('Subdirección que envía la información', validate_choice=False)
    metodo_entrega_editar = SelectField('Método de traspaso', validate_choice=False, choices=['Gabiente Electrónico',
                                                                                            'SFTP',
                                                                                            'En línea',
                                                                                            'Correo electrónico',
                                                                                            'Otro'])
    requiere_nomina_editar = SelectField('¿Requiere nómina?', validate_choice=False, choices=['Sí',
                                                                                            'No'])
    # Datos nómina
    nomina_registrada_editar = SelectField('Nóminas registradas', validate_choice=False)
    nomina_archivo_editar = StringField('Archivo nómina', render_kw={'placeholder': 'Nombre de la nómina para la extracción de datos'})
    nomina_metodo_editar = SelectField('Método de traspaso nómina', validate_choice=False, choices=['Seleccione método',
                                                                                                    'SFTP',
                                                                                                    'En línea',
                                                                                                    'Correo electrónico',
                                                                                                    'Otro'])


class AgregarNominaForm(FlaskForm):
    id_convenio = HiddenField('ID_Convneio')
    

class RegistrarHitoForm(FlaskForm):
    id_convenio = HiddenField('ID Convenio')
    hito = SelectField('Seleccione hito')
    fecha = DateField('Fecha', default=date.today, widget=DateInput(), validators=[DataRequired()])
    minuta = StringField('Link minuta', render_kw={'placeholder': 'Ingrese link de la minuta'})
    grabacion = StringField('Link grabación', render_kw={'placeholder': 'Ingrese link de la grabación'})

    def validate_hito(self, hito):
        if int(hito.data) == 0:
            raise ValidationError('Debe selecciona hito para registrar.')


