#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Base for creating a user interface for the Minitel"""

from ..Minitel import Minitel,Empty
from typing import Union

class UI:
    """Base class for creating user interface elements

    This class provides a framework for creating other
    classes to create a user interface.

    It establishes the following attributes:

    - posx and posy: top-left coordinates of the element
    - largeur and hauteur: dimensions in characters of the element
    - minitel: a Minitel object used for displaying the element
    - couleur: foreground/character color
    - activable: boolean indicating if the element can receive Minitel
      events (keyboard)

    Classes derived from UI must implement the following methods:
    - __init__: object initialization
    - affiche: object display
    - efface: object erasure
    - gere_touche: key press management (if the element is activable)
    - gere_arrivee: element activation management
    - gere_depart: element deactivation management

    """
    def __init__(self, minitel, posx, posy, largeur, hauteur, couleur):
        """Constructor

        :param minitel:
            The object to which to send commands and receive key
            presses.
        :type minitel:
            a Minitel object

        :param posx:
            x-coordinate of the element
        :type posx:
            an integer

        :param posy:
            y-coordinate of the element
        :type posy:
            an integer
        
        :param largeur:
            Width of the element in characters
        :type largeur:
            an integer
        
        :param hauteur:
            Height of the element in characters
        :type hauteur:
            an integer
        
        :param couleur:
            Color of the element
        :type couleur:
            an integer or a string
        """
        assert isinstance(minitel, Minitel)
        assert posx > 0 and posx <= 80
        assert posy > 0 and posy <= 24
        assert largeur > 0 and largeur + posx - 1 <= 80
        assert hauteur > 0 and hauteur + posy - 1 <= 80
        assert isinstance(couleur, (int, str)) or couleur == None

        # A UI element is always attached to a Minitel object
        self.minitel = minitel

        # A UI element occupies a rectangular area of the Minitel screen
        self.posx = posx
        self.posy = posy
        self.largeur = largeur
        self.hauteur = hauteur
        self.couleur = couleur

        # A UI element may or may not receive keyboard events
        # By default, it does not receive them
        self.activable = False

    def executer(self):
        """Execution loop of an element

        Calling this method starts an infinite loop that will
        manage key presses (gere_touche method) from the Minitel.
        As soon as a key is not handled by the element, the loop stops.
        """
        while True:
            try:
                r = self.minitel.recevoir_sequence(attente=30)
                if not self.gere_touche(r):
                    break
            except Empty :
                pass

    def affiche(self):
        """Displays the element

        This method is called as soon as we want to display the element.
        """
        pass

    def efface(self):
        """Erases the element

        This method is called as soon as we want to erase the element. By
        default, it displays a rectangle containing spaces instead of
        the element. It can be overridden to obtain more
        advanced display management.
        """
        for ligne in range(self.posy, self.posy + self.hauteur):
            self.minitel.position(self.posx, ligne)
            self.minitel.repeter(' ', self.largeur)

    # Disables a false positive. It is normal for this method not to use
    # the sequence argument and for it to be a method rather than a
    # function
    # pylint: disable-msg=W0613,R0201
    def gere_touche(self, sequence) -> bool:
        """Handles a key press

        This method is called automatically by the executer method as soon
        as a sequence is available for processing.

        For any interactive element, this method must be overridden because
        it does not handle any keys by default and therefore returns False.

        :param sequence:
            the character sequence from the Minitel that the element
            must process.
        :type sequence:
            a Sequence object

        :returns:
            a boolean indicating whether the key was handled by
            the element (True) or if the element could not process the key
            (False).
        """
        return False

    def gere_arrivee(self):
        """Manages the activation of the element

        This method is called when the element is activated (when it
        receives keyboard keys).
        """
        pass

    def gere_depart(self):
        """Manages the deactivation of the element

        This method is called when the element is deactivated (when it no
        longer receives keyboard keys).
        """
        pass

