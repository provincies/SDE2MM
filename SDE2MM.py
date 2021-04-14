#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ----- GEBRUIKTE SOFTWARE ---------------------------------------------
#
# python 3.7         http://www.python.org
# cx_Oracle          http://cx-oracle.sourceforge.net/
# psycopg2           http://initd.org/psycopg/docs/install.html
# pymssql            http://pymssql.org/en/latest/
#
#
# ----- GLOBALE VARIABELEN ---------------------------------------------

__doc__      = 'Programma om iso xml uit het sde schema te lezen'
__rights__   = 'provincie Noord-Brabant'
__author__   = 'Jan van Sambeek'
__date__     = ['11-2019', '04-2021']
__version__  = '1.0.5'

# ----- IMPORT LIBRARIES -----------------------------------------------

import os, sys, datetime, re, smtplib, logging, base64
import cx_Oracle
from SAMwareLib import *

# ----- REPAREERTEKST --------------------------------------------------

def repareerTekst(xmlTekst, W3Cproloog, commentaar, verwijderTags, utf8):
  """
  Repareer de Tekst
  """ 
  # verwijder begin en eind spaties
  xmlTekst = xmlTekst.strip()
  # als de tekst niet met de W3C prolog begint plaats deze aan het begin van de tekst
  if not xmlTekst.startswith(W3Cproloog): xmlTekst = W3Cproloog + '\n' + xmlTekst
  if commentaar: 
    # loop door het aantal te verwijderen commentaar regels
    for num in range(xmlTekst.count(commentaar[0])):
      # verwijder van begin commentaar[0] tot eind commentaar[1]
      xmlTekst = xmlTekst[:xmlTekst.find(commentaar[0])]+xmlTekst[xmlTekst.find(commentaar[1])+len(commentaar[1]):]
  if utf8:
    # loop door de utf8 dictionary
    for char in utf8:
      # vervang verkeerde characters als die voorkomen
      if char in xmlTekst:
        xmlTekst = xmlTekst.replace(char, utf8[char])
  # verwijder tags rondom verwijderTags
  for verwijderTag in verwijderTags:
    if verwijderTag and verwijderTag[0] in xmlTekst: 
      # zoek de linker en rechter pointer
      lpointer = xmlTekst[:xmlTekst.find(verwijderTag[0])].rfind(verwijderTag[1])
      rpointer = xmlTekst.find(verwijderTag[0]) + xmlTekst[xmlTekst.find(verwijderTag[0]):].find(verwijderTag[2]) + len(verwijderTag[2])
      # plak de tekst tot de linker pointer aan de tekst vanaf de rechter pointer
      xmlTekst = xmlTekst[:lpointer]+xmlTekst[rpointer:]
  return xmlTekst

# ----- XMLLEESBAAR ------------------------------------------------------

def xmlLeesbaar(xmlRegels, springin = 2):
  """
  Maak de tekst van de xml weer leesbaar voor de mens
  """ 
  # maak lege variabelen
  vorigeRegel = ''
  xmlTekst = ''
  spaties = 0
  regels = []
  # loop door de xml regels
  for xmlRegel in xmlRegels:
    # als '>   <' zich in de regel bevind
    if re.compile('>\s*<').search(xmlRegel):
      # vervang '>  <' door '>~<'
      splitRegels = re.compile('>\s*<').sub('>~<', xmlRegel)
      # split op de tilde
      splitRegels = splitRegels.split('~')
      # voeg een \n toe
      splitRegels = [splitRegel+'\n' for splitRegel in splitRegels]
      # voeg de splitRegels toe aan regels
      regels.extend(splitRegels)
    # voeg de xmlRegel toe aan regels  
    else: regels.append(xmlRegel)  
  # lees alle regels in
  for regel in regels:
    # lees alleen de gevulde regels
    if not re.compile('^\s*$').match(regel):
      # verwijder lege stuk begin regel
      regel = regel.lstrip()
      # verwijder spaties aan het einde van de regel
      regel = regel.rstrip(' ')
      if regel:
        # zet in het begin de spaties op 0
        if regel.startswith('<gmd:MD_Metadata') or regel.startswith('<MD_Metadata') or regel.startswith('<?xml'): spaties = 0
        # als de regel begint met een afsluit tag en de vorige regel begint met een tag
        elif regel.startswith('</') and vorigeRegel.startswith('<'): 
          # als de afsluit tag van de regel gelijk is aan de tag van de vorige regel
          if regel[2:regel.find('>')] == vorigeRegel[1:vorigeRegel.find('>')]: spaties += 0
          else: spaties += -1
        # als de vorige regel een afsluit tag is of eindigd met een afluit tag
        elif vorigeRegel.startswith('</') or vorigeRegel.endswith('/>'): spaties += 0
        # als de regel en de vorige regel starten met een tag
        elif regel.startswith('<') and vorigeRegel.startswith('<'): spaties += 1
        # als spaties door een foutje negatief zijn maak ze dan 0
        if spaties < 0 : spaties = 0
        # verzamel de regels in tekst
        xmlTekst += '%s%s' %(' '*spaties*springin, regel)
        # lees de huidige tag als vorige tag
        vorigeRegel = regel[regel.find('<') : regel.find('>')+1]
  return xmlTekst

# ----- XML SUBSTRING --------------------------------------------------

def xml_substring(xml, string):
  """
  functie om een gedeelte (bijv. Geonovum) uit een xml te selecteren
  """
  # als de zoeks string bestaat
  if xml.find(string) != -1:
    # return de substring
    return xml[xml[:xml.find(string)].rfind('<'): xml.rfind(string)+xml[xml.rfind(string):].find('>')+1]
  return ''

# ----- ZOEK TEKST ---------------------------------------
 
def zoek_tekst(xml, strings):
  """
  Return tekst uit een xml binnen 2 strings
  bijv: file_id = zoek_tekst(xml, ['fileIdentifier', 'CharacterString'])
  """
  # bepaal de linker en rechter pointer
  lpoint = xml.find(strings[0])
  lpoint += xml[xml.find(strings[0]):].find(strings[1])
  lpoint += xml[xml.find(strings[0])+xml[xml.find(strings[0]):].find(strings[1]):].find('>')+1
  rpoint = lpoint + xml[lpoint:].find('<')
  # return de tekst binnen de tags
  return xml[lpoint: rpoint]
  
# ----- HOOFD PROGRAMMA ------------------------------------------------

if __name__ == '__main__':
  """
  """
  # bepaal de start directorie en bestand
  start_dir, bestand  = os.path.split(os.path.abspath(__file__))  
  # als het eerste argument het config bestand is: bestand
  if len(sys.argv) == 2: bestand = sys.argv[1]
  # geef bestand anders dezelfde naam als het programma
  else: bestand = os.path.splitext(bestand)[0]+'.cfg'
  # maak een object van de configuratie data
  if os.path.isfile(start_dir+os.sep+bestand): cfg = Config(start_dir+os.sep+bestand)
  # verlaat anders het programma
  else: sys.exit('het configuratie bestand is niet gevonden')
  # als het configuratie bestand niet goed is verlaat het programma
  if cfg.get_dict() == None: sys.exit('er is iets niet goed met het configuratie bestand')

  # lees de directories uit
  xmlMap = cfg.get('dirs')['xmlMap']
  attrMap = cfg.get('dirs')['attrMap']
  toolsMap = cfg.get('dirs')['toolsMap']
  imageMap =  cfg.get('dirs')['imageMap']
  logMap = cfg.get('dirs')['logMap']
  # lees de W3Cproloogen uit
  W3Cproloog = cfg.get('W3Cproloog')
  # lees commentaar uit
  if cfg.get('commentaar'): commentaar = cfg.get('commentaar')
  else: commentaar = False
  # lees de te verwijderen tags uit
  if cfg.get('verwijderTags'): verwijderTags = cfg.get('verwijderTags')
  else: verwijderTags = False
  # lees de naar utf-8 om te zetten karakter (werkt alleen nog onde Linux)
  if cfg.get('utf8'): utf8 = cfg.get('utf8')
  else: utf8 = False
  # lees aantal spaties 
  aantalSpaties =  cfg.get('aantalSpaties')
  # lees de inlog gegevens uit
  inlog_geg = cfg.get('inlog_geg')
  
  # maak een log bestand
  logFile = logMap+os.sep+os.path.splitext(bestand)[0]+'.log'
  # maak een basis configuratie voor het loggen
  logging.basicConfig(filemode='a', format='%(asctime)s - %(levelname)-8s "%(message)s"', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO, filename=logFile)
  # het programma is gestart
  logging.info('-'*50)
  logging.info('%s is opgestart' %(__file__))
  logging.info('-'*50)

  # maak een leeg mail bericht
  mail_bericht = ''  
  # verwijder alle attribuut gegevens uit de attrMap
  [os.remove(attrMap+os.sep+metadata_xml) for metadata_xml in os.listdir(attrMap) if os.path.splitext(metadata_xml)[1].upper() == '.XML']
  # maak een lege list voor alle SDE metadata
  alle_SDE_Metadata = []
  # start tellers
  teller = [0, 0, 0, 0]
  # loop door de verschillende dbases
  for dbase in inlog_geg.keys():
    # lees de inlog voor gegevens voor de betreffende dbase
    if 'user' in inlog_geg[dbase]: user = inlog_geg[dbase]['user']
    if 'password' in inlog_geg[dbase]: password = inlog_geg[dbase]['password']
    if 'server' in inlog_geg[dbase]: server = inlog_geg[dbase]['server']
    if 'poort' in inlog_geg[dbase]: poort = inlog_geg[dbase]['poort']
    # maak connectie met de database
    try:
      db = cx_Oracle.connect(u'%s' %(user), u'%s' %(password), u'%s' %(dbase))
    # verlaat het programma als het niet lukt
    except foutje:
      # werk de logging bij
      logging.info('database %s geeft een foutmelding: %s' %(dbase, foutje))
      sys.exit('database %s geeft een foutmelding: %s' %(dbase, foutje))
    # werk de logging bij
    else: 
      logging.info('database %s is aangekoppeld' %(dbase))
      logging.info('database characterset: %s' %(db.encoding))
      # open een cursor
      cursor = db.cursor() 
      # select alle namen uit SDE.GDB_ITEMS
      cursor.execute(u'SELECT NAME, DOCUMENTATION FROM SDE.GDB_ITEMS')
      # loop door de resultaten
      for row in cursor.fetchall(): 
        # als er een uniek nummer is 
        if row[1]:
          # debug #
          #print(row[0])
          # selecteer de bijbehorende xml
          cursor.execute(u'SELECT sde.sdexmltotext(XML_DOC) FROM SDE.SDE_XML_DOC2 WHERE SDE_XML_ID=%d' %(row[1]))
          # lees de resultaten uit de xml
          SDE_xml = cursor.fetchone()[0].read()  #.decode(db.encoding, 'replace')
          # als de xml niet leeg is
          if not SDE_xml: logging.info('Metadata tabel: %s is niet aanwezig' %(row[0]))
          # bepaal of de xml een "ISO" xml is 
          if ('ISO 19115' in SDE_xml or 'ISO 19119' in SDE_xml) and '>dut<' in SDE_xml:
            # plaats de xml naam in alle_SDE_Metadata
            alle_SDE_Metadata.append(row[0])
            # lees de attribute gegevens
            ATTR_xml = xml_substring(SDE_xml, 'FC_FeatureCatalogue')
            ATTR_xml += xml_substring(SDE_xml, 'eainfo')
            # als het bestand nog niet bestaat
            if not os.path.isfile('%s%s%s_ATTR.xml' %(attrMap, os.sep, row[0])):
              # als ATTR_xml niet leeg is
              if ATTR_xml:
                # schrijf de attribuut gegevens weg
                with open('%s%s%s_ATTR.xml' %(attrMap, os.sep, row[0]), 'wb') as xml_best: xml_best.write(ATTR_xml.encode())
            # lees de tool gegevens
            tool_xml = xml_substring(SDE_xml, 'ToolSource')
            # als het bestand nog niet bestaat
            if not os.path.isfile('%s%s%s_tool.xml' %(toolsMap, os.sep, row[0])):
              # als tool_xml niet leeg is
              if tool_xml:
                # schrijf de tool gegevens weg
                with open('%s%s%s_tool.xml' %(toolsMap, os.sep, row[0]), 'wb') as xml_best: xml_best.write(tool_xml.encode())
            # lees de thumbnail uit en sla die op
            jpeg = zoek_tekst(SDE_xml, ['Thumbnail', 'Data'])
            # als de jpeg niet leeg is
            if len(jpeg) > 0:
              # als het bestand nog niet bestaat
              if not os.path.isfile('%s%s%s.jpg' %(imageMap, os.sep, row[0])):
                with open('%s%s%s.jpg' %(imageMap, os.sep, row[0]), 'wb') as xml_best: xml_best.write(base64.decodebytes(jpeg.encode()))
            # selecteer alleen de metadata tussen de tags MD_Metadata
            SDE_xml = xml_substring(SDE_xml, 'MD_Metadata')
            # kijk of de metadata al in de MM aanwezig is
            if os.path.isfile(('%s%s%s.xml' %(xmlMap, os.sep, row[0]))):
              # open dan de MM_xml
              with open('%s%s%s.xml' %(xmlMap, os.sep, row[0]), 'rb') as xml_best: MM_xml = xml_best.read().decode()
              # lees de wijzingings datum van de metadata uit
              MM_metadata_datum = zoek_tekst(MM_xml, ['dateStamp', 'Date'])   
              #lees de wijzingings datum van de metadata uit
              SDE_metadata_datum = zoek_tekst(SDE_xml, ['dateStamp', 'Date'])       
              # als er een nieuwere datum is vervang de xml
              if SDE_metadata_datum > MM_metadata_datum:
				# repareer de tekst
                xmlTekst = repareerTekst(SDE_xml, W3Cproloog, commentaar, verwijderTags, utf8)  
                # sla de gegevens op
                with open('%s%s%s.xml' %(xmlMap, os.sep, row[0]), 'wb') as  fileObject: fileObject.write(SDE_xml.encode('utf-8'))
                # open de regels van het bestand en verwijder de lege regels
                with open('%s%s%s.xml' %(xmlMap, os.sep, row[0]), 'r', encoding='utf-8') as fileObject: xmlLines = [line for line in fileObject.readlines() if line.strip()]
                # sla de leesbaar gemaakte tekst op
                with open('%s%s%s.xml' %(xmlMap, os.sep, row[0]), 'wb') as fileObject: fileObject.write(xmlLeesbaar(xmlLines, aantalSpaties).encode('utf-8')) 
                teller[0] += 1
                logging.info('Bestand (%s): %s%s%s.xml is vervangen' %(dbase, xmlMap, os.sep, row[0]))
                mail_bericht += 'Bestand (%s): %s%s%s.xml is vervangen\n' %(dbase, xmlMap, os.sep, row[0])
            # als de metadata nog niet bestaat schrijf die dan weg
            else:
              # repareer de tekst
              xmlTekst = repareerTekst(SDE_xml, W3Cproloog, commentaar, verwijderTags, utf8)  
              # sla de gegevens op
              with open('%s%s%s.xml' %(xmlMap, os.sep, row[0]), 'wb') as  fileObject: fileObject.write(SDE_xml.encode('utf-8'))
              # open de regels van het bestand en verwijder de lege regels
              with open('%s%s%s.xml' %(xmlMap, os.sep, row[0]), 'r', encoding='utf-8') as fileObject: xmlLines = [line for line in fileObject.readlines() if line.strip()]
              # sla de leesbaar gemaakte tekst op
              with open('%s%s%s.xml' %(xmlMap, os.sep, row[0]), 'wb') as fileObject: fileObject.write(xmlLeesbaar(xmlLines, aantalSpaties).encode('utf-8'))
              teller[1] += 1
              logging.info('Bestand (%s): %s%s%s.xml is toegevoegd' %(dbase, xmlMap, os.sep, row[0]))
              mail_bericht += 'Bestand (%s): %s%s%s.xml is toegevoegd\n' %(dbase, xmlMap, os.sep, row[0])
          # geef aan dat de xml geen iso profiel heeft      
          else: 
            teller[2] += 1
            logging.info('XML: %s voldoet niet aan het ISO_profiel' %(row[0]))
            mail_bericht += 'XML: %s voldoet niet aan het ISO_profiel\n' %(row[0])
      # sluit de database
      cursor.close()
      db.close()
  # loop door alle bestanden (zonder .xml) in de xmlMap
  for xml_bestand, extensie in [[os.path.splitext(xml_bestand)[0], os.path.splitext(xml_bestand)[1]] for xml_bestand in os.listdir(xmlMap)]:
    # als het bestand niet voorkomt in alle SDE Metadata, verwijder het dan
    if xml_bestand not in alle_SDE_Metadata and extensie == '.xml': 
      os.remove('%s%s%s%s' %(xmlMap, os.sep, xml_bestand, extensie))
      logging.info('Bestand: %s%s%s%s is verwijderd' %(xmlMap, os.sep, xml_bestand, extensie))
      mail_bericht += 'Bestand: %s%s%s%s is verwijderd\n' %(xmlMap, os.sep, xml_bestand, extensie)
      teller[3] += 1      
  # sluit de logging af met de aantallen verwerkte bestanden
  logging.info('')
  logging.info('Aantal vervangen xml bestanden:  %s' %(teller[0]))
  logging.info('Aantal toegevoegde xml bestanden:  %s' %(teller[1]))
  logging.info('Metadata die niet voldoet aan het ISO_profiel:  %s' %(teller[2]))
  logging.info('Aantal verwijderde xml bestanden:  %s' %(teller[3]))
  logging.info('')
  # als er iets veranderd is stuur dan een mail naar de beheerders
  if mail_bericht:
    # geef de totalen van de aangepaste bestanden
    mail_bericht += '\n\nAantal vervangen xml bestanden:  %s' %(teller[0])
    mail_bericht += '\nAantal toegevoegde xml bestanden:  %s' %(teller[1])
    mail_bericht += '\nMetadata die niet voldoet aan het ISO_profiel:  %s' %(teller[2])
    mail_bericht += '\nAantal verwijderde xml bestanden:  %s' %(teller[3])
    # lees de gegevens uit
    mail_gegevens = cfg.get('mail_gegevens')
    # vul de gegevens aan
    mail_gegevens['onderwerp'] = 'Bestand: %s is uitgevoerd' %(os.path.splitext(bestand)[0]) 
    bericht = 'Beste beheerder, \n\n\n' 
    bericht += 'Bij de verwerking van: %s zijn de volgende wijzigingen aangebracht:\n\n' %(os.path.splitext(bestand)[0])
    bericht += '%s\n\n\n' %(mail_bericht)
    bericht += '%s\n' %(mail_gegevens['bericht_naam'])
    bericht += '%s\n' %(mail_gegevens['bericht_org'])
    bericht += '%s\n' %(mail_gegevens['bericht_email'])
    bericht += '%s\n' %(mail_gegevens['bericht_post'])
    bericht += '%s  %s\n\n' %(mail_gegevens['bericht_postcode'], mail_gegevens['bericht_plaats'])
    bericht += '%s' %(mail_gegevens['bericht_www'])
    mail_gegevens['bericht'] = bericht
    # verstuur de gegevens
    zendMail(mail_gegevens)
  # beperk de omvang van de log file
  beperkLogFile(logFile)         

# ----- EINDE PROGRAMMA ------------------------------------------------
