def generar_nombre_institucion(institucion):
    """
    Genera el nombre de la institución con la sigla de la institución
    :param convenio: objeto de la clase Institucion/Ministerio
    :return: str(SIGLA Nombre)
    """
    return f'{institucion.nombre} - {institucion.sigla}'
