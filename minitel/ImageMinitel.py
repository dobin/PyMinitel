#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ImageMinitel is a class for converting an image readable by
PIL into semi-graphics for the Minitel.

"""

from operator import itemgetter

from minitel.constantes import ESC, SO, DC2, COULEURS_MINITEL
from minitel.Sequence import Sequence
from minitel.Minitel import Minitel
from math import sqrt

def _huit_niveaux(niveau):
    """Converts a level on 8 bits (256 possible values) into a level
    on 3 bits (8 possible values).

    :param niveau:
        Level to convert. If a tuple is provided, the brightness of
        the color is then calculated. The formula is from the page
        http://alienryderflex.com/hsp.html
    :type niveau:
        a tuple or an integer

    :returns:
        An integer between 0 and 7 inclusive.
    """
    # Level can be either a tuple or an integer
    # Handles both cases by testing the exception
    try:
        return niveau * 8 / 256
    except TypeError:
        return int(
            round(
                sqrt(
                    0.299 * niveau[0] ** 2 +
                    0.587 * niveau[1] ** 2 +
                    0.114 * niveau[2] ** 2
                )
            ) * 8 / 256
        )

def _deux_couleurs(couleurs):
    """Reduces a list of colors to a pair of two colors.

    The two colors retained are the most frequently
    present colors.

    :param couleurs:
        The colors to reduce. Each color must be an integer between
        0 and 7 inclusive.
    :type couleurs:
        A list of integers

    :returns:
        A tuple of two integers representing the selected colors.
    """
    assert isinstance(couleurs, list)

    # Creates a list containing the number of times a level is
    # recorded
    niveaux = [0, 0, 0, 0, 0, 0, 0, 0]

    # Goes through all the levels to count them
    for couleur in couleurs:
        niveaux[couleur] += 1

    # Prepares the list of levels in order to be able to sort it from the most
    # used to the least used. To do this, we create a list of tuples
    # (level, number of appearances)
    niveaux = [(index, valeur) for index, valeur in enumerate(niveaux)]

    # Sorts the levels by number of appearances
    niveaux = sorted(niveaux, key = itemgetter(1), reverse = True)

    # Returns the two most encountered levels
    return (niveaux[0][0], niveaux[1][0])

def _arp_ou_avp(couleur, arp, avp):
    """Converts a color into a background or foreground color.

    The conversion is done by calculating the proximity of the color with the
    background color (arp) and with the foreground color (avp).

    :param couleur:
        The color to convert (value from 0 to 7 inclusive).
    :type couleur:
        an integer

    :param arp:
        The background color (value from 0 to 7 inclusive)
    :type arp:
        an integer

    :param avp:
        The foreground color (value from 0 to 7 inclusive)
    :type avp:
        an integer

    :returns:
        0 if the color is closer to the background color, 1 if
        the color is closer to the foreground color.
    """
    assert isinstance(couleur, int)
    assert isinstance(arp, int)
    assert isinstance(avp, int)

    if(abs(arp - couleur) < abs(avp - couleur)):
        return 0

    return 1

def _minitel_arp(niveau):
    """Converts a level into a sequence of Minitel codes defining the
    background color.

    :param niveau:
        The level to convert (value from 0 to 7 inclusive).
    :type niveau:
        an integer

    :returns:
        A Sequence object containing the sequence to send to the
        Minitel for a background color corresponding to the
        level.
    """
    assert isinstance(niveau, int)

    try:
        return Sequence([ESC, 0x50 + COULEURS_MINITEL[niveau]])
    except IndexError:
        return Sequence([ESC, 0x50])

def _minitel_avp(niveau):
    """Converts a level into a sequence of Minitel codes defining the
    foreground color.

    :param niveau:
        The level to convert (value from 0 to 7 inclusive).
    :type niveau:
        an integer

    :returns:
        A Sequence object containing the sequence to send to the
        Minitel for a foreground color corresponding to the level.
    """
    assert isinstance(niveau, int)

    try:
        return Sequence([ESC, 0x40 + COULEURS_MINITEL[niveau]])
    except IndexError:
        return Sequence([ESC, 0x47])

class ImageMinitel:
    """A class for managing Minitel images with conversion from an image
    readable by PIL.

    This class manages an image in the Minitel sense of the term, that is to say by
    the use of the semi-graphic mode in which a character contains
    a combination of 2×3 pixels. This gives a maximum resolution of 80×72
    pixels.
    
    Apart from the low resolution thus obtained, the semi-graphic mode has
    several disadvantages compared to a true graphic mode:

    - there can only be 2 colors per 2×3 pixel block,
    - the pixels are not square
    """

    def __init__(self, minitel, disjoint = False):
        """Constructor

        :param minitel:
            The object to which to send the commands
        :type minitel:
            a Minitel object
        :param disjoint:
            Activates disjoint mode for images.
        :type disjoint:
            a boolean
        """
        assert isinstance(minitel, Minitel)
        assert isinstance(disjoint, bool)

        self.minitel = minitel

        # The image is stored as Sequences in order to be able to
        # display it at any position on the screen
        self.sequences = []

        self.largeur = 0
        self.hauteur = 0
        self.disjoint = disjoint

    def envoyer(self, colonne = 1, ligne = 1):
        """Sends the image to the Minitel at a given position

        On the Minitel, the first column has the value 1. The first line
        also has the value 1 although line 0 exists. The latter
        corresponds to the status line and has a different operation
        from the other lines.

        :param colonne:
            column at which to position the top left corner of the image
        :type colonne:
            an integer

        :param ligne:
            line at which to position the top left corner of the image
        :type ligne:
            an integer
        """
        assert isinstance(colonne, int)
        assert isinstance(ligne, int)

        for sequence in self.sequences:
            self.minitel.position(colonne, ligne)
            self.minitel.envoyer(sequence)
            ligne += 1

    def importer(self, image):
        """Imports an image from PIL and creates the corresponding Minitel code
        sequences. The supplied image must have been reduced to
        dimensions less than or equal to 80×72 pixels. The width must be
        a multiple of 2 and the height a multiple of 3.

        :param image:
            The image to import.
        :type niveau:
            an Image
        """
        assert image.size[0] <= 80
        assert image.size[1] <= 72

        # In semi-graphic mode, a character is 2 pixels wide
        # and 3 pixels high
        self.largeur = int(image.size[0] / 2)
        self.hauteur = int(image.size[1] / 3)

        # Initializes the list of sequences
        self.sequences = []

        for hauteur in range(0, self.hauteur):
            # Variables for optimizing the generated code
            old_arp = -1
            old_avp = -1
            old_alpha = 0
            compte = 0

            # Initializes a new sequence
            sequence = Sequence()

            # Switches to semi-graphic mode
            sequence.ajoute(SO)

            if self.disjoint:
                sequence.ajoute([ESC, 0x5A])

            for largeur in range(0, self.largeur):
                # Retrieves 6 pixels
                pixels = [
                    image.getpixel((largeur * 2 + x, hauteur * 3 + y))
                    for x, y in [(0, 0), (1, 0),
                                  (0, 1), (1, 1),
                                  (0, 2), (1, 2)]
                ]

                if self.disjoint:
                    # Converts each pixel color into two gray levels
                    pixels = [_huit_niveaux(pixel) for pixel in pixels]

                    arp, avp = _deux_couleurs(pixels)

                    if arp != 0:
                        arp, avp = 0, arp

                else:
                    # Converts each pixel color into eight gray levels
                    pixels = [_huit_niveaux(pixel) for pixel in pixels]

                    # Searches for the two most frequent colors
                    # a character can only have two colors!
                    arp, avp = _deux_couleurs(pixels)

                # Reduces the number of colors in a 6-pixel block to two
                # This can cause artifacts but is unavoidable
                pixels = [_arp_ou_avp(pixel, arp, avp) for pixel in pixels]

                # Converts the 6 pixels into a Minitel mosaic character
                # The character is coded on 7 bits
                bits = [
                    '0',
                    str(pixels[5]),
                    '1',
                    str(pixels[4]),
                    str(pixels[3]),
                    str(pixels[2]),
                    str(pixels[1]),
                    str(pixels[0])
                ]

                # Generates the byte (7 bits) of the mosaic character
                alpha = int(''.join(bits), 2)

                # If the colors of the previous character are inverted,
                # inverts the mosaic character. This avoids re-emitting
                # color codes. This only works
                # when disjoint mode is not active
                if not self.disjoint and old_arp == avp and old_avp == arp:
                    # Inverts each bit except the 6th and 8th
                    alpha = alpha ^ 0b01011111
                    avp, arp = arp, avp
                    
                if old_arp == arp and old_avp == avp and alpha == old_alpha:
                    # The previous pixels are identical, we remember it
                    # to use a repetition code later
                    compte += 1
                else:
                    # The pixels have changed, but there may be pixels
                    # that have not yet been emitted for optimization reasons
                    if compte > 0:
                        if compte == 1:
                            sequence.ajoute(old_alpha)
                        else:
                            sequence.ajoute([DC2, 0x40 + compte])

                        compte = 0

                    # Generates the Minitel codes
                    if old_arp != arp:
                        # The background has changed
                        sequence.ajoute(_minitel_arp(arp))
                        old_arp = arp

                    if old_avp != avp:
                        # The foreground has changed
                        sequence.ajoute(_minitel_avp(avp))
                        old_avp = avp

                    sequence.ajoute(alpha)
                    old_alpha = alpha

            if compte > 0:
                if compte == 1:
                    sequence.ajoute(old_alpha)
                else:
                    sequence.ajoute([DC2, 0x40 + compte])

                compte = 0

            if self.disjoint:
                sequence.ajoute([ESC, 0x59])

            # A line has just been finished, we store it in the list of
            # sequences
            self.sequences.append(sequence)
