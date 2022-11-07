def contar_adendum(data):
    try:
        return data['Adendum']
    except KeyError:
        return 0


def contar_convenios(data):
    try:
        return data['Convenio']
    except KeyError:
        return 0


def contar_por_firmar(data):
    try:
        return data['por_firmar']
    except KeyError:
        return 0


def contar_otros(data):
    try:
        return data['otros']
    except KeyError:
        return 0