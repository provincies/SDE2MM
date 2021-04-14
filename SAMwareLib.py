#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ----- GEBRUIKTE SOFTWARE ---------------------------------------------
#
# python-3.7         https://www.python.org/downloads/release/python-376/
#
#
# ----- GLOBALE VARIABELEN ---------------------------------------------

__doc__      = '''
               Librarie met diverse gemeenschappelijke classes en functies:
               - config: Class om configuratie bestanden uit te lezen/schrijven
               - zendMail: Fundie om mail met bijlagen te versturen naar één of meerder ontvangers.
               - beperkLogFile: Functie om de grootte van de log file te beperken
 
                '''
__rights__   = 'Jan van Sambeek'
__author__   = 'Jan van Sambeek'
__license__  = 'GNU Lesser General Public License, version 3 (LGPL-3.0)'
__date__     = '03-2021'
__version__  = '1.0'

# ----- IMPORT LIBRARIES -----------------------------------------------

import os, sys, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ----- CONFIG CLASS ---------------------------------------------------

class Config:
  """
  Lees config bestand en haal key's op
  Schrijf dictionarie naar config
  """
  def __init__(self, conf_bestand):
    """ ini config object """
    self.conf_bestand = conf_bestand
    self.conf = None

  def get(self, key, default = None):
    """ Lees values uit config bestand """
    if not self.conf: self.load()
    if self.conf and (key in self.conf): return self.conf[key]
    return default

  def get_dict(self, default = None):
    """ Geef de complete dictionarie """
    if not self.conf: self.load()
    if self.conf: return self.conf
    return default

  def set(self, key, value):
    """ Voeg keys en values toe aan config """
    if not self.conf: self.load()
    self.conf[key] = value
    self.save()

  def load(self):
    """
    Laad het config bestand
    Als het niet bestaat maak een lege config
    """
    try: self.conf = eval(open(self.conf_bestand, 'r').read())
    except: self.conf = {}

  def save(self):
    """ Schijf dictionarie naar config bestand """
    open(self.conf_bestand, 'w').write(repr(self.conf))

# ----- ZENDMAIL -------------------------------------------------------

def zendMail(mail_gegevens, SSL=True):
  """
  Functie zendMail(mail_gegevens, SSL=False)

  Is een programma om mail met bijlagen te versturen naar één of meerder ontvangers.
  De mail gegevens bestaan uit, een dictionarie met daarin:
  verzender, wachtwoord, alias, ontvangers, cc, bc,  onderwerp, bericht, de smtp_server en eventueel bijlagen.
  Ontvangers, cc, bc en bijlagen zijn lists, alle overige variabelen zijn strings.
  verplicht: verzender, ontvangers, onderwerp, bericht, de smtp_server
  optioneel: wachtwoord, alias, cc, bc, bijlagen
  Afhankelijk van de provider kan een SSL beveiliging meegegeven worden
  door SSL=True of SSL=False bij het oproepen van de functie mee te geven.


  voorbeeld:

  mail_gegevens = {}
  mail_gegevens['verzender']  = 'verzender@gmail.com'
  mail_gegevens['wachtwoord'] = '********'
  mail_gegevens['alias']      = 'alias verzender'
  mail_gegevens['ontvangers'] = ['ontvanger1@gmail.com', 'ontvanger2@gmail.com']
  mail_gegevens['cc']         = ['cc1@gmail.com, 'cc2@gmail.com']
  mail_gegevens['bc']         = ['bc1@gmail.com, 'bc2@gmail.com']
  mail_gegevens['onderwerp']  = 'onderwerp van de mail'
  mail_gegevens['bericht']    = 'bericht van de mail'
  mail_gegevens['smtp_server']= 'smtp.gmail.com'
  mail_gegevens['bijlagen']   = ['bijlage1.pdf', 'bijlage2.jpg']

  Zendmail(mail_gegevens, SSL=True)
  """
  # stel het bericht samen
  message = MIMEMultipart()
  # kijk of er een alias is anders gebruik de verzender
  if 'alias' in mail_gegevens.keys(): message['From'] = mail_gegevens['alias']
  else: message['From'] = mail_gegevens['verzender']
  # voeg de ontvangers toe aan de message
  message['To'] =  ', '.join(mail_gegevens['ontvangers'])
  # voeg de ontvangers toe aan ontvangers
  ontvangers = mail_gegevens['ontvangers']
  # als er cc's zijn voeg die toe
  if 'cc' in mail_gegevens.keys():
    message['CC'] =  ', '.join(mail_gegevens['cc'])
    ontvangers += mail_gegevens['cc']
  # als er bc's zijn voeg die toe
  if 'bc' in mail_gegevens.keys():
    message['BC'] =  ', '.join(mail_gegevens['bc'])
    ontvangers += mail_gegevens['bc']
  # voeg het onderwerp toe
  message['Subject'] = mail_gegevens['onderwerp']
  # voeg het bericht toe
  message.attach(MIMEText(mail_gegevens['bericht'], 'plain'))
  # als er bijlagen zijn voeg ze dan toe
  if 'bijlagen' in mail_gegevens.keys():
    # loop door alle bijlagen
    for mail_best in mail_gegevens['bijlagen']:
      bijlage = MIMEBase('application', "octet-stream")
      bijlage.set_payload(open(mail_best,"rb").read())
      encoders.encode_base64(bijlage)
      bijlage.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(mail_best))
      # voeg de bijlage toe
      message.attach(bijlage)
  # maak een beveiligde of onbeveiligde verbinding met de smtp server
  if SSL: smtp = smtplib.SMTP_SSL(mail_gegevens['smtp_server'])
  else: smtp = smtplib.SMTP(mail_gegevens['smtp_server'])
  # zet het debuglevel op false
  smtp.set_debuglevel(False)
  # login bij de smtp server
  if 'wachtwoord' in mail_gegevens.keys():
    smtp.login(mail_gegevens['verzender'], mail_gegevens['wachtwoord'].decode('base64','strict'))
  # verzend de totale mail
  smtp.sendmail(mail_gegevens['verzender'], ontvangers, message.as_string())
  # stop het object
  smtp.quit()
  return

# ----- BEPERKLOGFILE ------------------------------------------------

def beperkLogFile(logFile, maxRegels = 1000):
  """
  Als een log bestand te groot wordt verwijder dan de eerste regels
  """
  # open de log file
  with open(logFile, 'r') as fileObject: logRegels = fileObject.readlines()
  # als de log file langer is als het maximum aantal regels
  if len(logRegels) > maxRegels:
    # overschrijf de log met het maximum aantal regels
    with open(logFile, 'w') as fileObject: logRegels = fileObject.writelines(logRegels[-maxRegels:])
  return

# ----------------------------------------------------------------------
