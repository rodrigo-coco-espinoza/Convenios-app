from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, ValidationError, Email
from convenios_app.models import Institucion, Persona
from sqlalchemy import and_


class InstitucionForm(FlaskForm):
    id_institucion = HiddenField('id_institucion', default=0)
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=100)])
    sigla = StringField('Sigla', validators=[DataRequired()])
    rut = StringField('Rut', render_kw={"placeholder": "12345678-9"})
    direccion = StringField('Dirección')
    ministerio = SelectField('Ministerio al que pertenece')
    tipo = SelectField('Tipo de institución', validators=[DataRequired()], choices=['Seleccionar',
                                                                                    'Empresa pública',
                                                                                    'Municipalidad',
                                                                                    'Privado',
                                                                                    'Servicio Público'])
    submit = SubmitField('Confirmar')

    def validate_nombre(self, nombre):
        """
        Valida que el nombre no exista ya sea si es institución nueva o si se edita uno
        """
        institucion = Institucion.query.filter(and_(Institucion.nombre == nombre.data,
                                                    Institucion.id != int(self.id_institucion.data))).first()
        if institucion:
            raise ValidationError(f'{nombre.data} ya está registrado.')

    def validate_sigla(self, sigla):
        """
        Valida que la sigla no exista ya sea si es institución nueva o si se edita uno
        """
        institucion = Institucion.query.filter(and_(Institucion.sigla == sigla.data.upper(),
                                                    Institucion.id != int(self.id_institucion.data))).first()
        if institucion:
            raise ValidationError(f'{sigla.data.upper()} ya está registrado.')

    def validate_tipo(self, tipo):
        if tipo.data == 'Seleccionar':
            raise ValidationError('Debe seleccionar un tipo de institución.')



class PersonaForm(FlaskForm):
    id_persona = HiddenField('id_persona', default=0)
    nombre = StringField('Nombre', validators=[DataRequired()], render_kw={'placeholder': 'Nombre Apellido'})
    correo = StringField('Email', validators=[Email()])
    telefono = StringField('Telefono')
    cargo = StringField('Cargo')
    area = StringField('Área/Departamento')
    institucion = SelectField('Institución a la que pertenece')
    equipo = SelectField('Equipo de trabajo')
    submit = SubmitField('Confirmar')

    def validate_institucion(self, institucion):
        if int(institucion.data) == 0:
            raise ValidationError('Debe seleccionar una institución.')

    def validate_equipo(self, equipo):
        if int(equipo.data) == 0:
            raise ValidationError('Debe seleccionar un equipo.')

    def validate_nombre(self, nombre):
        """
        Valida que no exista otra persona con el mismo nombre en la misma institución
        """
        persona = Persona.query.filter(and_(Persona.nombre == nombre.data,
                                            Persona.id_institucion == int(self.institucion.data),
                                            Persona.id != int(self.id_persona.data))).first()
        if persona:
            institucion = Institucion.query.get(self.institucion.data)
            raise ValidationError(f' Ya existe {nombre.data} registrado en {institucion.nombre}.')

