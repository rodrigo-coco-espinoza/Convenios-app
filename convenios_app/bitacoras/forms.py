from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField, IntegerField, SelectMultipleField
from wtforms.validators import DataRequired, Length, ValidationError, Email
from convenios_app.models import Institucion


class ConvenioForm(FlaskForm):
    id_convenio = HiddenField('id_convenio', default=0)
    nombre = StringField('Nombre del convenio', render_kw={'placeholder': 'Intercambio de información'}, validators=[DataRequired()])
    estado = SelectField('Estado', choices=['En proceso',
                                            'En producción',
                                            'Pausado',
                                            'Reemplazado',
                                            'Cancelado'])
    tipo = SelectField('Tipo de documento', choices=['Seleccionar',
                                                     'Convenio',
                                                     'Adendum'])
    convenio_padre = SelectField('Convenio al cual pertenece el adendum')
    convenio_reemplazo = SelectField('Convenio por el cual se reemplaza')
    gabinete_electronico = StringField('Número de Gabinete Electrónico')
    proyecto = StringField('Número de proyecto')
    institucion = SelectField('Institución con la que se firma el convenio')
    coord_sii = SelectField('Coordinador SII')
    sup_sii = SelectField('Suplente SII')
    coord_ie = SelectField('Coordinador institución externa', choices=[(0, 'Seleccionar')], validate_choice=False)
    sup_ie = SelectField('Suplente institución externa', choices=[(0, 'Seleccionar')], validate_choice=False)
    responsable_convenio_ie = SelectField('Responsable del convenio institución externa', choices=[(0, 'Seleccionar')], validate_choice=False)
    sd_involucradas= SelectMultipleField('Subdirecciones involucradas en el convenio', render_kw={"": 'multiple'}, validate_choice=False)
    submit = SubmitField('Agregar')

    def validate_proyecto(self, proyecto):
        if len(proyecto.data) > 0:
            try:
                int(proyecto.data)
            except:
                raise ValidationError('Debe ingresar solo números.')

    def validate_gabinete_electronico(self, gabinete_electronico):
        if len(gabinete_electronico.data) > 0:
            try:
                int(gabinete_electronico.data)
            except:
                raise ValidationError('Debe ingresar solo números.')


    # def validate_coord_ie(self, coord_ie):
    #     if int(coord_ie.data) == 0:
    #         print('escogio 0')




#resolucion = IntegerField('Número de resolución')
#link_resolucion = StringField('Link de la resolución')