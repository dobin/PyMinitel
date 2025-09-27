#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Minitel is a module for controlling a Minitel from a Python script.
"""

from serial import Serial      # Physical link with the Minitel
from threading import Thread   # Threads for sending/receiving
from queue import Queue, Empty # Character queues for sending/receiving

from minitel.Sequence import Sequence # Manages character sequences

from minitel.constantes import (SS2, SEP, ESC, CSI, PRO1, PRO2, PRO3, MIXTE1,
    MIXTE2, TELINFO, ENQROM, SOH, EOT, TYPE_MINITELS, STATUS_FONCTIONNEMENT,
    LONGUEUR_PRO2, STATUS_TERMINAL, PROG, START, STOP, LONGUEUR_PRO3,
    RCPT_CLAVIER, ETEN, C0, MINUSCULES, RS, US, VT, LF, BS, TAB, CON, COF,
    AIGUILLAGE_ON, AIGUILLAGE_OFF, RCPT_ECRAN, EMET_MODEM, FF, CAN, BEL, CR,
    SO, SI, B300, B1200, B4800, B9600, REP, COULEURS_MINITEL,
    CAPACITES_BASIQUES, CONSTRUCTEURS)

def normaliser_couleur(couleur):
    """Returns the Minitel color number.

    From a color provided as a string with the
    name of the color in French or an integer indicating a level of
    gray, this function returns the corresponding color number
    for the Minitel.

    :param couleur:
        Accepted values are noir, rouge, vert, jaune, bleu,
        magenta, cyan, blanc, and integers from 0 (black) to 7 (white)
    :type couleur:
        a string or an integer

    :returns:
        The corresponding color number on the Minitel or None if
        the requested color is not valid.
    """
    assert isinstance(couleur, (str, int))

    # The color is converted to a string so that the caller
    # can use '0' (str) or 0 (int) interchangeably.
    couleur = str(couleur)

    if couleur in COULEURS_MINITEL:
        return COULEURS_MINITEL[couleur]

    return None

class Minitel:
    """A class for controlling the Minitel via a serial port

    Introduction
    ============

    The Minitel class allows sending and receiving character sequences
    to and from a Minitel in a Python program.
    It works via a serial link between the computer and the Minitel.

    By default, it uses /dev/ttyUSB0 as the device. Indeed, one
    of the easiest ways to connect a Minitel to a computer
    is to use a 5v USB-TTL cable (PL2303) because the
    Minitel's peripheral socket works in TTL (0v/5v) and not in RS232
    (-12v/12v). This type of cable embeds a component that is recognized
    automatically by Linux kernels and is assigned to /dev/ttyUSB*. Under
    Android, the Linux kernel does not have the driver as standard.

    As long as the selected device is a serial device, this
    class should not pose any problem for communicating with the Minitel.
    For example, it is entirely possible to create a serial proxy by
    using an Arduino connected via USB to the computer and whose
    pins would be connected to the Minitel.

    The Minitel class allows determining the operating speed of the
    Minitel, identifying the model, configuring it, and sending and receiving
    character sequences.

    Given its threaded operation, the main program
    using this class does not have to worry about being available to receive
    the character sequences sent by the Minitel.

    Quick Start
    ================

    The lifecycle of a Minitel object consists of creation,
    determining the Minitel's speed, its capabilities, the use
    of the Minitel by the application, and the release of resources::
        
        from minitel.Minitel import Minitel

        minitel = Minitel()

        minitel.deviner_vitesse()
        minitel.identifier()

        # ...
        # Use of the minitel object
        # ...

        minitel.close()

    """
    def __init__(self, peripherique = 'COM3'):
        """Minitel constructor

        The serial connection is established according to the Minitel's basic standard.
        When switched on, the Minitel is configured at 1200 bps, 7 bits, even parity,
        Videotex mode.

        This may not correspond to the actual configuration of the Minitel at
        the time of execution. However, this is not a problem because the
        serial connection can be reconfigured at any time.

        :param peripherique:
            The device to which the Minitel is connected. By default, the
            device is /dev/ttyUSB0
        :type peripherique:
            String
    
        """
        assert isinstance(peripherique, str)

        # Initializes the Minitel's state
        self.mode = 'VIDEOTEX'
        self.vitesse = 1200

        # Initializes the list of Minitel capabilities
        self.capacite = CAPACITES_BASIQUES

        # Creates the two input/output queues
        self.entree = Queue()
        self.sortie = Queue()

        # Initializes the connection with the Minitel
        self._minitel = Serial(
            peripherique,
            baudrate = 1200, # 1200 bps speed, the Minitel standard
            bytesize = 7,    # 7-bit character size
            parity   = 'E',  # even parity
            stopbits = 1,    # 1 stop bit
            timeout  = 1,    # 1 second timeout
            xonxoff  = False,    # no software control
            rtscts   = False     # no hardware control
        )

        # Initializes a flag to stop the threads
        # (threads share the same variables as the main code)
        self._continuer = True

        # Creates the two read/write threads
        self._threads = []
        self._threads.append(Thread(None, self._gestion_entree, None, ()))
        self._threads.append(Thread(None, self._gestion_sortie, None, ()))

        # Starts the two read/write threads
        for thread in self._threads:
            # Configures each thread in daemon mode
            thread.setDaemon(True)
            try:
                # Starts the thread
                thread.start()
            except (KeyboardInterrupt, SystemExit):
                self.close()

    def close(self):
        """Closes the connection with the Minitel

        Tells the send/receive threads that they should stop and
        waits for them to stop. As the send and receive timeouts are
        set to 1 second, this is the average time this method will take to
        execute.
        """
        # Tells the threads that they should stop all activity
        self._continuer = False

        # Waits for all threads to finish
        for thread in self._threads:
            thread.join()

        self._minitel.close()

    def _gestion_entree(self):
        """Manages character sequences sent from the Minitel

        This method should not be called directly, it is reserved
        exclusively for the Minitel class. It loops indefinitely trying
        to read a character on the serial connection.
        """
        # Adds to the entree queue everything the Minitel can send
        while self._continuer:
            # Waits for a character for 1 second
            caractere = self._minitel.read()

            if len(caractere) == 1:
                self.entree.put(caractere)

    def _gestion_sortie(self):
        """Manages character sequences sent to the Minitel

        This method should not be called directly, it is reserved
        exclusively for the Minitel class. It loops indefinitely trying
        to read a character from the output queue.
        """
        # Sends to the Minitel everything in the sortie queue and
        # continues to do so as long as the continuer flag is true
        while self._continuer or not self.sortie.empty():
            # Waits for a character for 1 second
            try:
                sortie_unicode = self.sortie.get(block = True, timeout = 1)
                self._minitel.write(sortie_unicode.encode())

                # Waits for the character sent to the minitel to have been sent
                # because the output is buffered
                self._minitel.flush()

                # Allows the queue's join method to work
                self.sortie.task_done()

            except Empty:
                continue

    def envoyer(self, contenu):
        """Sends a character sequence

        Sends a character sequence towards the Minitel.

        :param contenu:
            A character sequence interpretable by the Sequence class.
        :type contenu:
            a Sequence object, a string or unicode, a list,
            an integer
        """
        # Converts any input into a Sequence object
        if not isinstance(contenu, Sequence):
            contenu = Sequence(contenu)

        # Adds the characters one by one to the send queue
        for valeur in contenu.valeurs:
            self.sortie.put(chr(valeur))

    def recevoir(self, bloque = False, attente = None):
        """Reads a character from the Minitel

        Returns a character present in the receive queue.

        :param bloque:
            True to wait for a character if there are none in the
            receive queue. False to not wait and
            return immediately.
        :type bloque:
            a boolean

        :param attente:
            wait in seconds, values below a second
            accepted. Valid only in bloque = True mode
            If attente = None and bloque = True, then we wait
            indefinitely for a character to arrive.
        :type attente:
            an integer, or None

        :raise Empty:
            Raises an Empty exception if bloque = True
            and the waiting time has been exceeded
        """
        assert bloque in [True, False]
        assert isinstance(attente, (int,float)) or attente == None

        return self.entree.get(bloque, attente).decode()

    def recevoir_sequence(self,bloque = True, attente=None):
        """Reads a sequence from the Minitel

        Returns a Sequence object received from the Minitel. This function
        analyzes the Minitel's transmissions to make a consistent sequence
        from the Minitel's point of view. For example, if the Minitel sends a
        SS2, SEP or ESC character, it only announces a series of
        characters designating a result or a character that does not exist in the
        ASCII standard. On the other hand, the number of characters that can be received
        after special characters is standardized. This allows to know
        exactly the number of characters that will constitute the sequence.

        It is this method that should be used rather than the
        recevoir method when communicating with the Minitel.

        :param bloque:
            True to wait for a sequence if there are none in the
            receive queue. False to not wait and
            return immediately.
        :type bloque:
            a boolean

        :param attente:
            wait in seconds, values below a second
            accepted. Valid only in bloque = True mode
            If attente = None and bloque = True, then we wait
            indefinitely for a character to arrive.
        :type attente:
            an integer, or None

        :returns:
            a Sequence object
        """
        # Creates a sequence
        sequence = Sequence()

        # Adds the first character read to the sequence in blocking mode
        sequence.ajoute(self.recevoir(bloque = bloque, attente = attente))
        assert sequence.longueur != 0

        # Tests the received character
        if sequence.valeurs[-1] in [SS2, SEP]:
            # A sequence starting with SS2 or SEP will have a length of 2
            sequence.ajoute(self.recevoir(bloque = True))
        elif sequence.valeurs[-1] == ESC:
            # ESC sequences have variable sizes ranging from 1 to 4
            try:
                # Tries to read a character with a waiting time of 1/10s
                # This allows reading the Esc key which sends
                # only the ESC code with nothing after.
                sequence.ajoute(self.recevoir(bloque = True, attente = 0.1))

                # A CSI sequence starts with ESC, 0x5b
                if sequence.valeurs == CSI:
                    # A CSI sequence calls for at least 1 character
                    sequence.ajoute(self.recevoir(bloque = True))

                    if sequence.valeurs[-1] in [0x32, 0x34]:
                        # The sequence ESC, 0x5b, 0x32/0x34 calls for a last
                        # character
                        sequence.ajoute(self.recevoir(bloque = True))
            except Empty:
                # If no character has occurred after 1/10s, we continue
                pass

        return sequence

    def appeler(self, contenu, attente):
        """Sends a sequence to the Minitel and waits for its response.

        This method allows sending a command to the Minitel (configuration,
        status query) and waiting for its response. This function waits
        at most 1 second before giving up. In this case, an empty sequence
        is returned.

        Before launching the command, the method empties the receive queue.

        :param contenu:
            A character sequence interpretable by the Sequence
            class
        :type contenu:
            a Sequence object, a string, a unicode string
            or an integer

        :param attente:
            Number of characters expected from the Minitel in
            response to our sending.
        :type attente:
            an integer

        :returns:
            a Sequence object containing the Minitel's response to the command
            sent.
        """
        assert isinstance(attente, int)

        # Empties the receive queue
        self.entree = Queue()

        # Sends the sequence
        self.envoyer(contenu)

        # Waits for the entire sequence to have been sent
        self.sortie.join()

        # Tries to receive the number of characters indicated by the attente
        # parameter with a delay of 1 second.
        retour = Sequence()
        for _ in range(0, attente):
            try:
                # Waits for a character
                entree_bytes = self.entree.get(block = True, timeout = 1)
                retour.ajoute(entree_bytes.decode())
            except Empty:
                # If a character has not been sent in less than a second,
                # we give up
                break

        return retour

    def definir_mode(self, mode = 'VIDEOTEX'):
        """Defines the Minitel's operating mode.

        The Minitel can operate in 3 modes: VideoTex (the standard Minitel
        mode, the one when switched on), Mixed or TeleInformatique (an
        80-column mode).

        The definir_mode method takes into account the current mode of the Minitel to
        issue the correct command.

        :param mode:
            a value among the following: VIDEOTEX,
            MIXTE or TELEINFORMATIQUE (case is important).
        :type mode:
            a string

        :returns:
            False if the mode change could not take place, True otherwise.
        """
        assert isinstance(mode, str)

        # 3 modes are possible
        if mode not in ['VIDEOTEX', 'MIXTE', 'TELEINFORMATIQUE']:
            return False

        # If the requested mode is already active, do nothing
        if self.mode == mode:
            return True

        resultat = False

        # There are 9 possible cases, but only 6 are relevant. The cases
        # asking to switch from VIDEOTEX to VIDEOTEX, for example, do not give
        # rise to any transaction with the Minitel
        if self.mode == 'TELEINFORMATIQUE' and mode == 'VIDEOTEX':
            retour = self.appeler([CSI, 0x3f, 0x7b], 2)
            resultat = retour.egale([SEP, 0x5e])
        elif self.mode == 'TELEINFORMATIQUE' and mode == 'MIXTE':
            # There is no command to switch directly from
            # TeleInformatique mode to Mixed mode. We therefore perform the
            # transition in two steps via Videotex mode
            retour = self.appeler([CSI, 0x3f, 0x7b], 2)
            resultat = retour.egale([SEP, 0x5e])

            if not resultat:
                return False

            retour = self.appeler([PRO2, MIXTE1], 2)
            resultat = retour.egale([SEP, 0x70])
        elif self.mode == 'VIDEOTEX' and mode == 'MIXTE':
            retour = self.appeler([PRO2, MIXTE1], 2)
            resultat = retour.egale([SEP, 0x70])
        elif self.mode == 'VIDEOTEX' and mode == 'TELEINFORMATIQUE':
            retour = self.appeler([PRO2, TELINFO], 4)
            resultat = retour.egale([CSI, 0x3f, 0x7a])
        elif self.mode == 'MIXTE' and mode == 'VIDEOTEX':
            retour = self.appeler([PRO2, MIXTE2], 2)
            resultat = retour.egale([SEP, 0x71])
        elif self.mode == 'MIXTE' and mode == 'TELEINFORMATIQUE':
            retour = self.appeler([PRO2, TELINFO], 4)
            resultat = retour.egale([CSI, 0x3f, 0x7a])

        # If the change has taken place, we keep the new mode in memory
        if resultat:
            self.mode = mode

        return resultat

    def identifier(self):
        """Identifies the connected Minitel.

        This method must be called once the connection with the
        Minitel has been established in order to determine the available
        features and characteristics.

        No value is returned. Instead, the capacite attribute of
        the object contains a dictionary of values providing information on the
        Minitel's capabilities:

        - capacite['nom'] -- Name of the Minitel (e.g. Minitel 2)
        - capacite['retournable'] -- Can the Minitel be flipped and
          serve as a modem? (True or False)
        - capacite['clavier'] -- Keyboard (None, ABCD or Azerty)
        - capacite['vitesse'] -- Max speed in bps (1200, 4800 or 9600)
        - capacite['constructeur'] -- Manufacturer's name (e.g. Philips)
        - capacite['80colonnes'] -- Can the Minitel display 80
          columns? (True or False)
        - capacite['caracteres'] -- Can characters be redefined?
          (True or False)
        - capacite['version'] -- Software version (a letter)
        """
        self.capacite = CAPACITES_BASIQUES

        # Issues the identification command
        retour = self.appeler([PRO1, ENQROM], 5)

        # Tests the validity of the response
        if (retour.longueur != 5 or
            retour.valeurs[0] != SOH or
            retour.valeurs[4] != EOT):
            return

        # Extracts the identification characters
        constructeur_minitel = chr(retour.valeurs[1])
        type_minitel         = chr(retour.valeurs[2])
        version_logiciel     = chr(retour.valeurs[3])

        # Minitel types
        if type_minitel in TYPE_MINITELS:
            self.capacite = TYPE_MINITELS[type_minitel]

        if constructeur_minitel in CONSTRUCTEURS:
            self.capacite['constructeur'] = CONSTRUCTEURS[constructeur_minitel]

        self.capacite['version'] = version_logiciel

        # Manufacturer correction
        if constructeur_minitel == 'B' and type_minitel == 'v':
            self.capacite['constructeur'] = 'Philips'
        elif constructeur_minitel == 'C':
            if version_logiciel == ['4', '5', ';', '<']:
                self.capacite['constructeur'] = 'Telic ou Matra'

        # Determines the screen mode in which the Minitel is
        retour = self.appeler([PRO1, STATUS_FONCTIONNEMENT], LONGUEUR_PRO2)

        if retour.longueur != LONGUEUR_PRO2:
            # The Minitel is in Teleinformatique mode because it does not respond
            # to a protocol command
            self.mode = 'TELEINFORMATIQUE'
        elif retour.valeurs[3] & 1 == 1:
            # Bit 1 of the operating status indicates 80-column mode
            self.mode = 'MIXTE'
        else:
            # By default, we consider that we are in Videotex mode
            self.mode = 'VIDEOTEX'

    def deviner_vitesse(self):
        """Guesses the connection speed with the Minitel.

        This method should be called just after creating the object
        in order to automatically determine the transmission speed on
        which the Minitel is set.

        To perform the detection, the deviner_vitesse method will test the
        speeds 9600 bps, 4800 bps, 1200 bps and 300 bps (in this order) and
        send a PRO1 terminal status request command each time.
        If the Minitel responds with a PRO2 acknowledgment, we have detected the speed.

        In case of detection, the speed is stored in the vitesse attribute
        of the object.

        :returns:
            The method returns the speed in bits per second or -1 if it
            could not be determined.
        """
        # Possible speeds up to Minitel 2
        vitesses = [9600, 4800, 1200, 300]

        for vitesse in vitesses:
            # Configures the serial port to the speed to be tested
            self._minitel.baudrate = vitesse

            # Sends a terminal status request
            retour = self.appeler([PRO1, STATUS_TERMINAL], LONGUEUR_PRO2)

            # The Minitel must return a PRO2 acknowledgment
            if retour.longueur == LONGUEUR_PRO2:
                self.vitesse = vitesse
                return vitesse

        # The speed was not found
        return -1

    def definir_vitesse(self, vitesse):
        """Programs the Minitel and the serial port for a given speed.

        To change the communication speed between the computer and the
        Minitel, the developer must first ensure that the connection with
        the Minitel has been established at the correct speed (see the
        deviner_vitesse method).

        This method should only be called after the Minitel has been
        identified (see the identifier method) because it is based on the
        detected capabilities of the Minitel.

        The method first sends a speed setting command to the Minitel
        and, if it accepts it, configures the serial port to the new
        speed.

        :param vitesse:
            speed in bits per second. Accepted values are 300, 1200,
            4800 and 9600. The value 9600 is only allowed from Minitel
            2
        :type vitesse:
            an integer

        :returns:
            True if the speed could be programmed, False otherwise.
        """
        assert isinstance(vitesse, int)

        # Possible speeds up to Minitel 2
        vitesses = {300: B300, 1200: B1200, 4800: B4800, 9600: B9600}

        # Tests the validity of the requested speed
        if vitesse not in vitesses or vitesse > self.capacite['vitesse']:
            return False

        # Sends a protocol command for speed programming
        retour = self.appeler([PRO2, PROG, vitesses[vitesse]], LONGUEUR_PRO2)

        # The Minitel must return a PRO2 acknowledgment
        if retour.longueur == LONGUEUR_PRO2:
            # If we can read a PRO2 acknowledgment before having set the
            # serial port speed, it means that the Minitel cannot use
            # the requested speed
            return False

        # Configures the serial port to the new speed
        self._minitel.baudrate = vitesse
        self.vitesse = vitesse

        return True

    def configurer_clavier(self, etendu = False, curseur = False,
                           minuscule = False):
        """Configures the keyboard operation.

        Configures the operation of the Minitel keyboard. This impacts the
        codes and characters that the Minitel can send to the computer
        depending on the keys pressed (alphabetic keys, function keys,
        key combinations, etc.).

        The method returns True if all configuration commands have
        been correctly processed by the Minitel. As soon as a command fails,
        the method stops immediately and returns False.

        :param etendu:
            True for an extended mode keyboard, False for a normal mode
            keyboard
        :type etendu:
            a boolean

        :param curseur:
            True if the cursor keys should be managed, False otherwise
        :type curseur:
            a boolean

        :param minuscule:
            True if pressing an alphabetic key without simultaneously pressing
            the Shift key should generate a lowercase letter, False if it
            should generate an uppercase letter.
        :type minuscule:
            a boolean
        """
        assert etendu in [True, False]
        assert curseur in [True, False]
        assert minuscule in [True, False]

        # The keyboard commands work on a start/stop toggle principle
        bascules = { True: START, False: STOP }

        # Creates the sequences of the 3 calls according to the arguments
        appels = [
            ([PRO3, bascules[etendu   ], RCPT_CLAVIER, ETEN], LONGUEUR_PRO3),
            ([PRO3, bascules[curseur  ], RCPT_CLAVIER, C0  ], LONGUEUR_PRO3),
            ([PRO2, bascules[minuscule], MINUSCULES        ], LONGUEUR_PRO2)
        ]

        # Sends the commands one by one
        for appel in appels:
            commande = appel[0] # First element of the tuple = command
            longueur = appel[1] # Second element of the tuple = response length

            retour = self.appeler(commande, longueur)

            if retour.longueur != longueur:
                return False

        return True

    def couleur(self, caractere = None, fond = None):
        """Defines the colors used for the next characters.

        The possible colors are black, red, green, yellow, blue, magenta,
        cyan, white and a gray level from 0 to 7.

        Note:
        In Videotex, the background color only applies to delimiters. These
        delimiters are the space and semi-graphic characters. Defining
        the background color and immediately displaying a character other
        than a delimiter (a letter for example) will have no effect.

        If a color is set to None, the method does not issue any
        command to the Minitel.

        If a color is not valid, it is simply ignored.

        :param caractere:
            color to assign to the foreground.
        :type caractere:
            a string, an integer or None

        :param fond:
            color to assign to the background.
        :type fond:
            a string, an integer or None
        """
        assert isinstance(caractere, (str, int)) or caractere == None
        assert isinstance(fond, (str, int)) or fond == None

        # Defines the foreground color (the character color)
        if caractere != None:
            couleur = normaliser_couleur(caractere)
            if couleur != None:
                self.envoyer([ESC, 0x40 + couleur])

        # Defines the background color (the background color)
        if fond != None:
            couleur = normaliser_couleur(fond)
            if couleur != None:
                self.envoyer([ESC, 0x50 + couleur])

    def position(self, colonne, ligne, relatif = False):
        """Defines the position of the Minitel cursor

        Note:
        This method optimizes cursor movement, so it is important
        to consider the positioning mode (relative vs.
        absolute) because the number of characters generated can range from 1 to 5.

        On the Minitel, the first column has the value 1. The first line
        also has the value 1 although line 0 exists. The latter
        corresponds to the status line and has a different operation
        from the other lines.

        :param colonne:
            column to position the cursor at
        :type colonne:
            a relative integer

        :param ligne:
            line to position the cursor at
        :type ligne:
            a relative integer

        :param relatif:
            indicates whether the coordinates provided are relative
            (True) to the current cursor position or if
            they are absolute (False, default value)
        :type relatif:
            a boolean
        """
        assert isinstance(colonne, int)
        assert isinstance(ligne, int)
        assert relatif in [True, False]

        if not relatif:
            # Absolute movement
            if colonne == 1 and ligne == 1:
                self.envoyer([RS])
            else:
                self.envoyer([US, 0x40 + ligne, 0x40 + colonne])
        else:
            # Relative movement from the current position
            if ligne != 0:
                if ligne >= -4 and ligne <= -1:
                    # Short upward movement
                    self.envoyer([VT]*-ligne)
                elif ligne >= 1 and ligne <= 4:
                    # Short downward movement
                    self.envoyer([LF]*ligne)
                else:
                    # Long upward or downward movement
                    direction = { True: 'B', False: 'A'}
                    self.envoyer([CSI, str(ligne), direction[ligne < 0]])

            if colonne != 0:
                if colonne >= -4 and colonne <= -1:
                    # Short leftward movement
                    self.envoyer([BS]*-colonne)
                elif colonne >= 1 and colonne <= 4:
                    # Short rightward movement
                    self.envoyer([TAB]*colonne)
                else:
                    # Long leftward or rightward movement
                    direction = { True: 'C', False: 'D'}
                    self.envoyer([CSI, str(colonne), direction[colonne < 0]])

    def taille(self, largeur = 1, hauteur = 1):
        """Defines the size of the next characters

        The Minitel is capable of enlarging characters. Four sizes are
        available:

        - largeur = 1, hauteur = 1: normal size
        - largeur = 2, hauteur = 1: characters twice as wide
        - largeur = 1, hauteur = 2: characters twice as high
        - largeur = 2, hauteur = 2: characters twice as high and wide

        Note:
        This command only works in Videotex mode.

        Positioning with characters twice as high is done from
        the bottom of the character.

        :param largeur:
            width multiplier (1 or 2)
        :type largeur:
            an integer

        :param hauteur:
            height multiplier (1 or 2)
        :type hauteur:
            an integer
        """
        assert largeur in [1, 2]
        assert hauteur in [1, 2]

        self.envoyer([ESC, 0x4c + (hauteur - 1) + (largeur - 1) * 2])

    def effet(self, soulignement = None, clignotement = None, inversion = None):
        """Activates or deactivates effects

        The Minitel has 3 effects on characters: underline,
        blinking and video inversion.

        :param soulignement:
            indicates whether to activate underlining (True) or deactivate it
            (False)
        :type soulignement:
            a boolean or None

        :param clignotement:
            indicates whether to activate blinking (True) or deactivate it
            (False)
        :type clignotement:
            a boolean or None

        :param inversion:
            indicates whether to activate video inversion (True) or deactivate it
            (False)
        :type inversion:
            a boolean or None
        """
        assert soulignement in [True, False, None]
        assert clignotement in [True, False, None]
        assert inversion in [True, False, None]

        # Manages underlining
        soulignements = {True: [ESC, 0x5a], False: [ESC, 0x59], None: None}
        self.envoyer(soulignements[soulignement])

        # Manages blinking
        clignotements = {True: [ESC, 0x48], False: [ESC, 0x49], None: None}
        self.envoyer(clignotements[clignotement])

        # Manages video inversion
        inversions = {True: [ESC, 0x5d], False: [ESC, 0x5c], None: None}
        self.envoyer(inversions[inversion])

    def curseur(self, visible):
        """Activates or deactivates the cursor display

        The Minitel can display a blinking cursor at the
        display position of the next characters.

        It is interesting to deactivate it when the computer has to send
        long character sequences because the Minitel will try to
        display the cursor for each character displayed, generating an
        unpleasant effect.

        :param visible:
            indicates whether to activate the cursor (True) or make it invisible
            (False)
        :type visible:
            a boolean
        """
        assert visible in [True, False]

        etats = {True: CON, False: COF}
        self.envoyer([etats[visible]])

    def echo(self, actif):
        """Activates or deactivates keyboard echo

        By default, the Minitel sends any character typed on the keyboard to both
        the screen and the peripheral socket. This trick saves the
        computer from having to send back to the screen the last character typed,
        thus saving bandwidth.

        In the case where the computer offers a more advanced user interface,
        it is important to be able to control exactly what is
        displayed by the Minitel.

        The method returns True if the command has been correctly processed by the
        Minitel, False otherwise.

        :param actif:
            indicates whether to activate echo (True) or deactivate it (False)
        :type actif:
            a boolean

        :returns:
            True if the command was accepted by the Minitel, False otherwise.
        """
        assert actif in [True, False]

        actifs = {
            True: [PRO3, AIGUILLAGE_ON, RCPT_ECRAN, EMET_MODEM],
            False: [PRO3, AIGUILLAGE_OFF, RCPT_ECRAN, EMET_MODEM]
        }
        retour = self.appeler(actifs[actif], LONGUEUR_PRO3)
        
        return retour.longueur == LONGUEUR_PRO3

    def efface(self, portee = 'tout'):
        """Erases all or part of the screen

        This method allows erasing:


        :param portee:
            indicates the scope of the erasure:

            - the whole screen ('tout'),
            - from the cursor to the end of the line ('finligne'),
            - from the cursor to the bottom of the screen ('finecran'),
            - from the beginning of the screen to the cursor ('debutecran'),
            - from the beginning of the line to the cursor ('debut_ligne'),
            - the entire line ('ligne'),
            - the status line, row 00 ('statut'),
            - the whole screen and the status line ('vraimenttout').
        :type porte:
            a string
        """
        portees = {
            'tout': [FF],
            'finligne': [CAN],
            'finecran': [CSI, 0x4a],
            'debutecran': [CSI, 0x31, 0x4a],
            #'tout': [CSI, 0x32, 0x4a],
            'debut_ligne': [CSI, 0x31, 0x4b],
            'ligne': [CSI, 0x32, 0x4b],
            'statut': [US, 0x40, 0x41, CAN, LF],
            'vraimenttout': [FF, US, 0x40, 0x41, CAN, LF]
        }

        assert portee in portees

        self.envoyer(portees[portee])

    def repeter(self, caractere, longueur):
        """Repeats a character

        :param caractere:
            character to repeat
        :type caractere:
            a string

        :param longueur:
            the number of times the character is repeated
        :type longueur:
            a positive integer
        """
        assert isinstance(longueur, int)
        assert longueur > 0 and longueur <= 40
        assert isinstance(caractere, (str, int, list))
        assert isinstance(caractere, int) or len(caractere) == 1

        self.envoyer([caractere, REP, 0x40 + longueur - 1])

    def bip(self):
        """Emits a beep

        Asks the Minitel to emit a beep
        """
        self.envoyer([BEL])

    def debut_ligne(self):
        """Return to the beginning of the line

        Positions the cursor at the beginning of the current line.
        """
        self.envoyer([CR])

    def supprime(self, nb_colonne = None, nb_ligne = None):
        """Deletes characters after the cursor

        By specifying a number of columns, this method deletes
        characters after the cursor, the Minitel brings back the last characters
        contained on the line.
        
        By specifying a number of lines, this method deletes lines
        below the line containing the cursor, moving up the following lines.

        :param nb_colonne:
            number of characters to delete
        :type nb_colonne:
            a positive integer
        :param nb_ligne:
            number of lines to delete
        :type nb_ligne:
            a positive integer
        """
        assert (isinstance(nb_colonne, int) and nb_colonne >= 0) or \
                nb_colonne == None
        assert (isinstance(nb_ligne, int) and nb_ligne >= 0) or \
                nb_ligne == None

        if nb_colonne != None:
            self.envoyer([CSI, str(nb_colonne), 'P'])

        if nb_ligne != None:
            self.envoyer([CSI, str(nb_ligne), 'M'])

    def insere(self, nb_colonne = None, nb_ligne = None):
        """Inserts characters after the cursor

        By inserting characters after the cursor, the Minitel pushes the
        last characters contained on the line to the right.

        :param nb_colonne:
            number of characters to insert
        :type nb_colonne:
            a positive integer
        :param nb_ligne:
            number of lines to insert
        :type nb_ligne:
            a positive integer
        """
        assert (isinstance(nb_colonne, int) and nb_colonne >= 0) or \
                nb_colonne == None
        assert (isinstance(nb_ligne, int) and nb_ligne >= 0) or \
                nb_ligne == None

        if nb_colonne != None:
            self.envoyer([CSI, '4h', ' ' * nb_colonne, CSI, '4l'])

        if nb_ligne != None:
            self.envoyer([CSI, str(nb_ligne), 'L'])

    def semigraphique(self, actif = True):
        """Switches to semi-graphic mode or alphabetic mode

        :param actif:
            True to switch to semi-graphic mode, False to return to
            normal mode
        :type actif:
            a boolean
        """
        assert actif in [True, False]

        actifs = { True: SO, False: SI}
        self.envoyer(actifs[actif])

    def redefinir(self, depuis, dessins, jeu = 'G0'):
        """Redefines Minitel characters

        From Minitel 2, it is possible to redefine characters.
        Each character is drawn from an 8×10 pixel matrix.

        The character designs are given by a sequence of 0s and 1s in
        a string. Any other character is purely and
        simply ignored. This feature allows drawing the
        characters from a standard text editor and adding
        comments.
        
        Example::

            11111111
            10000001
            10000001
            10000001
            10000001 This is a rectangle!
            10000001
            10000001
            10000001
            10000001
            11111111

        The Minitel does not insert any separation pixels between the characters,
        so this must be taken into account and included in your designs.

        Once the character(s) are redefined, the special character set
        containing them is automatically selected and they can therefore
        be used immediately.

        :param depuis:
            character from which to redefine
        :type depuis:
            a string
        :param dessins:
            designs of the characters to be redefined
        :type dessins:
            a string
        :param jeu:
            character palette to modify (G0 or G1)
        :type jeu:
            a string
        """
        assert jeu == 'G0' or jeu == 'G1'
        assert isinstance(depuis, str) and len(depuis) == 1
        assert isinstance(dessins, str)

        # Two sets are available G’0 and G’1
        if jeu == 'G0':
            self.envoyer([US, 0x23, 0x20, 0x20, 0x20, 0x42, 0x49])
        else:
            self.envoyer([US, 0x23, 0x20, 0x20, 0x20, 0x43, 0x49])

        # We indicate from which character we want to redefine the designs
        self.envoyer([US, 0x23, depuis, 0x30])

        octet = ''
        compte_pixel = 0
        for pixel in dessins:
            # Only the characters 0 and 1 are interpreted, the others are
            # ignored. This allows presenting the designs in the source code
            # in a more readable way
            if pixel != '0' and pixel != '1':
                continue

            octet = octet + pixel
            compte_pixel += 1

            # We group the character's pixels in packets of 6
            # because we can only send 6 bits at a time
            if len(octet) == 6:
                self.envoyer(0x40 + int(octet, 2))
                octet = ''

            # When 80 pixels (8 columns × 10 lines) have been sent
            # we add 4 zero bits because the sending is done in packets of 6 bits
            # (8×10 = 80 pixels, 14×6 = 84 bits, 84-80 = 4)
            if compte_pixel == 80:
                self.envoyer(0x40 + int(octet + '0000', 2))
                self.envoyer(0x30)
                octet = ''
                compte_pixel = 0

        # Positioning the cursor allows exiting the definition mode
        self.envoyer([US, 0x41, 0x41])

        # Selects the freshly modified character set (G’0 or G’1)
        if jeu == 'GO':
            self.envoyer([ESC, 0x28, 0x20, 0x42])
        else:
            self.envoyer([ESC, 0x29, 0x20, 0x43])

