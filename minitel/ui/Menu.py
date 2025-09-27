#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Menu management class"""
from .UI import UI
from ..constantes import HAUT, BAS
from ..Sequence import Sequence

class Menu(UI):
    """Menu management class

    This class allows displaying a menu to the user so that they can
    select an entry using the UP and DOWN keys.

    The management of the action in case of validation or cancellation is the responsibility
    of the calling program.

    It establishes the following attributes:

    - options: array containing the options (unicode strings),
    - selection: selected option (index in the options array),
    - largeur_ligne: line width determined from the longest line.

    The options are contained in an array of the following form::

        options = [
          u'New',
          u'Open',
          u'-',
          u'Save',
          u'Save as...',
          u'Restore',
          u'-',
          u'Preview',
          u'Print...',
          u'-',
          u'Close',
          u'Quit'
        ]

    A minus (-) indicates a separator.

    There cannot be the same entry twice in the options list.

    """
    def __init__(self, minitel, options, posx, posy, selection = 0,
                 couleur = None):
        self.options = options
        self.selection = selection

        # Determines the width of the menu
        self.largeur_ligne = 0
        for option in self.options:
            self.largeur_ligne = max(self.largeur_ligne, len(option))

        # Determines the width and height of the menu display area
        largeur = self.largeur_ligne + 2
        hauteur = len(self.options) + 2

        UI.__init__(self, minitel, posx, posy, largeur, hauteur, couleur)

        self.activable = True

    def gere_touche(self, sequence):
        """Key management

        This method is called automatically by the executer method.

        The keys managed by the Menu class are UP and DOWN to
        move around in the menu.

        A beep is emitted if the UP (respectively DOWN) key is pressed
        while the selection is already on the first (respectively
        last) line.

        :param sequence:
            The sequence received from the Minitel.
        :type sequence:
            a Sequence object

        :returns:
            True if the key was handled by the menu, False otherwise.
        """
        assert isinstance(sequence, Sequence)

        if sequence.egale(HAUT):
            selection = self.option_precedente(self.selection)
            if selection == None:
                self.minitel.bip()
            else:
                self.change_selection(selection)

            return True

        if sequence.egale(BAS):
            selection = self.option_suivante(self.selection)
            if selection == None:
                self.minitel.bip()
            else:
                self.change_selection(selection)

            return True

        return False

    def affiche(self):
        """Displays the complete menu"""
        i = 0

        # Position on the top line
        self.minitel.position(self.posx + 1, self.posy)

        # Application of color if necessary
        if self.couleur != None:
            self.minitel.couleur(caractere = self.couleur)

        # Draws the top line
        self.minitel.repeter(0x5f, self.largeur_ligne)

        # Draws the lines one by one
        for _ in self.options:
            # Application of color if necessary
            if self.couleur != None:
                self.minitel.couleur(caractere = self.couleur)

            # Displays the current line indicating if it is selected
            self.affiche_ligne(i, self.selection == i)
            i += 1

        # Position on the bottom line
        self.minitel.position(self.posx + 1, self.posy + len(self.options) + 1)

        # Application of color if necessary
        if self.couleur != None:
            self.minitel.couleur(caractere = self.couleur)

        # Draws the bottom line
        self.minitel.repeter(0x7e, self.largeur_ligne)

    def affiche_ligne(self, selection, etat = False):
        """Displays a line of the menu
        
        :param selection:
            index of the line to display in the options list
        :type selection:
            a positive integer
        
        :param etat:
        :type etat:
            a boolean
        """
        assert isinstance(selection, int)
        assert selection >= 0 and selection < len(self.options)
        assert etat in [True, False]

        # Positions at the beginning of the line
        self.minitel.position(self.posx, self.posy + selection + 1)

        # Application of color if necessary
        if self.couleur != None:
            self.minitel.couleur(caractere = self.couleur)

        # Draws the left line
        self.minitel.envoyer([0x7d])

        # 2 possible cases: a separator or a normal entry
        if self.options[selection] == '-':
            self.minitel.repeter(0x60, self.largeur_ligne)
        else:
            # If the option is selected, we apply the inverse video effect
            if etat:
                self.minitel.effet(inversion = True)

            # Draws an entry by left-justifying it over the width of
            # the line
            option = self.options[selection]
            self.minitel.envoyer(option.ljust(self.largeur_ligne))

        # If the option is selected, we stop the inverse video effect
        if etat:
            self.minitel.effet(inversion = False)

        # Draws the right line
        self.minitel.envoyer([0x7b])
        
    def change_selection(self, selection):
        """Changes the current selection
        
        :param selection:
            index of the line to select in the options list
        :type selection:
            a positive integer
        """
        assert isinstance(selection, int)
        assert selection >= 0 and selection < len(self.options)

        # If the new selection is the current selection, we ignore it
        if self.selection == selection:
            return

        # Displays the current selected line as not selected
        self.affiche_ligne(self.selection, False)

        # Displays the new selected line
        self.affiche_ligne(selection, True)

        # Updates the index of the selected option
        self.selection = selection

    def option_suivante(self, numero):
        """Determines the index of the next option

        Returns the index of the option following the option indicated by the
        numero argument.

        :param numero:
            index of the line to select in the options list
        :type numero:
            a positive integer

        :returns:
            the index of the next option or None if it does not exist.
        """
        assert isinstance(numero, int)
        assert numero >= 0 and numero < len(self.options)

        # Traverses the options after the numero index while staying within the
        # limits of the options list
        for i in range(numero + 1, len(self.options)):
            # Separators are ignored
            if self.options[i] != '-':
                return i

        # No option was found after the one indicated in numero
        return None
    
    def option_precedente(self, numero):
        """Determines the index of the previous option

        Returns the index of the option preceding the option indicated by the
        numero argument.

        :param numero:
            index of the line to select in the options list
        :type numero:
            a positive integer

        :returns:
            the index of the previous option or None if it does not exist.
        """
        assert isinstance(numero, int)
        assert numero >= 0 and numero < len(self.options)

        # Traverses the options before the numero index while staying within the
        # limits of the options list
        for i in range(numero - 1, -1, -1):
            # Separators are ignored
            if self.options[i] != '-':
                return i

        # No option was found before the one indicated in numero
        return None
