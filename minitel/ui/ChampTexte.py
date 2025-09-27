#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Text field management class"""

from .UI import UI
from ..constantes import (
    GAUCHE, DROITE, CORRECTION, ACCENT_AIGU, ACCENT_GRAVE, ACCENT_CIRCONFLEXE, 
    ACCENT_TREMA, ACCENT_CEDILLE
)

# Characters from the Minitel handled by the text field
CARACTERES_MINITEL = (
    'abcdefghijklmnopqrstuvwxyz' +
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
    ' *$!:;,?./&(-_)=+\'@#' +
    '0123456789'
)

class ChampTexte(UI):
    """Text field management class

    This class manages a text field. Like the text fields of a
    HTML form, this text field has a displayable length and a
    maximum total length.

    ChampTexte does not manage any labels.

    The following attributes are available:

    - longueur_visible: length occupied by the field on the screen
    - longueur_totale: maximum number of characters in the field
    - valeur: value of the field (UTF-8 encoded)
    - curseur_x: position of the cursor in the field
    - decalage: start of display of the field on the screen
    - accent: accent waiting to be applied to the next character
    - champ_cache: the characters are not displayed on the minitel, they are
                    replaced by '*' (used for passwords for example)
    """
    def __init__(self, minitel, posx, posy, longueur_visible,
                 longueur_totale = None, valeur = '', couleur = None, champ_cache=False):
        assert isinstance(posx, int)
        assert isinstance(posy, int)
        assert isinstance(longueur_visible, int)
        assert isinstance(longueur_totale, int) or longueur_totale == None
        assert isinstance(valeur, str)
        assert posx + longueur_visible < 80
        assert longueur_visible >= 1
        if longueur_totale == None:
            longueur_totale = longueur_visible
        assert longueur_visible <= longueur_totale

        UI.__init__(self, minitel, posx, posy, longueur_visible, 1, couleur)

        # Initializes the field
        self.longueur_visible = longueur_visible
        self.longueur_totale = longueur_totale
        self.valeur = '' + valeur
        self.curseur_x = 0
        self.decalage = 0
        self.activable = True
        self.accent = None
        self.champ_cache = champ_cache

    def gere_touche(self, sequence) -> bool:
        """Key management

        This method is called automatically by the executer method.

        The keys managed by the ChampTexte class are as follows:

        - GAUCHE, DROITE, to move around in the field,
        - CORRECTION, to delete the character to the left of the cursor,
        - ACCENT_AIGU, ACCENT_GRAVE, ACCENT_CIRCONFLEXE, ACCENT_TREMA,
        - ACCENT_CEDILLE,
        - the characters of the ASCII standard that can be typed on a Minitel
          keyboard.

        :param sequence:
            The sequence received from the Minitel.
        :type sequence:
            a Sequence object

        :returns:
            True if the key was handled by the text field, False otherwise.
        """
        if sequence.egale(GAUCHE):
            self.accent = None
            self.curseur_gauche()
            return True        
        elif sequence.egale(DROITE):
            self.accent = None
            self.curseur_droite()
            return True        
        elif sequence.egale(CORRECTION):
            self.accent = None
            if self.curseur_gauche():
                self.valeur = (self.valeur[0:self.curseur_x] +
                               self.valeur[self.curseur_x + 1:])
                self.affiche()
            return True        
        elif (sequence.egale(ACCENT_AIGU) or
              sequence.egale(ACCENT_GRAVE) or
              sequence.egale(ACCENT_CIRCONFLEXE) or
              sequence.egale(ACCENT_TREMA)):
            self.accent = sequence
            return True
        elif sequence.egale([ACCENT_CEDILLE, 'c']):
            self.accent = None
            self.valeur = (self.valeur[0:self.curseur_x] +
                           'ç' +
                           self.valeur[self.curseur_x:])
            self.curseur_droite()
            self.affiche()
            return True
        elif chr(sequence.valeurs[0]) in CARACTERES_MINITEL:
            caractere = '' + chr(sequence.valeurs[0])
            if self.accent != None:
                if caractere in 'aeiou':
                    if self.accent.egale(ACCENT_AIGU):
                        caractere = 'áéíóú'['aeiou'.index(caractere)]
                    elif self.accent.egale(ACCENT_GRAVE):
                        caractere = 'àèìòù'['aeiou'.index(caractere)]
                    elif self.accent.egale(ACCENT_CIRCONFLEXE):
                        caractere = 'âêîôû'['aeiou'.index(caractere)]
                    elif self.accent.egale(ACCENT_TREMA):
                        caractere = 'äëïöü'['aeiou'.index(caractere)]

                self.accent = None

            self.valeur = (self.valeur[0:self.curseur_x] +
                           caractere +
                           self.valeur[self.curseur_x:])
            self.curseur_droite()
            self.affiche()
            return True        

        return False

    def curseur_gauche(self):
        """Moves the cursor one character to the left

        If the cursor cannot be moved, a beep is emitted.

        If the cursor requests to move to a part of the field that is not
        yet visible, a shift occurs.

        :returns:
            True if the cursor has been moved, False otherwise.
        """
        # We cannot move the cursor to the left if it is already on the first
        # character
        if self.curseur_x == 0:
            self.minitel.bip()
            return False

        self.curseur_x = self.curseur_x - 1

        # Performs a shift if the cursor overflows the visible area
        if self.curseur_x < self.decalage:
            self.decalage = max(
                0,
                int(self.decalage - self.longueur_visible / 2)
            )
            self.affiche()
        else:
            self.minitel.position(
                self.posx + self.curseur_x - self.decalage,
                self.posy
            )

        return True
    
    def curseur_droite(self):
        """Moves the cursor one character to the right

        If the cursor cannot be moved, a beep is emitted.

        If the cursor requests to move to a part of the field that is not
        yet visible, a shift occurs.

        :returns:
            True if the cursor has been moved, False otherwise.
        """
        # We cannot move the cursor to the right if it is already on the last
        # character or at the maximum length
        if self.curseur_x == min(len(self.valeur), self.longueur_totale):
            self.minitel.bip()
            return False
    
        self.curseur_x = self.curseur_x + 1

        # Performs a shift if the cursor overflows the visible area
        if self.curseur_x > self.decalage + self.longueur_visible:
            self.decalage = max(
                0,
                int(self.decalage + self.longueur_visible / 2)
            )
            self.affiche()
        else:
            self.minitel.position(
                self.posx + self.curseur_x - self.decalage,
                self.posy
            )

        return True

    def gere_arrivee(self):
        """Manages the activation of the text field

        The method positions the cursor and makes it visible.
        """
        self.minitel.position(
            self.posx + self.curseur_x - self.decalage,
            self.posy
        )
        self.minitel.curseur(True)

    def gere_depart(self):
        """Manages the deactivation of the text field

        The method cancels any accent start and makes the cursor invisible.
        """
        self.accent = None
        self.minitel.curseur(False)

    def affiche(self):
        """Displays the text field

        If the value is smaller than the displayed length, we fill the
        extra spaces with dots.

        After calling this method, the cursor is automatically positioned.

        This method is called as soon as we want to display the element.
        """
        # Start of the text field on the screen
        self.minitel.curseur(False)
        self.minitel.position(self.posx, self.posy)

        # Label color
        if self.couleur != None:
            self.minitel.couleur(caractere = self.couleur)

        if not self.champ_cache :
            #If the field is not hidden, we display the characters
            val = str( self.valeur )
        else : 
            val = "*" * len( self.valeur  ) 

        if len(val) - self.decalage <= self.longueur_visible:
            # Case where value is smaller than visible length
            affichage = val[self.decalage:]
            affichage = affichage.ljust(self.longueur_visible, '.')
        else:
            # Case where value is larger than visible length
            affichage = val[
                self.decalage:
                self.decalage + self.longueur_visible
            ]

        # Displays the content
        self.minitel.envoyer(affichage)

        # Makes the cursor visible
        self.minitel.position(
            self.posx + self.curseur_x - self.decalage,
            self.posy
        )
        self.minitel.curseur(True)

