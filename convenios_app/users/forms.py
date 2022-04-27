from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from convenios_app.models import Persona, User


class RegistrationForm(FlaskForm):
    user = StringField('Usuario', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar contraseña', validators=[DataRequired(), EqualTo('password')])
    # TODO: agrgar nuevos tipos
    tipo = SelectField('Tipo de cuenta', choices=['Seleccionar cuenta',
                                                  'Admin',
                                                  'Analista',
                                                  'Otro'])
    persona = SelectField('Persona usuaria')
    submit = SubmitField('Registrar')

    def validate_user(self, user):
        """
        Valida que el nombre de usuario no esté registrado en la base de datos.
        """
        usuario = User.query.filter(User.username == user.data).first()
        if usuario:
            raise ValidationError('Nombre de usuario ya está registrado. Por favor, pruebe otro.')

    def validate_tipo(self, tipo):
        """
        Valida que se haya seleccionado un tipo de cuenta.
        """
        if tipo.data == 'Seleccionar cuenta':
            raise ValidationError('Debe seleccionar un tipo de cuenta.')

    def validate_persona(self, persona):
        """
        Valida que se haya seleccionado a la persona dueña de la cuenta y que no posea ya una.
        """
        if int(persona.data) == 0:
            raise ValidationError('Debe selecionar a la persona dueña de la cuenta.')

        persona = User.query.filter(User.id_persona == persona.data).first()
        if persona:
            raise ValidationError('Esta persona ya tiene una cuenta.')


class LoginForm(FlaskForm):
    user = StringField('Usuario', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember = BooleanField('Recuérdame')
    submit = SubmitField('Ingresar')