#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Label management class"""
from .UI import UI

class Label(UI):
    """Label management class

    It only displays a single line of text.
    """
    def __init__(self, minitel, posx, posy, valeur = '', couleur = None):
        assert isinstance(posx, int)
        assert isinstance(posy, int)
        assert isinstance(valeur, str) or isinstance(valeur, str)

        # Initializes the field
        self.valeur = valeur

        UI.__init__(self, minitel, posx, posy, len(self.valeur), 1, couleur)

    def gere_touche(self, sequence):
        """Key management

        This method is called automatically by the executer method.

        A Label does not handle any keys and therefore always returns False.

        :param sequence:
            The sequence received from the Minitel.
        :type sequence:
            a Sequence object

        :returns:
            False
        """
        return False

    def affiche(self):
        """Displays the label

        This method is called as soon as we want to display the element.
        """
        # Start of the label on the screen
        self.minitel.position(self.posx, self.posy)

        # Label color
        if self.couleur != None:
            self.minitel.couleur(caractere = self.couleur)

        # Displays the content
        self.minitel.envoyer(self.valeur)

