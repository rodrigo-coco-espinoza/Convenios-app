from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField, IntegerField, SelectMultipleField
from wtforms.validators import DataRequired, Length, ValidationError, Email
from convenios_app.models import Institucion, Convenio
from sqlalchemy import and_
from convenios_app.bitacoras.utils import formato_nombre, generar_nombre_convenio



class ConvenioForm(FlaskForm):
    id_convenio = HiddenField('id_convenio', default=0)
    nombre = StringField('Nombre del convenio', render_kw={'placeholder': 'Intercambio de información'},
                         validators=[DataRequired()])
    estado = SelectField('Estado', choices=['En proceso',
                                            'En producción',
                                            'Pausado',
                                            'Reemplazado',
                                            'Cancelado'])
    tipo = SelectField('Tipo de documento', choices=['Seleccionar',
                                                     'Convenio',
                                                     'Adendum'])
    convenio_padre = SelectField('Convenio al cual pertenece el adendum',
                                 choices=[(0, 'Seleccione una institución para ver los convenios')],
                                 validate_choice=False)
    convenio_reemplazo = SelectField('Convenio por el cual se reemplaza')
    gabinete_electronico = StringField('Número de Gabinete Electrónico')
    proyecto = StringField('Número de proyecto')
    institucion = SelectField('Institución con la que se firma el convenio')
    coord_sii = SelectField('Coordinador SII')
    sup_sii = SelectField('Suplente SII')
    coord_ie = SelectField('Coordinador institución externa', choices=[(0, 'Seleccionar')], validate_choice=False)
    sup_ie = SelectField('Suplente institución externa', choices=[(0, 'Seleccionar')], validate_choice=False)
    responsable_convenio_ie = SelectField('Responsable del convenio IE', choices=[(0, 'Seleccionar')],
                                          validate_choice=False)
    sd_involucradas= SelectMultipleField('Subdirecciones involucradas en el convenio', render_kw={"": 'multiple'},
                                         validate_choice=False)
    submit = SubmitField('Agregar')

    def validate_nombre(self, nombre):
        """
        Valida que no exista otro convenio con el mismo nombre con la institución
        """
        convenio = Convenio.query.filter(and_(Convenio.nombre == formato_nombre(nombre.data),
                                              Convenio.id_institucion == int(self.institucion.data),
                                              Convenio.id != int(self.id_convenio.data))).first()

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

    def validate_sd_involucradas(self, sd_involucradas):
        if len(sd_involucradas.data) == 0:
            raise ValidationError('Debe escoger al menos una subdirección involucrada.')

    def validate_proyecto(self, proyecto):
        if len(proyecto.data) > 0:
            try:
                int(proyecto.data)
            except:
                raise ValidationError('Debe ingresar solo números.')
        nro_proyecto = Convenio.query.filter(and_(Convenio.proyecto == proyecto.data, Convenio.id != int(self.id_convenio.data))).first()
        if nro_proyecto:
            raise ValidationError(f'El número de proyecto {proyecto.data} ya está registrado. Vuelva a seleccionar el convenio para editar')

    def validate_estado(self, estado):
        if estado.data == 'Reemplazado' and int(self.convenio_reemplazo.data) == 0:
            raise ValidationError('Debe seleccionar el convenio por el cual sera reemplazado. Vuelva a seleccionar el convenio para editar.')

    def validate_gabinete_electronico(self, gabinete_electronico):
        if len(gabinete_electronico.data) > 0:
            try:
                int(gabinete_electronico.data)
            except:
                raise ValidationError('Debe ingresar solo números.')

    def validate_institucion(self, institucion):
        if int(self.id_convenio.data) != 0:
            convenio = Convenio.query.get(self.id_convenio.data)
            if convenio.id_institucion != int(institucion.data):
                raise ValidationError(f'No está perminitdo cambiar la institución de {generar_nombre_convenio(convenio)}')








#resolucion = IntegerField('Número de resolución')
#link_resolucion = StringField('Link de la resolución')