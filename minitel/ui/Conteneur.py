#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Class for grouping user interface elements"""

from .UI import UI
from ..Sequence import Sequence
from ..constantes import ENTREE, MAJ_ENTREE

class Conteneur(UI):
    """Class for grouping user interface elements

    This class allows grouping user interface elements to
    facilitate their management. It is notably capable of displaying all the
    elements it contains and managing the transition from one element to another.

    The transition from one element to another is done using the ENTER key for
    the next element and the SHIFT+ENTER combination for the
    previous element. If the user wants the next element while already
    on the last element, the Minitel will emit a beep. Same for the
    previous element.

    Elements whose activable attribute is False are purely and
    simply ignored during inter-element navigation.

    The following attributes are available:

    - elements: list of elements in their order of appearance
    - element_actif: UI class object designating the active element
    - fond: background color of the container
    """
    def __init__(self, minitel, posx, posy, largeur, hauteur, couleur = None,
                 fond = None):
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
            an integer, a string or None

        :param fond:
            Background color of the container
        :type couleur:
            an integer, a string or None
        """
        assert isinstance(posx, int)
        assert isinstance(posy, int)
        assert isinstance(largeur, int)
        assert isinstance(hauteur, int)
        assert isinstance(couleur, (str, int)) or couleur == None
        assert isinstance(fond, (str, int)) or fond == None

        # Attribute initialization
        self.elements = []
        self.element_actif = None
        self.fond = fond

        UI.__init__(self, minitel, posx, posy, largeur, hauteur, couleur)

    def gere_touche(self, sequence):
        """Key management

        This method is called automatically by the executer method.

        It first tries to have the key processed by the active element.
        If the active element does not handle the key, the container tests if the
        ENTER or SHIFT+ENTER keys have been pressed. These two keys
        allow the user to navigate between elements.

        In case of a change of active element, the container calls the
        gere_depart method of the old active element and the gere_arrivee method of the
        new active element.

        :param sequence:
            The sequence received from the Minitel.
        :type sequence:
            a Sequence object

        :returns:
            True if the key was handled by the container or one of its
            elements, False otherwise.
        """
        assert isinstance(sequence, Sequence)

        # No active element? So nothing to do
        if self.element_actif == None:
            return False

        # Forwards the sequence to the active element
        touche_geree = self.element_actif.gere_touche(sequence)

        # If the active element has processed the sequence, it's over
        if touche_geree:
            return True

        # If the active element has not processed the sequence, see if the
        # container can process it

        # The enter key allows moving to the next field
        if sequence.egale(ENTREE):
            self.element_actif.gere_depart()
            self.suivant()
            self.element_actif.gere_arrivee()
            return True

        # The Shift + Enter combination allows moving to the previous field
        if sequence.egale(MAJ_ENTREE):
            self.element_actif.gere_depart()
            self.precedent()
            self.element_actif.gere_arrivee()
            return True

        return False
            
    def affiche(self):
        """Displays the container and its elements

        When this method is called, the container draws the background if the
        background color has been defined. Then, it asks each of the
        contained elements to draw itself.

        Note:
            The coordinates of the container and the coordinates of the elements are
            independent.

        """
        # Colors the container background if a background color has been defined
        if self.fond != None:
            for posy in range(self.posy, self.posy + self.hauteur):
                self.minitel.position(self.posx, posy)
                self.minitel.couleur(fond = self.fond)
                self.minitel.repeter(' ', self.largeur)

        # Asks each element to display itself
        for element in self.elements:
            element.affiche()

        # If an active element has been defined, we give it control
        if self.element_actif != None:
            self.element_actif.gere_arrivee()

    def ajoute(self, element):
        """Adds an element to the container

        The container maintains an ordered list of its elements.

        When an element is added, if its color has not been defined, it
        takes that of the container.

        If no element of the container is active and the added element is
        activable, it automatically becomes the active element for the
        container.

        :param element:
            the element to add to the ordered list.
        
        :type element:
            an object of class UI or its descendants.
        """
        assert isinstance(element, UI)
        assert element not in self.elements

        # Assigns the container's color to the element by default
        if element.couleur == None:
            element.couleur = self.couleur

        # Adds the element to the container's list of elements
        self.elements.append(element)

        if self.element_actif == None and element.activable == True:
            self.element_actif = element

    def suivant(self):
        """Moves to the next active element

        This method selects the next activable element in the list
        from the active element.

        :returns:
            True if a next active element was found and selected,
            False otherwise.
        """
        # If there are no elements, there can be no active element
        if len(self.elements) == 0:
            return False

        # Gets the index of the active element
        if self.element_actif == None:
            index = -1
        else:
            index = self.elements.index(self.element_actif)

        # Searches for the next element that is activable
        while index < len(self.elements) - 1:
            index += 1
            if self.elements[index].activable == True:
                self.element_actif = self.elements[index]
                return True

        return False

    def precedent(self):
        """Moves to the previous active element

        This method selects the previous activable element in the list
        from the active element.

        :returns:
            True if a previous active element was found and selected,
            False otherwise.
        """
        # If there are no elements, there can be no active element
        if len(self.elements) == 0:
            return False

        # Gets the index of the active element
        if self.element_actif == None:
            index = len(self.elements)
        else:
            index = self.elements.index(self.element_actif)

        # Searches for the next element that is activable
        while index > 0:
            index -= 1
            if self.elements[index].activable == True:
                self.element_actif = self.elements[index]
                return True

        return False

