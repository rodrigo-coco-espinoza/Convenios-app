from flask_wtf import FlaskForm
from wtforms import StringField, FileField, SelectField, SubmitField, HiddenField, IntegerField, SelectMultipleField, validators
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Length, ValidationError, Email
from convenios_app.models import Institucion, Convenio, TrayectoriaEtapa, TrayectoriaEquipo
from sqlalchemy import and_
from convenios_app.main.utils import formato_nombre, generar_nombre_convenio
from wtforms.widgets import TextArea
from wtforms.widgets import DateInput
from datetime import date, datetime
from convenios_app.bitacoras.forms import ETAPAS, EQUIPOS


class ValidadorForm(FlaskForm):
    separador = StringField("Separador", render_kw={"placeholder": 'Ingrese separador del archivo'}, validators=[DataRequired(message="Debe ingresar el tipo de validador.")])
    archivo = FileField("Seleccione archivo", validators=[DataRequired(message="Debe seleccionar un archivo para analizar.")])
    submit = SubmitField("Validar")