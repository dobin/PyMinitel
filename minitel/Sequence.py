#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sequence is a module for managing character sequences
that can be sent to a Minitel.

"""

from unicodedata import normalize
from binascii import unhexlify

# Conversion tables for special characters
UNICODEVERSVIDEOTEX = {
    '£': '1923', '°': '1930', '±': '1931', 
    '←': '192C', '↑': '192D', '→': '192E', '↓': '192F', 
    '¼': '193C', '½': '193D', '¾': '193E', 
    'ç': '194B63', '’': '194B27', 
    'à': '194161', 'á': '194261', 'â': '194361', 'ä': '194861', 
    'è': '194165', 'é': '194265', 'ê': '194365', 'ë': '194865', 
    'ì': '194169', 'í': '194269', 'î': '194369', 'ï': '194869', 
    'ò': '19416F', 'ó': '19426F', 'ô': '19436F', 'ö': '19486F', 
    'ù': '194175', 'ú': '194275', 'û': '194375', 'ü': '194875', 
    'Œ': '196A', 'œ': '197A', 
    'ß': '197B', 'β': '197B'
}

UNICODEVERSAUTRE = {
    '£': '0E230F',
    '°': '0E5B0F', 'ç': '0E5C0F', '’': '27', '`': '60', '§': '0E5D0F',
    'à': '0E400F', 'è': '0E7F0F', 'é': '0E7B0F', 'ù': '0E7C0F'
}

class Sequence:
    """A class representing a sequence of values

    A Sequence is a series of values ready to be sent to a Minitel.
    These values comply with the ASCII standard.
    """
    def __init__(self, valeur = None, standard = 'VIDEOTEX'):
        """Sequence constructor

        :param valeur:
            value to add when constructing the object. If the value is
            None, no value is added
        :type valeur:
            a string, an integer, a list, a sequence or
            None

        :param standard:
            standard to use for unicode to Minitel conversion. The
            possible values are VIDEOTEX, MIXTE and TELEINFORMATIQUE (case
            is important)
        :type standard:
            a string
        """
        assert valeur == None or \
                isinstance(valeur, (list, int, str, Sequence))
        assert standard in ['VIDEOTEX', 'MIXTE', 'TELEINFORMATIQUE']

        self.valeurs = []
        self.longueur = 0
        self.standard = standard

        if valeur != None:
            self.ajoute(valeur)
        
    def ajoute(self, valeur):
        """Adds a value or a sequence of values

        The submitted value is first canonicalized by the canonise method before
        being added to the sequence. This ensures that the sequence only contains
        integers representing characters of the ASCII standard.

        :param valeur:
            value to add
        :type valeur:
            a string, an integer, a list or a Sequence
        """
        assert isinstance(valeur, (list, int, str, Sequence))

        self.valeurs += self.canonise(valeur)
        self.longueur = len(self.valeurs)

    def canonise(self, valeur):
        """Canonicalizes a character sequence

        If a list is submitted, whatever its depth, it will be
        flattened. A list can therefore contain strings,
        integers or lists. This facility allows for easier construction of
        character sequences. It also facilitates the
        comparison of two sequences.

        :param valeur:
            value to canonicalize
        :type valeur:
            a string, an integer, a list or a Sequence

        :returns:
            A list of depth 1 of integers representing values in the
            ASCII standard.

        Example::
            canonise(['dd', 32, ['dd', 32]]) will return
            [100, 100, 32, 100, 100, 32]
        """
        assert isinstance(valeur, (list, int, str, Sequence))

        # If the value is just an integer, we keep it in a list
        if isinstance(valeur, int):
            return [valeur]

        # If the value is a Sequence, its values have already been canonicalized
        if isinstance(valeur, Sequence):
            return valeur.valeurs

        # At this point, the parameter contains either a string or
        # a list. Either one is iterable with a for ... in loop
        # Recursively transforms each element of the list into an integer
        canonise = []
        for element in valeur:
            if isinstance(element, str):
                # This loop handles 2 cases: the one where list is a unicode
                # string and the one where element is a string
                for caractere in element:
                    for ascii in self.unicode_vers_minitel(caractere):
                        canonise.append(ascii)
            elif isinstance(element, int):
                # An integer just needs to be added to the final list
                canonise.append(element)
            elif isinstance(element, list):
                # If the element is a list, we canonicalize it recursively
                canonise = canonise + self.canonise(element)

        return canonise

    def unicode_vers_minitel(self, caractere):
        """Converts a unicode character to its Minitel equivalent

        :param caractere:
            character to convert
        :type valeur:
            a unicode string

        :returns:
            a string containing a sequence of characters for
            the Minitel.
        """
        assert isinstance(caractere, str) and len(caractere) == 1

        if self.standard == 'VIDEOTEX':
            if caractere in UNICODEVERSVIDEOTEX:
                return unhexlify(UNICODEVERSVIDEOTEX[caractere])
        else:
            if caractere in UNICODEVERSAUTRE:
                return unhexlify(UNICODEVERSAUTRE[caractere])

        return normalize('NFKD', caractere).encode('ascii', 'replace')

    def egale(self, sequence):
        """Tests the equality of 2 sequences

        :param sequence:
            sequence to compare. If the sequence is not a Sequence object,
            it is first converted to a Sequence object in order to canonicalize its
            values.
        :type sequence:
            a Sequence object, a list, an integer, a string
            or a unicode string

        :returns:
            True if the 2 sequences are equal, False otherwise
        """
        assert isinstance(sequence, (Sequence, list, int, str))

        # If the sequence to compare is not of the Sequence class, then
        # we convert it
        if not isinstance(sequence, Sequence):
            sequence = Sequence(sequence)

        return self.valeurs == sequence.valeurs

