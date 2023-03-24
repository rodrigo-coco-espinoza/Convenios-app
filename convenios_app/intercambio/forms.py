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

