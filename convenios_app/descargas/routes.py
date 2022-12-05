from flask import Blueprint, send_file, make_response
from numpy import dtype
from convenios_app.models import (BitacoraAnalista, BitacoraTarea, Convenio, TrayectoriaEquipo, TrayectoriaEtapa, RecepcionConvenio, WSConvenio,
                                SdInvolucrada, Equipo)
from convenios_app import db
from sqlalchemy import and_, or_
from convenios_app.bitacoras.utils import dias_habiles, obtener_iniciales
from convenios_app.informes.utils import obtener_etapa_actual_dias
from convenios_app.descargas.utils import (contar_adendum, contar_convenios, contar_otros,contar_por_firmar)
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
        'Días en proceso': pd.Series(dtype='int'),
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

        # Obtener días en proceso
        dias_en_proceso = 0
        for etapa in TrayectoriaEtapa.query.filter(TrayectoriaEtapa.id_convenio == convenio.id).order_by(
            TrayectoriaEtapa.ingreso.asc()).all():
            salida_etapa = (lambda salida: salida if salida != None else date.today())(etapa.salida)
            dias_en_proceso += dias_habiles(etapa.ingreso, salida_etapa)
        fila['Días en proceso'] = dias_en_proceso

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
    texto = f"Nota: Información extraída  del Sistema de Convenios el {datetime.today().strftime('%d-%m-%Y a las %H:%M')} - Área de Información Estadística y Tributaria, SDGEET."
    bold = workbook.add_format({'bold': True})
    worksheet.write(0, 0, texto, bold)
    # Formato de tabla
    worksheet.add_table(f'A3:N{len(convenios_df.index) + 3}', {'style': 'Table Style Medium 1',
                                    'autofilter': False,
                                    'columns': [{'header': '#'},
                                                {'header': 'Institución'},
                                                {'header': 'Convenio'},
                                                {'header': 'Días en proceso'},
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
    texto = f'Nota: Información extraída del Sistema de Convenios el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} - Área de Información Estadística y Tributaria, SDGEET.'
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
    texto = f'Nota: Información extraída del Sistema de Convenios el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} - Área de Información Estadística y Tributaria, SDGEET.'
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
    # Obtener convenios
    convenios_query = Convenio.query.all()
    # Calcular información de cada institución
    instituciones= {}
    for convenio in convenios_query:
        # Convenios en producción o en proceso
        if convenio.estado == 'En producción' or convenio.estado == 'En proceso':
            # Convenios firmados
            if convenio.fecha_documento != None:
                try:
                    instituciones[convenio.institucion.sigla][convenio.tipo] += 1
                except KeyError:
                    try: 
                        instituciones[convenio.institucion.sigla][convenio.tipo] = 1
                    except:
                        instituciones[convenio.institucion.sigla] = {'id_institucion': convenio.id_institucion}
                        instituciones[convenio.institucion.sigla][convenio.tipo] = 1
            # Convenios por firmar
            else:
                try:
                    instituciones[convenio.institucion.sigla]["por_firmar"] += 1
                except KeyError:
                    try:
                        instituciones[convenio.institucion.sigla]["por_firmar"] = 1
                    except KeyError:
                        instituciones[convenio.institucion.sigla] = {'id_institucion': convenio.id_institucion}
                        instituciones[convenio.institucion.sigla]["por_firmar"] = 1                     
        # Otros convenios
        else:
            try:
                instituciones[convenio.institucion.sigla]['otros'] += 1
            except KeyError:
                try: 
                    instituciones[convenio.institucion.sigla]['otros'] = 1
                except KeyError:
                    instituciones[convenio.institucion.sigla] = {'id_institucion': convenio.id_institucion}
                    instituciones[convenio.institucion.sigla]['otros'] = 1
    
        # Agregar recepciones
        recepciones = RecepcionConvenio.query.filter(and_(RecepcionConvenio.id_convenio == convenio.id, RecepcionConvenio.estado == 1)).count()
        try:
            instituciones[convenio.institucion.sigla]['recepciones'] += recepciones
        except KeyError:
            instituciones[convenio.institucion.sigla]['recepciones'] = recepciones
        # Agregar WS
        ws = WSConvenio.query.filter(and_(WSConvenio.id_convenio == convenio.id, WSConvenio.estado == 1)).count()
        try:
            instituciones[convenio.institucion.sigla]['ws'] += ws
        except KeyError:
            instituciones[convenio.institucion.sigla]['ws'] = ws
        # Agregar entregas
        # PENDIENTE
        # Agrega nombre del convenio
        if '-' in convenio.institucion.sigla:
            instituciones[convenio.institucion.sigla]['nombre'] = convenio.institucion.nombre
        else:
            instituciones[convenio.institucion.sigla]['nombre'] = convenio.institucion.nombre

    # Generar tabla para dataframe
    tabla = []
    for institucion, data in instituciones.items():
        tabla.append([
            data['nombre'],
            institucion,
            contar_convenios(data),
            contar_adendum(data),
            contar_por_firmar(data),
            contar_otros(data),
            data['recepciones'] if data['recepciones'] else 0,
            data['ws'] if data['ws'] else 0
        ])

    # Crear dataframe 
    instituciones_df = pd.DataFrame(tabla, columns=['Institución',
                                                    'Sigla',
                                                    'Convenios',
                                                    'Addendum',
                                                    'Por firmar',
                                                    'Otros',
                                                    'Recepciones',
                                                    'WebServices'])


    # Ordenar tabla
    instituciones_df.sort_values(by='Institución', ignore_index=True, inplace=True)
    # Índice desde 1
    instituciones_df.index += 1
    # Convertir a Excel
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    instituciones_df.reset_index().to_excel(excel_writer=writer, sheet_name='Convenios por institución', startrow=2, index=False)
    #Escribir texto en la primera fila
    workbook = writer.book
    worksheet = writer.sheets['Convenios por institución']
    texto = f'Nota: Información extraída del Sistema de Convenios el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} - Área de Información Estadística y Tributaria, SDGEET.'
    bold = workbook.add_format({'bold': True})
    worksheet.write(0, 0, texto, bold)
    # Formato de tabla
    worksheet.add_table(f'A3:I{len(instituciones_df.index) + 3}',
                        {'style': 'Table Style Medium 1',
                        'autofilter': False,
                        'columns': [{'header': '#'},
                                    {'header': 'Institución'},
                                    {'header': 'Sigla'},
                                    {'header': 'Convenios'},
                                    {'header': 'Addendum'},
                                    {'header': 'Por firmar'},
                                    {'header': 'Otros'},
                                    {'header': 'Recepciones'},
                                    {'header': 'WebServices'},
                                    ]})
    # Guardar
    writer.save()
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=convenios_por_institucion_{date.today()}.xlsx"
    response.headers["Content-type"] = "application/x-xls"

    return response

@descargas.route('/descargar_bitacora_proceso')
def descargar_bitacora_proceso():
    # Obtener convneios en proceso
    convenios_query = Convenio.query.filter(Convenio.estado == 'En proceso').all()
    # Crear data frame con la tabla a descargar
    convenios_df = pd.DataFrame({
        'Institución': pd.Series(dtype='str'),
        'Convenio': pd.Series(dtype='str'),
        'Última observación': pd.Series(dtype='str'),
        'Fecha observación': pd.Series(dtype='datetime64[ns]'),
        'Próxima tarea': pd.Series(dtype='str'),
        'Plazo': pd.Series(dtype='datetime64[ns]'),
        'Coord': pd.Series(dtype='str'),
         'Sup': pd.Series(dtype='str')
         })
    # Recorrer convenios en proceso
    for convenio in convenios_query:
        # Crear diccionario con fila a insertar
        fila = {
            'Institución': convenio.institucion.sigla,
            'Convenio': (lambda tipo: convenio.nombre if tipo == 'Convenio' else f'(Ad) {convenio.nombre}')(convenio.tipo),
            'Coord': obtener_iniciales(convenio.coord_sii.nombre),
            'Sup': obtener_iniciales(convenio.sup_sii.nombre)
        }
        # Obtener última observación
        observacion_query = BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == convenio.id,
                                                                BitacoraAnalista.estado != 'Eliminado')).order_by(
                                                                    BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).first()
        fila['Última observación'] = observacion_query.observacion
        fila['Fecha observación'] = observacion_query.fecha                                                                
        # Obtener próxima tarea
        tarea_query = BitacoraTarea.query.filter(
            and_(BitacoraTarea.id_convenio == convenio.id, BitacoraTarea.estado == 'Pendiente')).order_by(
                BitacoraTarea.plazo.asc(), BitacoraTarea.timestamp.asc()).first()
        fila['Próxima tarea'] = tarea_query.tarea if tarea_query != None else None
        fila['Plazo'] = tarea_query.plazo if  tarea_query != None else None
        # Agregar fila
        convenios_df = pd.concat([convenios_df, pd.DataFrame([fila])], ignore_index=True)
    
    # Ordenar tabla
    convenios_df.sort_values(by='Institución', ignore_index=True, inplace=True)
    # Índice desde 1
    convenios_df.index += 1
    # Convertir a Excel
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    convenios_df.reset_index().to_excel(excel_writer=writer, sheet_name='Convenios en proceso', startrow=2, index=False)
    #Escribir texto en la primera fila
    workbook = writer.book
    worksheet = writer.sheets['Convenios en proceso']
    texto = f'Nota: Información extraída del Sistema de Convenios el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} - Área de Información Estadística y Tributaria, SDGEET.'
    bold = workbook.add_format({'bold': True})
    worksheet.write(0, 0, texto, bold)
    # Formato de tabla
    worksheet.add_table(f'A3:I{len(convenios_df.index) + 3}',
                        {'style': 'Table Style Medium 1',
                        'autofilter': False,
                        'columns': [{'header': '#'},
                                    {'header': 'Institución'},
                                    {'header': 'Convenio'},
                                    {'header': 'Última observación'},
                                    {'header': 'Fecha observación'},
                                    {'header': 'Próxima tarea'},
                                    {'header': 'Plazo'},
                                    {'header': 'Coord'},
                                    {'header': 'Sup'},
                                    ]})

    # Guardar
    writer.save()
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=bitacora_convenios_en_proceso_{date.today()}.xlsx"
    response.headers["Content-type"] = "application/x-xls"

    return response

@descargas.route('/descargar_bitacora_produccion')
def descargar_bitacora_produccion():
    # Obtener convenios en producción
    convenios_query = Convenio.query.filter(Convenio.estado == 'En producción').all()
    # Crear data frame con la tabla a descargar
    convenios_df = pd.DataFrame({
        'Institución': pd.Series(dtype='str'),
        'Convenio': pd.Series(dtype='str'),
        'Coord': pd.Series(dtype='str'),
        'Sup': pd.Series(dtype='str')
    })
    # Recorrer otros convenios
    for convenio in convenios_query:
        # Crear diccionario con fila a insertar
        fila = {
            'Institución': convenio.institucion.sigla,
            'Convenio': (lambda tipo: convenio.nombre if tipo == 'Convenio' else f'(Ad) {convenio.nombre}')(convenio.tipo),
            'Coord': obtener_iniciales(convenio.coord_sii.nombre),
            'Sup': obtener_iniciales(convenio.sup_sii.nombre) if convenio.sup_sii else None
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
    #Escribir texto en la primera fila
    workbook = writer.book
    worksheet = writer.sheets['Convenios en producción']
    texto = f'Nota: Información extraída del Sistema de Convenios el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} - Área de Información Estadística y Tributaria, SDGEET.'
    bold = workbook.add_format({'bold': True})
    worksheet.write(0, 0, texto, bold)
    # Formato de tabla
    worksheet.add_table(f'A3:E{len(convenios_df.index) + 3}',
                        {'style': 'Table Style Medium 1',
                        'autofilter': False,
                        'columns': [{'header': '#'},
                                    {'header': 'Institución'},
                                    {'header': 'Convenio'},
                                    {'header': 'Coord'},
                                    {'header': 'Sup'}
                                    ]})
    # Guardar
    writer.save()
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=bitacora_convenios_en_produccion_{date.today()}.xlsx"
    response.headers["Content-type"] = "application/x-xls"

    return response

@descargas.route('/descargar_bitacora_otros')
def descargar_bitacora_otros():
    # Obtener otros convenios
    convenios_query = Convenio.query.filter(and_(
        Convenio.estado != 'En proceso', Convenio.estado != 'En producción')).all()
    # Crear data frame con la tabla a descargar
    convenios_df = pd.DataFrame({
        'Institución': pd.Series(dtype='str'),
        'Convenio': pd.Series(dtype='str'),
        'Estado': pd.Series(dtype='str'),
        'Coord': pd.Series(dtype='str'),
        'Sup': pd.Series(dtype='str')
    })
    # Recorrer otros convenios
    for convenio in convenios_query:
        # Crear diccionario con fila a insertar
        fila = {
            'Institución': convenio.institucion.sigla,
            'Convenio': (lambda tipo: convenio.nombre if tipo == 'Convenio' else f'(Ad) {convenio.nombre}')(convenio.tipo),
            'Estado': convenio.estado,
            'Coord': obtener_iniciales(convenio.coord_sii.nombre),
            'Sup': obtener_iniciales(convenio.sup_sii.nombre) if convenio.sup_sii else None
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
    texto = f'Nota: Información extraída del Sistema de Convenios el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} - Área de Información Estadística y Tributaria, SDGEET.'
    bold = workbook.add_format({'bold': True})
    worksheet.write(0, 0, texto, bold)
    # Formato de tabla
    worksheet.add_table(f'A3:F{len(convenios_df.index) + 3}',
                        {'style': 'Table Style Medium 1',
                        'autofilter': False,
                        'columns': [{'header': '#'},
                                    {'header': 'Institución'},
                                    {'header': 'Convenio'},
                                    {'header': 'Estado'},
                                    {'header': 'Coord'},
                                    {'header': 'Sup'}
                                    ]})
    # Guardar
    writer.save()
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=bitacora_otros_convenios_{date.today()}.xlsx"
    response.headers["Content-type"] = "application/x-xls"

    return response

@descargas.route('/descargar_sd_actual/<int:equipo>')
def descargar_sd_actual(equipo):
    # Obtener equipo
    equipo_query = Equipo.query.get(equipo)
    # Obtener convenios del equipo para generar datos
    lista_convenios_asociados = [convenio.id_convenio for convenio in
        SdInvolucrada.query.filter(SdInvolucrada.id_subdireccion == equipo).all()]
    convenios_query = Convenio.query.filter(Convenio.id.in_(lista_convenios_asociados)).all()
    # Crear data frame con la tabla a descargar
    convenios_df = pd.DataFrame({
        'Institución': pd.Series(dtype='str'),
        'Convenio': pd.Series(dtype='str'),
        'Estado': pd.Series(dtype='str'),
        'Última observación': pd.Series(dtype='str'),
        'Fecha observación': pd.Series(dtype='datetime64[ns]'),
        'Coord': pd.Series(dtype='str'),
        'Sup': pd.Series(dtype='str')
         })
    # Recorrer convenios en proceso
    for convenio in convenios_query:
        # Crear diccionario con fila a insertar
        fila = {
            'Institución': convenio.institucion.sigla,
            'Convenio': (lambda tipo: convenio.nombre if tipo == 'Convenio' else f'(Ad) {convenio.nombre}')(convenio.tipo),
            'Estado': convenio.estado,
            'Coord': obtener_iniciales(convenio.coord_sii.nombre),
            'Sup': obtener_iniciales(convenio.sup_sii.nombre) if convenio.sup_sii else None
        }
        # Obtener última observación
        observacion_query = BitacoraAnalista.query.filter(and_(BitacoraAnalista.id_convenio == convenio.id,
                                                                BitacoraAnalista.estado != 'Eliminado')).order_by(
                                                                    BitacoraAnalista.fecha.desc(), BitacoraAnalista.timestamp.desc()).first()
        fila['Última observación'] = observacion_query.observacion
        fila['Fecha observación'] = observacion_query.fecha                                                                
        # Agregar fila
        convenios_df = pd.concat([convenios_df, pd.DataFrame([fila])], ignore_index=True)

    # Ordenar tabla
    convenios_df.sort_values(by='Estado', ignore_index=True, inplace=True)
    # Índice desde 1
    convenios_df.index += 1
    # Convertir a Excel
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    convenios_df.reset_index().to_excel(excel_writer=writer, sheet_name='Estado actual convenios', startrow=2, index=False)
    #Escribir texto en la primera fila
    workbook = writer.book
    worksheet = writer.sheets['Estado actual convenios']
    texto = f'Nota: Información extraída del Sistema de Convenios el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} - Área de Información Estadística y Tributaria, SDGEET.'
    bold = workbook.add_format({'bold': True})
    worksheet.write(0, 0, texto, bold)
    # Formato de tabla
    worksheet.add_table(f'A3:H{len(convenios_df.index) + 3}',
                        {'style': 'Table Style Medium 1',
                        'autofilter': False,
                        'columns': [{'header': '#'},
                                    {'header': 'Institución'},
                                    {'header': 'Convenio'},
                                    {'header': 'Estado'},
                                    {'header': 'Última observación'},
                                    {'header': 'Fecha observación'},
                                    {'header': 'Coord'},
                                    {'header': 'Sup'},
                                    ]})

    # Guardar
    writer.save()
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=estado_actual_convenios_{equipo_query.sigla}_{date.today()}.xlsx"
    response.headers["Content-type"] = "application/x-xls"

    return response

@descargas.route('/descargar_sd_asignados/<int:equipo>')
def descargar_sd_asignados(equipo):
    # Obtener equipo
    equipo_query = Equipo.query.get(equipo)
    # Obtener convenios asignados a la SD
    lista_convenios_asignados = [trayecto.id_convenio for trayecto in
        TrayectoriaEquipo.query.filter(and_(TrayectoriaEquipo.id_equipo == equipo,
                                            TrayectoriaEquipo.salida == None)).all()]
    convenios_query = Convenio.query.filter(Convenio.id.in_(lista_convenios_asignados))
    # Crear data frame con la tabla a descargar
    convenios_df = pd.DataFrame({
        'Institución': pd.Series(dtype='str'),
        'Convenio': pd.Series(dtype='str'),
        'Días en área': pd.Series(dtype='int'),
        'Etapa actual': pd.Series(dtype='str'),
        'Días en etapa': pd.Series(dtype='int')
         })
    # Recorrer convenios en proceso
    for convenio in convenios_query:
        # Crear diccionario con fila a insertar
        etapa_actual = TrayectoriaEtapa.query.filter(and_(TrayectoriaEtapa.id_convenio == convenio.id,
                                               TrayectoriaEtapa.salida == None)).first()
        fila = {
            'Institución': convenio.institucion.sigla,
            'Convenio': (lambda tipo: convenio.nombre if tipo == 'Convenio' else f'(Ad) {convenio.nombre}')(convenio.tipo),
            'Días en área': dias_habiles(TrayectoriaEquipo.query.filter(and_(TrayectoriaEquipo.id_convenio == convenio.id,
                                                  TrayectoriaEquipo.salida == None, TrayectoriaEquipo.id_equipo == equipo)).first().ingreso,
                                   date.today()),
            'Etapa actual': etapa_actual.etapa.etapa,
            'Días en etapa': dias_habiles(etapa_actual.ingreso, date.today())
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
    convenios_df.reset_index().to_excel(excel_writer=writer, sheet_name='Convenios asignados', startrow=2, index=False)
    #Escribir texto en la primera fila
    workbook = writer.book
    worksheet = writer.sheets['Convenios asignados']
    texto = f'Nota: Información extraída del Sistema de Convenios el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} - Área de Información Estadística y Tributaria, SDGEET.'
    bold = workbook.add_format({'bold': True})
    worksheet.write(0, 0, texto, bold)
    # Formato de tabla
    worksheet.add_table(f'A3:F{len(convenios_df.index) + 3}',
                        {'style': 'Table Style Medium 1',
                        'autofilter': False,
                        'columns': [{'header': '#'},
                                    {'header': 'Institución'},
                                    {'header': 'Convenio'},
                                    {'header': 'Días en área'},
                                    {'header': 'Etapa actual'},
                                    {'header': 'Días en etapa'}
                                    ]})

    # Guardar
    writer.save()
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=convenios_asignados_{equipo_query.sigla}_{date.today()}.xlsx"
    response.headers["Content-type"] = "application/x-xls"

    return response

@descargas.route('/descargar_sd_recepcion/<int:equipo>')
def descargar_sd_recepcion(equipo):
    # Obtene equipo
    equipo_query = Equipo.query.get(equipo)
    # Obtener recepción de información de la SD
    recepciones_query = RecepcionConvenio.query.filter(and_(RecepcionConvenio.id_sd == equipo, RecepcionConvenio.estado == True)).all()
    recepciones = {key: [] for key in ['En línea', 'Diario', 'Semanal', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']}
    for recepcion in recepciones_query:
        # Verificar si la recepción es en múltiples meses
        periodicidad = recepcion.periodicidad.split('-') if '-' in recepcion.periodicidad else [recepcion.periodicidad]
        # Agregar recepciones según la periocididad que corresponda
        if "En línea" in periodicidad:
            recepciones['En línea'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if "Diario" in periodicidad:
            recepciones['Diario'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if "Semanal" in periodicidad:
            recepciones['Semanal'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if  any(item in ["Mensual", "1"] for item in periodicidad):
            recepciones['Enero'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "2"] for item in periodicidad):
            recepciones['Febrero'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "3"] for item in periodicidad):
            recepciones['Marzo'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "4"] for item in periodicidad):
            recepciones['Abril'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "5"] for item in periodicidad):
            recepciones['Mayo'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "6"] for item in periodicidad):
            recepciones['Junio'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "7"] for item in periodicidad):
            recepciones['Julio'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "8"] for item in periodicidad):
            recepciones['Agosto'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "9"] for item in periodicidad):
            recepciones['Septiembre'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "10"] for item in periodicidad):
            recepciones['Octubre'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "11"] for item in periodicidad):
            recepciones['Noviembre'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
        if any(item in ["Mensual", "12"] for item in periodicidad):
            recepciones['Diciembre'].append({
                'institucion': recepcion.convenio.institucion.sigla,
                'nombre': recepcion.nombre,
                'archivo': recepcion.archivo,
                'metodo': recepcion.metodo
            })
    # Crear archivo excel para añadir hojas
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    # Crear hoja de cálculo por cada periodo de recepción 
    for periodo, datos in recepciones.items():
        if datos:
            # Crear dataframe
            recepciones_periodo_df = pd.DataFrame({
                                        'Institución': pd.Series(dtype='str'),
                                        'Nombre entrega': pd.Series(dtype='str'),
                                        'Nombre archivo': pd.Series(dtype='str'),
                                        'Método': pd.Series(dtype='str')
                                        })
            # Recorrer periodo y agregar al df
            for recepcion in datos:
                fila = {'Institución': recepcion['institucion'],
                        'Nombre entrega': recepcion['nombre'],
                        'Nombre archivo': recepcion['archivo'],
                        'Método': recepcion['metodo']
                        }
                # Agregar fila
                recepciones_periodo_df = pd.concat([recepciones_periodo_df, pd.DataFrame([fila])], ignore_index=True)          
            
            # Ordenar tabla
            recepciones_periodo_df.sort_values(by='Institución', ignore_index=True, inplace=True)
            # Índice desde 1
            recepciones_periodo_df.index += 1
            # Crear hoja con las recepciones del periodo
            recepciones_periodo_df.reset_index().to_excel(excel_writer=writer, sheet_name=f'{periodo}', startrow=2, index=False)
            #Escribir texto en la primera fila
            worksheet = writer.sheets[f'{periodo}']
            texto = f'Nota: Información extraída del Sistema de Convenios el {datetime.today().strftime("%d-%m-%Y a las %H:%M")} - Área de Información Estadística y Tributaria, SDGEET.'
            bold = workbook.add_format({'bold': True})
            worksheet.write(0, 0, texto, bold)
            # Formato de tabla
            worksheet.add_table(f'A3:E{len(recepciones_periodo_df.index) + 3}',
                                {'style': 'Table Style Medium 1',
                                'autofilter': False,
                                'columns': [{'header': '#'},
                                            {'header': 'Institución'},
                                            {'header': 'Nombre entrega'},
                                            {'header': 'Nombre archivo'},
                                            {'header': 'Método'}
                                            ]})  

    # Guardar
    writer.save()
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=recepciones_{equipo_query.sigla}_{date.today()}.xlsx"
    response.headers["Content-type"] = "application/x-xls"

    return response                    
