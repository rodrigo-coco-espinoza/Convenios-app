from flask import Blueprint, send_file, make_response
from convenios_app.models import (Convenio, TrayectoriaEquipo, TrayectoriaEtapa)
from convenios_app import db
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import dias_habiles
from convenios_app.main.utils import generar_nombre_institucion, generar_nombre_convenio, formato_nombre
from datetime import datetime, date
import pandas as pd
from io import BytesIO


descargas = Blueprint('descargas', __name__)

@descargas.route('/descargar_informes_proceso')
def descargar_informes_proceso():
    # Obtener convenios en proceso
    convenios_query = Convenio.query.filter(Convenio.estado == 'En proceso').all()
    
    # Crear data frame con la tabla a descargar
    convenios_df = pd.DataFrame({
        'Institución': pd.Series(dtype='str'),
        'Convenio': pd.Series(dtype='str'),
        'Etapa actual': pd.Series(dtype='str'),
        'Días en etapa': pd.Series(dtype='int'),
        'Área 1': pd.Series(dtype='str'),
        'Días A1': pd.Series(dtype='int'),
        'Área 2': pd.Series(dtype='str'),
        'Días A2': pd.Series(dtype='int'),
        'Área 3': pd.Series(dtype='str'),
        'Días A3': pd.Series(dtype='int'),
        'Área 4': pd.Series(dtype='str'),
        'Días A4': pd.Series(dtype='int')
    })
    
    # Recorrer convenios en proceso
    for convenio in convenios_query:
        # Crear diccionario con fila a insertar
        fila = {
            'Institución': convenio.institucion.sigla,
            'Convenio': (lambda tipo: convenio.nombre if tipo == 'Convenio' else f'(Ad) {convenio.nombre}')(convenio.tipo)
        }
        # Obtener etapa actual
        etapa_query = TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == convenio.id,
                                                        TrayectoriaEtapa.salida == None)).first()
        fila['Etapa actual'] = etapa_query.etapa.etapa
        fila['Días en etapa'] = dias_habiles(etapa_query.ingreso, date.today())                                             

        # Obtener áreas
        equipos_query = TrayectoriaEquipo.query.filter(and_(TrayectoriaEquipo.id_convenio == convenio.id,
                                                            TrayectoriaEquipo.salida == None)).all()
        if len(equipos_query) == 1:
            fila['Área 1'] = equipos_query[0].equipo.sigla
            fila['Días A1'] = dias_habiles(equipos_query[0].ingreso, date.today())
        elif len(equipos_query) == 2:
            fila['Área 1'] = equipos_query[0].equipo.sigla
            fila['Días A1'] = dias_habiles(equipos_query[0].ingreso, date.today())
            fila['Área 2'] = equipos_query[1].equipo.sigla
            fila['Días A2'] = dias_habiles(equipos_query[1].ingreso, date.today())
        elif len(equipos_query) == 3:
            fila['Área 1'] = equipos_query[0].equipo.sigla
            fila['Días A1'] = dias_habiles(equipos_query[0].ingreso, date.today())
            fila['Área 2'] = equipos_query[1].equipo.sigla
            fila['Días A2'] = dias_habiles(equipos_query[1].ingreso, date.today())
            fila['Área 3'] = equipos_query[2].equipo.sigla
            fila['Días A3'] = dias_habiles(equipos_query[2].ingreso, date.today())
        elif len(equipos_query) == 4:
            fila['Área 1'] = equipos_query[0].equipo.sigla
            fila['Días A1'] = dias_habiles(equipos_query[0].ingreso, date.today())
            fila['Área 2'] = equipos_query[1].equipo.sigla
            fila['Días A2'] = dias_habiles(equipos_query[1].ingreso, date.today())
            fila['Área 3'] = equipos_query[2].equipo.sigla
            fila['Días A3'] = dias_habiles(equipos_query[2].ingreso, date.today())
            fila['Área 4'] = equipos_query[3].equipo.sigla
            fila['Días A4'] = dias_habiles(equipos_query[3].ingreso, date.today())
 
        # Agregar fila
        convenios_df = pd.concat([convenios_df, pd.DataFrame([fila])], ignore_index=True)
    # Convertir números a int
    convenios_df = convenios_df.convert_dtypes()
    # Ordenar tabla
    convenios_df.sort_values(by='Institución', ignore_index=True, inplace=True)
    # Índice desde 1
    convenios_df.index += 1
    # Convertir a Excel
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    convenios_df.reset_index().to_excel(excel_writer=writer, sheet_name='Convenios en proceso', startrow=2, index=False)
    # Escribir texto en la primera fila
    workbook = writer.book
    worksheet = writer.sheets['Convenios en proceso']
    texto = f"Nota: Información extraída el {datetime.today().strftime('%d-%m-%Y a las %H:%M')} del Sistema de Convenios - Área de Información Estadística y Tributaria, SDGEET."
    bold = workbook.add_format({'bold': True})
    worksheet.write(0, 0, texto, bold)
    # Formato de tabla
    worksheet.add_table(f'A3:M{len(convenios_df.index) + 3}', {'style': 'Table Style Medium 1',
                                    'autofilter': False,
                                    'columns': [{'header': '#'},
                                                {'header': 'Institución'},
                                                {'header': 'Convenio'},
                                                {'header': 'Etapa actual'},
                                                {'header': 'Días en etapa'},
                                                {'header': 'Área 1'},
                                                {'header': 'Días A1'},
                                                {'header': 'Área 2'},
                                                {'header': 'Días A2'},
                                                {'header': 'Área 3'},
                                                {'header': 'Días A3'},
                                                {'header': 'Área 4'},
                                                {'header': 'Días A4'}
                                                ]})

    # Guardar
    writer.save()
    # Enviar archivo para descarga
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=convenios_en_proceso_{date.today()}.xlsx"
    response.headers["Content-type"] = "application/x-xls"

    return response

@descargas.route('/descagar_informes_produccion')
def descargar_informes_produccion():
    # Obtener convenios en producción
    convenios_query = Convenio.query.filter(Convenio.estado == 'En producción').all()

    # Crear data frame con la tabla a descargar
    convenios_df = pd.DataFrame({
        'Institución': pd.Series(dtype='str'),
        'Convenio': pd.Series(dtype='str'),
        'Fecha firma': pd.Series(dtype='datetime64[ns]'),
        'Nro Resolución': pd.Series(dtype='int'),
        'Fecha Resolución': pd.Series(dtype='datetime64[ns]')
    })

    # Recorrer convenios en producción
    for convenio in convenios_query:
        # Crear diccionario con fila a insertar
        fila = {
            'Institución': convenio.institucion.sigla,
            'Convenio': (lambda tipo: convenio.nombre if tipo == 'Convenio' else f'(Ad) {convenio.nombre}')(convenio.tipo),
            'Fecha firma': convenio.fecha_documento,
            'Nro Resolución': convenio.nro_resolucion,
            'Fecha Resolución': convenio.fecha_resolucion
        }
        # Agregar fila
        convenios_df = pd.concat([convenios_df, pd.DataFrame([fila])], ignore_index=True)
    
    # Ordenar tabla
    convenios_df.sort_values(by='Institución', ignore_index=True, inplace=True)
    # Índice desde 1
    convenios_df.index += 1
    # Convertir a Excel
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    convenios_df.reset_index().to_excel(excel_writer=writer, sheet_name='Convenios en producción', startrow=2, index=False)
    # Escribir texto en la primera fila
    workbook = writer.book
    worksheet = writer.sheets['Convenios en producción']
    texto = f'Nota: Información extraída el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} del Sistema de Convenios - Área de Información Estadística y Tributaria, SDGEET.'
    bold = workbook.add_format({'bold': True})
    worksheet.write(0, 0, texto, bold)
    # Formato de tabla
    worksheet.add_table(f'A3:F{len(convenios_df.index) + 3}',
                        {'style': 'Table Style Medium 1',
                        'autofilter': False,
                        'columns': [{'header': '#'},
                                    {'header': 'Institución'},
                                    {'header': 'Convenio'},
                                    {'header': 'Fecha firma'},
                                    {'header': 'Nro Resolución'},
                                    {'header': 'Fecha Resolución'}
                                    ]})
    # Guardar
    writer.save()
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=convenios_en_produccion_{date.today()}.xlsx"
    response.headers["Content-type"] = "application/x-xls"

    return response

@descargas.route('/descargar_informes_otros')
def descargar_informes_otros():
    # Obtener otros convenios
    convenios_query = Convenio.query.filter(and_(Convenio.estado != 'En proceso', Convenio.estado != 'En producción')).all()
    # Crear data frame con la tabla a descargar
    convenios_df = pd.DataFrame({
        'Institución': pd.Series(dtype='str'),
        'Convenio': pd.Series(dtype='str'),
        'Estado': pd.Series(dtype='str')
    })
    # Recorrer otros convenios
    for convenio in convenios_query:
        # Crear diccionario con fila a insertar
        fila = {
            'Institución': convenio.institucion.sigla,
            'Convenio': (lambda tipo: convenio.nombre if tipo == 'Convenio' else f'(Ad) {convenio.nombre}')(convenio.tipo),
            'Estado': convenio.estado
        }
        # Agregar fila
        convenios_df = pd.concat([convenios_df, pd.DataFrame([fila])], ignore_index=True)
    
    # Ordenar tabla
    convenios_df.sort_values(by='Institución', ignore_index=True, inplace=True)
    # Índice desde 1
    convenios_df.index += 1
    # Convertir a Excel
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    convenios_df.reset_index().to_excel(excel_writer=writer, sheet_name='Otros convenios', startrow=2, index=False)
    #Escribir texto en la primera fila
    workbook = writer.book
    worksheet = writer.sheets['Otros convenios']
    texto = f'Nota: Información extraída el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} del Sistema de Convenios - Área de Información Estadística y Tributaria, SDGEET.'
    bold = workbook.add_format({'bold': True})
    worksheet.write(0, 0, texto, bold)
    # Formato de tabla
    worksheet.add_table(f'A3:D{len(convenios_df.index) + 3}',
                        {'style': 'Table Style Medium 1',
                        'autofilter': False,
                        'columns': [{'header': '#'},
                                    {'header': 'Institución'},
                                    {'header': 'Convenio'},
                                    {'header': 'Estado'}
                                    ]})
    # Guardar
    writer.save()
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=otros_convenios_{date.today()}.xlsx"
    response.headers["Content-type"] = "application/x-xls"

    return response

@descargas.route('/descargar_informes_institucion')
def descargar_informes_institucion():
    pass
