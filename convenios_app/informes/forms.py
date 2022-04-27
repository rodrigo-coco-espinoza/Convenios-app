from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField, IntegerField, SelectMultipleField, validators
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Length, ValidationError, Email
from convenios_app.models import Institucion, Convenio, TrayectoriaEtapa, TrayectoriaEquipo
from sqlalchemy import and_
from convenios_app.main.utils import formato_nombre, generar_nombre_convenio
from wtforms.widgets import TextArea
from wtforms.widgets import DateInput
from datetime import date, datetime
from convenios_app.bitacoras.forms import ETAPAS, EQUIPOS


class MisConveniosInfoConvenioForm(FlaskForm):
    id_convenio = HiddenField('id_trayectoria_convenio', default=0)
    id_trayectoriaEtapa = HiddenField('id_trayectoria_etapa')
    etapa = SelectField('Etapa actual del convenio', choices=ETAPAS)
    fecha_etapa = DateField('Fecha', widget=DateInput(), validators=(validators.Optional(),))
    id_trayectoriaEquipo_1 = HiddenField('id_equipo_1')
    equipo_1 = SelectField('Equipo en el que se encuentra el convenio', choices=EQUIPOS)
    fecha_equipo_1 = DateField('Fecha', widget=DateInput(), validators=(validators.Optional(),))
    id_trayectoriaEquipo_2 = HiddenField('id_equipo_2')
    equipo_2 = SelectField('Equipo en el que se encuentra el convenio', choices=EQUIPOS)
    fecha_equipo_2 = DateField('Fecha', widget=DateInput(), validators=(validators.Optional(),))
    id_trayectoriaEquipo_3 = HiddenField('id_equipo_3')
    equipo_3 = SelectField('Equipo en el que se encuentra el convenio', choices=EQUIPOS)
    fecha_equipo_3 = DateField('Fecha', widget=DateInput(), validators=(validators.Optional(),))
    id_trayectoriaEquipo_4 = HiddenField('id_equipo_4')
    equipo_4 = SelectField('Equipo en el que se encuentra el convenio', choices=EQUIPOS)
    fecha_equipo_4 = DateField('Fecha', widget=DateInput(), validators=(validators.Optional(),))

    def validate_id_convenio(self, id_convenio):
        if int(id_convenio.data) == 0:
            raise ValidationError('Debe seleccionar un convenio.')

    def validate_fecha_etapa(self, fecha_etapa):
        if int(self.id_convenio.data) != 0:
            etapa_actual = TrayectoriaEtapa.query.get(self.id_trayectoriaEtapa.data)
            if etapa_actual.ingreso > fecha_etapa.data:
                raise ValidationError(f'No puede seleccionar una fecha anterior a {etapa_actual.ingreso}')

    def validate_equipo_1(self, equipo_1):
        if int(self.id_convenio.data) != 0:
            # Validar que se asigne al menos a un equipo
            if [equipo_1.data, self.equipo_2.data, self.equipo_3.data, self.equipo_4.data].count('0') == 4:
                raise ValidationError(f'El convenio debe estar asignado a un equipo.')
            # Si se cambia de equipo, que no sea por uno que estaba asignado
            otras_etapas_actuales = [
                (lambda trayectoria_2: TrayectoriaEquipo.query.get(trayectoria_2).id_equipo if trayectoria_2 != '0' else 0)(
                    self.id_trayectoriaEquipo_2.data),
                (lambda trayectoria_3: TrayectoriaEquipo.query.get(trayectoria_3).id_equipo if trayectoria_3 != '0' else 0)(
                    self.id_trayectoriaEquipo_3.data),
                (lambda trayectoria_4: TrayectoriaEquipo.query.get(trayectoria_4).id_equipo if trayectoria_4 != '0' else 0)(
                    self.id_trayectoriaEquipo_4.data)
            ]
            if int(equipo_1.data) in otras_etapas_actuales and equipo_1.data != '0':
                raise ValidationError(f'Esta área ya estaba asiganda. Vuelva a cargar el convenio.')
            # Si se cambia de equipo (o se deja de asingar) verificar que la fecha sea mayor a la actual
            if self.id_trayectoriaEquipo_1.data != '0' and TrayectoriaEquipo.query.get(
                    self.id_trayectoriaEquipo_1.data).id_equipo != int(equipo_1.data):
                equipo_actual = TrayectoriaEquipo.query.get(self.id_trayectoriaEquipo_1.data)
                if self.fecha_equipo_1.data is None:
                    raise ValidationError('Debe seleccionar una fecha.')
                if equipo_actual.ingreso > self.fecha_equipo_1.data:
                    raise ValidationError(f'No puede seleccionar una fecha anterior a {equipo_actual.ingreso}')

    def validate_equipo_2(self, equipo_2):
        if int(self.id_convenio.data) != 0:
            # Validar que el equipo no esté repetido
            if [self.equipo_1.data, equipo_2.data].count(equipo_2.data) > 1 and equipo_2.data != '0':
                raise ValidationError(f'Equipo de trabajo repetido.Vuelva a cargar el convenio.')
            # Si se cambia de equipo, que no sea por uno que estaba asignado
            otras_etapas_actuales = [
                (lambda trayectoria_1: TrayectoriaEquipo.query.get(
                    trayectoria_1).id_equipo if trayectoria_1 != '0' else 0)(self.id_trayectoriaEquipo_1.data),
                (lambda trayectoria_3: TrayectoriaEquipo.query.get(
                    trayectoria_3).id_equipo if trayectoria_3 != '0' else 0)(self.id_trayectoriaEquipo_3.data),
                (lambda trayectoria_4: TrayectoriaEquipo.query.get(
                    trayectoria_4).id_equipo if trayectoria_4 != '0' else 0)(self.id_trayectoriaEquipo_4.data)
            ]
            if int(equipo_2.data) in otras_etapas_actuales and equipo_2.data != '0':
                raise ValidationError(f'Esta área ya estaba asiganda. Vuelva a cargar el convenio.')

            # Si se cambia de equipo (o se deja de asingar) verificar que la fecha sea mayor a la actual
            if self.id_trayectoriaEquipo_2.data != '0' and TrayectoriaEquipo.query.get(
                    self.id_trayectoriaEquipo_2.data).id_equipo != int(equipo_2.data):
                equipo_actual = TrayectoriaEquipo.query.get(self.id_trayectoriaEquipo_2.data)
                if self.fecha_equipo_2.data is None:
                    raise ValidationError('Debe seleccionar una fecha.')
                if equipo_actual.ingreso > self.fecha_equipo_2.data:
                    raise ValidationError(f'No puede seleccionar una fecha anterior a {equipo_actual.ingreso}')

            # Si se asigna nuevo equipo verificar que se haya ingresado fecha
            if self.id_trayectoriaEquipo_2.data == '0' and equipo_2.data != '0' and self.fecha_equipo_2.data is None:
                raise ValidationError('Debe seleccionar una fecha.')

    def validate_equipo_3(self, equipo_3):
        if int(self.id_convenio.data) != 0:
            # Validar que el equipo no esté repetido
            if [self.equipo_1.data, self.equipo_2.data, equipo_3.data].count(equipo_3.data) > 1 and equipo_3.data != '0':
                raise ValidationError(f'Equipo de trabajo repetido. Vuelva a cargar el convenio.')
            # Si se cambia de equipo, que no sea por uno que estaba asignado
            otras_etapas_actuales = [
                (lambda trayectoria_1: TrayectoriaEquipo.query.get(
                    trayectoria_1).id_equipo if trayectoria_1 != '0' else 0)(self.id_trayectoriaEquipo_1.data),
                (lambda trayectoria_2: TrayectoriaEquipo.query.get(
                    trayectoria_2).id_equipo if trayectoria_2 != '0' else 0)(self.id_trayectoriaEquipo_2.data),
                (lambda trayectoria_4: TrayectoriaEquipo.query.get(
                    trayectoria_4).id_equipo if trayectoria_4 != '0' else 0)(self.id_trayectoriaEquipo_4.data)
            ]
            if int(equipo_3.data) in otras_etapas_actuales and equipo_3.data != '0':
                raise ValidationError(f'Esta área ya estaba asiganda. Vuelva a cargar el convenio.')

            # Si se cambia de equipo (o se deja de asingar) verificar que la fecha sea mayor a la actual
            if self.id_trayectoriaEquipo_3.data != '0' and TrayectoriaEquipo.query.get(
                    self.id_trayectoriaEquipo_3.data).id_equipo != int(equipo_3.data):
                equipo_actual = TrayectoriaEquipo.query.get(self.id_trayectoriaEquipo_3.data)
                if self.fecha_equipo_3.data is None:
                    raise ValidationError('Debe seleccionar una fecha.')
                if equipo_actual.ingreso > self.fecha_equipo_3.data:
                    raise ValidationError(f'No puede seleccionar una fecha anterior a {equipo_actual.ingreso}')

            # Si se asigna nuevo equipo verificar que se haya ingresado fecha
            if self.id_trayectoriaEquipo_3.data == '0' and equipo_3.data != '0' and self.fecha_equipo_3.data is None:
                raise ValidationError('Debe seleccionar una fecha.')

    def validate_equipo_4(self, equipo_4):
        if int(self.id_convenio.data) != 0:
            # Validar que el equipo no esté repetido
            if ([self.equipo_1.data, self.equipo_2.data, self.equipo_3.data, equipo_4.data].count(equipo_4.data) > 1
                    and equipo_4.data != '0'):
                raise ValidationError(f'Equipo de trabajo repetido. Vuelva a cargar el convenio.')
            # Si se cambia de equipo, que no sea por uno que estaba asignado
            otras_etapas_actuales = [
                (lambda trayectoria_1: TrayectoriaEquipo.query.get(
                    trayectoria_1).id_equipo if trayectoria_1 != '0' else 0)(self.id_trayectoriaEquipo_1.data),
                (lambda trayectoria_2: TrayectoriaEquipo.query.get(
                    trayectoria_2).id_equipo if trayectoria_2 != '0' else 0)(self.id_trayectoriaEquipo_2.data),
                (lambda trayectoria_3: TrayectoriaEquipo.query.get(
                    trayectoria_3).id_equipo if trayectoria_3 != '0' else 0)(self.id_trayectoriaEquipo_3.data)
            ]
            if int(equipo_4.data) in otras_etapas_actuales and equipo_4.data != '0':
                raise ValidationError(f'Esta área ya estaba asiganda. Vuelva a cargar el convenio.')

            # Si se cambia de equipo (o se deja de asingar) verificar que la fecha sea mayor a la actual
            if self.id_trayectoriaEquipo_4.data != '0' and TrayectoriaEquipo.query.get(
                    self.id_trayectoriaEquipo_4.data).id_equipo != int(equipo_4.data):
                equipo_actual = TrayectoriaEquipo.query.get(self.id_trayectoriaEquipo_4.data)
                if self.fecha_equipo_4.data is None:
                    raise ValidationError('Debe seleccionar una fecha.')
                if equipo_actual.ingreso > self.fecha_equipo_4.data:
                    raise ValidationError(f'No puede seleccionar una fecha anterior a {equipo_actual.ingreso}')

            # Si se asigna nuevo equipo verificar que se haya ingresado fecha
            if self.id_trayectoriaEquipo_4.data == '0' and equipo_4.data != '0' and self.fecha_equipo_4.data is None:
                raise ValidationError('Debe seleccionar una fecha.')


class MisConveniosBitacoraForm(FlaskForm):
    id_convenio_bitacora = HiddenField('id_convenio_bitacora', default=0)
    observacion = StringField('Observación', render_kw={'placeholder': 'Observación'}, widget=TextArea(),
                                validators=[DataRequired()])
    fecha = DateField('Fecha', default=date.today, widget=DateInput(), validators=[DataRequired()])


class MisConveniosTareaForm(FlaskForm):
    id_convenio_tarea = HiddenField('id_convenio_tarea', default=0)
    tarea = StringField('Tarea', render_kw={'placeholder': 'Tarea a realizar'}, widget=TextArea(),
                              validators=[DataRequired()])
    plazo = DateField('Fecha', default=date.today, widget=DateInput(), validators=[DataRequired()])