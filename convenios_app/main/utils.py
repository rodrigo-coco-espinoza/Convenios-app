PALABRAS_MENORES = ['a', 'ante', 'bajo', 'cabe', 'con', 'contra', 'de', 'desde', 'durante', 'en', 'entre', 'hacia',
                    'hasta',
                    'mediante', 'para', 'por', 'es', 'según', 'sin', 'so', 'sobre', 'tras', 'versus', 'vía', 'el', 'la',
                    'los',
                    'las', 'un', 'uno', 'unos', 'una', 'unas', 'lo', 'al', 'del', 'y', 'e', 'ni', 'que', 'o', 'u',
                    'pero',
                    'aunque', 'mas', 'sino', 'porque', 'pues', 'como', 'más', 'tal', 'i', 'b', 'c', 'd', 'f', 'g', 'h',
                    'j',
                    'k', 'l', 'ñ', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z']
PALABRAS_MAYORES = ['ws', 'sii']
COLORES_ETAPAS = {
    'Definición de Alcance del Convenio': '#DFF6FF',
    'Confección de Documento de Convenio': '#5D8BF4',
    'Gestión de Visto Bueno y Firmas': '#2D31FA',
    'Generación de Resolución y Protocolo Técnico': '#051367'
}
COLORES_EQUIPOS = {
    'SDGEET': '#0057D5',
    'IE': '#F94300',
    'SDAC': '#FF0022',
    'SDAV': '#46237A',
    'SDF': '#0A7A10',
    'SDI': '#FFC100',
    'SDJ': '#9A4407',
    'GDIR': '#590925',
    'DGC': '#E683E2',
    'SDA': '#40531B',
    'SDACORP': '#3EDB00',
    'SDDP': '#1B2D2A',
    'SDN': '#41EAD4',
    'AIET': '#0057D5'
}

ID_EQUIPOS = {
'SDGEET': 6,
    'IE': 2,
    'SDAC': 3,
    'SDAV': 4,
    'SDF': 5,
    'SDI': 7,
    'SDJ': 8,
    'GDIR': 9,
    'DGC': 10,
    'SDA': 11,
    'SDACORP': 12,
    'SDDP': 13,
    'SDN': 14,
    'AIET': 1
}


def generar_nombre_institucion(institucion):
    """
    Genera el nombre de la institución con la sigla de la institución
    :param convenio: objeto de la clase Institucion/Ministerio
    :return: str(SIGLA Nombre)
    """
    return f'{institucion.nombre} - {institucion.sigla}'


def formato_nombre(nombre):
    """
    Devuelve el nombre del convenio con el formato especificado.
    :param nombre: str del formulario de convenios.
    :return: str con el nombre del convenio formateado.
    """
    nombre = nombre.strip()
    palabras_lista = nombre.split(" ")
    nombre_lista = []
    for i, palabra in enumerate(palabras_lista):

        # Si la palabra está en mayúsculas, se deja así
        if palabra.isupper():
            nombre_lista.append(palabra)
        # Si la palabra es mayor se deja en mayúsculas
        elif palabra.lower() in PALABRAS_MAYORES:
            nombre_lista.append(palabra.upper())
        else:
            # Capitalizar primera palabra
            if i == 0:
                nombre_lista.append(palabra.capitalize())
            else:
                # No capitalizar las preposiciones, conjuncions o artículos
                if palabra.lower() in PALABRAS_MENORES:
                    nombre_lista.append(palabra)
                else:
                    nombre_lista.append(palabra.capitalize())

    return ' '.join(nombre_lista)


def generar_nombre_convenio(convenio):
    """
    Genera el nombre del convenio con la sigla de la institución
    :param convenio: objeto de la clase Convenio
    :return: str(SIGLA Nombre)
    """
    if convenio.tipo == 'Convenio':
        return f'{convenio.institucion.sigla} {convenio.nombre}'
    else:
        return f'{convenio.institucion.sigla} (Ad) {convenio.nombre}'
