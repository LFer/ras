# -*- coding: utf-8 -*-
#############################################################################
#
# Copyright (c) 2016 G-Dev Team (Fork)
# Copyright (c) 2008, AxiaCore
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#############################################################################

UNIDADES = (
    '',
    'UN ',
    'DOS ',
    'TRES ',
    'CUATRO ',
    'CINCO ',
    'SEIS ',
    'SIETE ',
    'OCHO ',
    'NUEVE ',
    'DIEZ ',
    'ONCE ',
    'DOCE ',
    'TRECE ',
    'CATORCE ',
    'QUINCE ',
    'DIECISEIS ',
    'DIECISIETE ',
    'DIECIOCHO ',
    'DIECINUEVE ',
    'VEINTE '
)

DECENAS = (
    'VEINTI',
    'TREINTA ',
    'CUARENTA ',
    'CINCUENTA ',
    'SESENTA ',
    'SETENTA ',
    'OCHENTA ',
    'NOVENTA ',
    'CIEN '
)

CENTENAS = (
    'CIENTO ',
    'DOSCIENTOS ',
    'TRESCIENTOS ',
    'CUATROCIENTOS ',
    'QUINIENTOS ',
    'SEISCIENTOS ',
    'SETECIENTOS ',
    'OCHOCIENTOS ',
    'NOVECIENTOS '
)

UNITS = (
    ('',''),
    ('MIL ','MIL '),
    ('MILLON ','MILLONES '),
    ('MIL MILLONES ','MIL MILLONES '),
    ('BILLON ','BILLONES '),
    ('MIL BILLONES ','MIL BILLONES '),
    ('TRILLON ','TRILLONES '),
    ('MIL TRILLONES','MIL TRILLONES'),
    ('CUATRILLON','CUATRILLONES'),
    ('MIL CUATRILLONES','MIL CUATRILLONES'),
    ('QUINTILLON','QUINTILLONES'),
    ('MIL QUINTILLONES','MIL QUINTILLONES'),
    ('SEXTILLON','SEXTILLONES'),
    ('MIL SEXTILLONES','MIL SEXTILLONES'),
    ('SEPTILLON','SEPTILLONES'),
    ('MIL SEPTILLONES','MIL SEPTILLONES'),
    ('OCTILLON','OCTILLONES'),
    ('MIL OCTILLONES','MIL OCTILLONES'),
    ('NONILLON','NONILLONES'),
    ('MIL NONILLONES','MIL NONILLONES'),
    ('DECILLON','DECILLONES'),
    ('MIL DECILLONES','MIL DECILLONES'),
    ('UNDECILLON','UNDECILLONES'),
    ('MIL UNDECILLONES','MIL UNDECILLONES'),
    ('DUODECILLON','DUODECILLONES'),
    ('MIL DUODECILLONES','MIL DUODECILLONES'),
)

#ISO 4217
CURRENCY = (
    {'country': u'Colombia', 'currency': 'COP', 'singular': u'PESO COLOMBIANO', 'plural': u'PESOS COLOMBIANOS', 'symbol': u'$'},
    {'country': u'Estados Unidos', 'currency': 'USD', 'singular': u'DÓLAR', 'plural': u'DÓLARES', 'symbol': u'US$'},
    {'country': u'Europa', 'currency': 'EUR', 'singular': u'EURO', 'plural': u'EUROS', 'symbol': u'€', 'decimalsingular':u'Céntimo','decimalplural':u'Céntimos'},
    {'country': u'México', 'currency': 'MXN', 'singular': u'PESO MEXICANO', 'plural': u'PESOS MEXICANOS', 'symbol': u'$'},
    {'country': u'Perú', 'currency': 'PEN', 'singular': u'NUEVO SOL', 'plural': u'NUEVOS SOLES', 'symbol': u'S/.'},
    {'country': u'Reino Unido', 'currency': 'GBP', 'singular': u'LIBRA', 'plural': u'LIBRAS', 'symbol': u'£'},
    {'country': u'Uruguay', 'currency': 'UYU', 'singular': u'PESO URUGUAYO', 'plural': u'PESOS URUGUAYOS', 'symbol': u'$', 'decimalsingular':u'Centavo','decimalplural':u'Centavos'}
)

def __convert_group(n):
    """Turn each group of numbers into letters"""
    output = ''
    if(n == '100'):
        output = "CIEN "
    elif(n[0] != '0'):
        output = CENTENAS[int(n[0]) - 1]
    k = int(n[1:])
    if(k <= 20):
        output += UNIDADES[k]
    else:
        if((k > 30) & (n[2] != '0')):
            output += '%sY %s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
        else:
            output += '%s%s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
    return output

def hundreds_word(number):
    """Converts a positive number less than a thousand (1000) to words in Spanish

    Args:
        number (int): A positive number less than 1000
    Returns:
        A string in Spanish with first letters capitalized representing the number in letters
    Examples:
        >>> to_word(123)
        'Ciento Ventitres'
    """
    converted = ''
    if not (0 < number < 1000):
        return 'No es posible convertir el numero a letras'
    number_str = str(number).zfill(9)
    cientos = number_str[6:]
    if(cientos):
        if(cientos == '001'):
            converted += 'UN '
        elif(int(cientos) > 0):
            converted += '%s ' % __convert_group(cientos)
    return converted.title().strip()

def _check_currency(number, currency):
    integer = ""
    fraction = ""
    if currency != None:
        currency = currency.upper()
        try:
            _currency = filter(lambda x: x['currency'] == currency, CURRENCY).next()
            if int(number) == 1:
                integer = _currency['singular']
            else:
                integer = _currency['plural']
                if round(float(number) - int(number), 2) == float(0.01):
                    fraction = _currency.get('decimalsingular',"")
                else:
                    fraction = _currency.get('decimalplural',"")
        except:
            pass
    return integer, fraction

def to_word(number, currency=None, decimals_separator_str=None, negative_str=None):
    """Converts a positive number less than:
    (999999999999999999999999999999999999999999999999999999999999999999999999)
    to words in Spanish

    Args:
        number (int or float): A number less than specified above
        currency(str, optional): A string in ISO 4217 short format
        decimals_separator_str(str, optional): A string to show decimals separator, by default is "punto"
        negative_str(str, optional): A string to show negative numbers, by default is "Menos"
    Returns:
        A string in Spanish with first letters capitalized representing the number in letters
    Examples:
        >>> to_word(53625999567)
        'Cincuenta Y Tres Mil Seiscientos Venticinco Millones Novecientos Noventa Y Nueve Mil Quinientos Sesenta Y Siete'
        >>>> to_word(1481.01, 'EUR',decimals_separator_str='con')
        'Mil Cuatrocientos Ochenta Y Un Euros con Un Céntimo'
    """
    if not decimals_separator_str:
        decimals_separator_str = "punto"
    if not negative_str:
        negative_str = "Menos"
    entero, fraccion = _check_currency(number, currency)
    negative = ""
    if number < 0:
        number = number * (-1)
        negative = negative_str + ' '
    human_readable = []
    human_readable_decimals = []
    num_decimals ='{:,.2f}'.format(round(number,2)).split('.') #Only 2 decimals
    num_units = num_decimals[0].split(',')
    num_decimals = num_decimals[1].split(',')

    for i,n in enumerate(num_units):
        if int(n) != 0:
            words = hundreds_word(int(n))
            units = UNITS[len(num_units)-i-1][0 if int(n) == 1 else 1]
            human_readable.append([words,units])
    for i,n in enumerate(num_decimals):
        if int(n) != 0:
            words = hundreds_word(int(n))
            units = UNITS[len(num_decimals)-i-1][0 if int(n) == 1 else 1]
            human_readable_decimals.append([words,units])

    #filtrar MIL MILLONES - MILLONES -> MIL - MILLONES
    for i,item in enumerate(human_readable):
        try:
            if human_readable[i][1].find(human_readable[i+1][1]):
                human_readable[i][1] = human_readable[i][1].replace(human_readable[i+1][1],'')
        except IndexError:
            pass
    human_readable = [item for sublist in human_readable for item in sublist]
    human_readable.append(entero)
    for i,item in enumerate(human_readable_decimals):
        try:
            if human_readable_decimals[i][1].find(human_readable_decimals[i+1][1]):
                human_readable_decimals[i][1] = human_readable_decimals[i][1].replace(human_readable_decimals[i+1][1],'')
        except IndexError:
            pass
    human_readable_decimals = [item for sublist in human_readable_decimals for item in sublist]
    human_readable_decimals.append(fraccion)
    sentence = negative + ' '.join(human_readable).replace('  ',' ').title().strip()
    if sentence[0:len('un mil')] == 'Un Mil':
        sentence = 'Mil' + sentence[len('Un Mil'):]
    if num_decimals != ['00']:
        sentence = sentence + ' ' + decimals_separator_str + ' ' + ' '.join(human_readable_decimals).replace('  ',' ').title().strip()
    return sentence
