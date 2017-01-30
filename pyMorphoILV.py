#!/usr/bin/env python
# -*- coding: utf-8 -*-

import usb.core
import usb.util
import usb.control

import array
import atexit

from threading import Thread
import threading

class Morpho(object):
  def __init__(self, vendID=0x079b, prodID=0x0024, baudrate=38400, endPOut=0x02, endPIn = 0x83):
    print "Inicializando instancia Morpho Reader"
    # Look for a specific device and open it
    dev = usb.core.find(idVendor=vendID, idProduct=prodID) # Morpho Bio Reader
    if dev is None:
      raise ValueError('Device not found')

    # Detach interfaces if Linux already attached a driver on it.
    for itf_num in [0, 1]:
      itf = usb.util.find_descriptor(dev.get_active_configuration(),
                                  bInterfaceNumber=itf_num)
      if dev.is_kernel_driver_active(itf):
          dev.detach_kernel_driver(itf)
      usb.util.claim_interface(dev, itf)


    # set control line state 0x2221
    # set line encoding 0x2021 (baudrate, 8N1)
    #
    extra = array.array('B', [0x00, 0x00, 0x08])
    baud = self.int2array(baudrate)
    baud.extend(extra)

    dev.ctrl_transfer(0x21, 0x22, 0x01 | 0x02, 0, None)
    dev.ctrl_transfer(0x21, 0x20, 0, 0, baud)

    self.lector = dev
    self.endPOut = endPOut
    self.endPIn  = endPIn
    self.ILVCommand = 0x00
    atexit.register(self.exit_handler)

  def sendILV(self, data):
# Enviar SYNC
    payload = headerData = bytearray(B"SYNC");

# Enviar tamaño de datos y complemento a 2
    dataSize = len(data);
    cDataSize = -(dataSize+1);
    payload.extend(self.int2array(dataSize))
    payload.extend(self.int2array(cDataSize))
# Enviar comando
    payload.extend(data);
# Enviar terminación
    tailData = bytearray("EN");
    payload.extend(tailData)

    self.lector.write(self.endPOut, payload, interface = 1)
#    print "Enviando: ", ":".join("{:02x}".format(c,'02x') for c in payload)

  def startRead(self, q):
    readThread = Thread(target=self.read, args=(q,))
    readThread.start()
    self.readThread = readThread

  def read(self, out_q):
    t = threading.currentThread()
    serialReading = False
    serialErrorReported = False
    while getattr(t, "do_run", True):
      try:
        data = self.lector.read(self.endPIn, 1024, interface = 1)
#          print 'Back: "%s"' % ":".join("{:02x}".format(c) for c in data)
        if not serialReading: #No estabamos leyendo, iniciar lectura en buffer
          if len(data) < 6:
            out_q.put({'status':'Error','data':'Error de comunicación con lector biometrico'})
	    continue
          if data[0] == 0x53 and data[1] == 0x59 and data[2] == 0x4E and data[3] == 0x43: #Si viene el header iniciamos la lectura
#	    print "'SYNC' encontrado"
            if data[-1]==0x4E and data[-2]==0x45: #Si viene el final leimos el chunk completo
#              print "Todo en un paquete ... Terminamos";
              out_q.put(self.processILV(data, len(data), 12))
            else: #Si no, iniciamos la lectura
#              print "Inicializando el buffer"
              serialData    = data
              serialReading = True
            serialErrorReported = False
          else:
            if not serialErrorReported :
              out_q.put({'status':'Error','data':"No se encontro 'SYNC'"})
              serialErrorReported = True
        else:
          serialData.extend(data)
          if data[-1]==0x4E and data[-2]==0x45: # Si viene el final terminamos de leer el chunk completo
 #           print "Fin lectura";
            out_q.put(self.processILV(serialData, len(serialData), 12))
            serialReading = False
      except usb.core.USBError as e:
        pass
#        print e
    print("Morpho Reading Stopped.")


# Commandos
  def getInfo(self):
    data = array.array('B', [0x05, 0x01, 0x00, 0x2F])
    self.sendILV(data)

  def getImage(self):

    longitud	= 8+7+9+4
    base        = 0x00
    espera      = 0x07
    calidad     = 0x00
    pasadas     = 0x01
    dedos       = 0x01
    guardar     = 0x00
    tamano      = 0x00

# Image
    data = array.array('B', [0x21])
    data.extend(self.short2array(longitud))
    data.extend(array.array('B',[base]))
    data.extend(self.short2array(espera))
    data.extend(array.array('B',[calidad, pasadas, dedos, guardar, tamano]))
# ILV de Asynchronous event
    idEvent	= 0x34 #ID_ASYNCHRONOUS_EVENT
    size	= 4
    command	= 0x03 #(COMMAND) | (IMAGE) // | ¿(CODE_QUALITY)?

    data.extend(array.array('B',[idEvent]))
    data.extend(self.short2array(size))
    data.extend(array.array('B',[command, 0x00, 0x00, 0x00]))

# ILV de Export Image
    idEvent	= 0x3D #ID_EXPORT_IMAGE
    size	= 6
    imageType	= 0x00 #ID_DEFAULT_IMAGE
    
    data.extend(array.array('B',[idEvent]))
    data.extend(self.short2array(size))
    data.extend(array.array('B',[imageType]))
    #ILV de compresión
    idEvent	= 0x3E #ID_COMPRESSION 
    size	= 2
    command	= 0x2C #ID_COMPRESSION_NULL
    data.extend(array.array('B',[idEvent]))
    data.extend(self.short2array(size))
    data.extend(array.array('B',[command, 0x00]))

# ILV de Huella latente
    idEvent	= 0x39 #ID_LATENT_SETTING
    size	= 1
    command	= 0x01 #ENABLED
    data.extend(array.array('B',[idEvent]))
    data.extend(self.short2array(size))
    data.extend(array.array('B',[command]))
    self.sendILV(data)

  def createDB(self):    #TODO
    longitud          = 5;
    maximoRegistros   = 100;

    data = array.array('B', [0x30])
    data.extend(self.short2array(longitud))
    data.extend(array.array('B',[0x00, 0x00]))
    data.extend(self.short2array(maximoRegistros))
    data.extend(array.array('B',[0x02]))
    self.sendILV(data);

  def borrarDB(self):    #TODO
    data = array.array('B', [0x33, 0x01, 0x00, 0x00])
    self.sendILV(data);

# Helpers
  def int2array(self, i):
    return [i >> n & 0xff for n in (0,8,16,24)]

  def short2array(self, i):
    return [i >> n & 0xff for n in (0,8)]



#Misc / closing
  def exit_handler(self):
    self.close()
  def close(self):
    if hasattr(self, 'readThread'):
      print "Terminando Hilo"
      self.readThread.do_run = False
      self.readThread.join()
      del(self.readThread)
    usb.util.dispose_resources(self.lector)
    
  def processILV(self, buffer, size, offset):
    ILV_OK 		= 0x00
    ILVERR_CMDE_ABORTED	= 0xE5;
    
    ILVSTS_OK		= 0x00;
    ILVSTS_HIT		= 0x01;
    ILVSTS_NO_HIT	= 0x02;
    ILVSTS_DB_FULL	= 0x04;
    ILVSTS_DB_EMPTY	= 0x05;
    ILVSTS_FFD		= 0x22;
    ILVSTS_MOIST_FINGER	= 0x23;

    if buffer[offset] == 0x50:
      print "Comando ILV invalido"
    else:
      code = buffer[offset];
      longitud = (buffer[offset+1]&0xFF) + ((buffer[offset+2]<<8)&0xFF00);
      if longitud==65535: # Mensaje con longitud mayor, usar 4 bytes
        offset+=2
	longitud = (buffer[offset+1]&0xFF) + ((buffer[offset+2]<<8)&0xFF00) + ((buffer[offset+3]<<16)&0xFF0000) + ((buffer[offset+4]<<24)&0xFF000000)
	offset+=2
#      print "Longitud de comando ILV = ", str(longitud)
      status = 0xFF
      if longitud>0:
        status = buffer[offset+3]
      if code == 0x71: # Comando de "Asynchronous Message"
        if status != ILV_OK:
	  return {'status':'Error', 'data':'Mensaje asincrono con error'}
        self.ILVCommand = code;
        if longitud>6:
          return self.processILV(buffer, size, offset+4)
#      print "code:", str(code)
      # Ejecutamos cuando ya se cargo ILVCommand en iteración anterior
      if self.ILVCommand == 0x71: # Mensaje asincrono
#        print "Mensaje asincrono2"
        self.ILVCommand = code;
        if   code == 0x01: # Mensaje de control
          pass
        elif code == 0x02: # Mensaje imagen asincrona
          return {'status':'huella', 'data': self.processImage(buffer, offset)}
	else:
          print "Mensaje asincrono desconocido"
        return;
      if code == 0x22: # Comando de identificacion
        if status != ILV_OK:
          print "Codig error %d" % status
	  if status != ILVERR_CMDE_ABORTED:
            print "Error del dispositivo biometrico, intente de nuevo"
          return;
        if buffer[offset+4]==ILVSTS_HIT:
          dbIdx = buffer[offset+5]+(buffer[offset+6]<<8)+(buffer[offset+7]<<16)+(buffer[offset+8]<<24)
          print "Usuario identificado"
          ILVCommand = code
          if longitud>6:
            self.processILV(buffer, size, offset+9)
        else:
          print "Usuario No identificado"
        return
      if code == 0x21: # Comando de enrolado
        ILVCommand = code
        if status != ILV_OK:
          print "Codig error %d" % status
          if status != ILVERR_CMDE_ABORTED:
            print "Error del dispositivo biometrico, intente de nuevo"
	  return
        if buffer[offset+4]==ILVSTS_OK:
          dbIdx = buffer[offset+5]+(buffer[offset+6]<<8)+(buffer[offset+7]<<16)+(buffer[offset+8]<<24)
#          print "Usuario enrolado correctamente"
          ILVCommand = code
          if longitud>6:
            return self.processILV(buffer, size, offset+9)
        else:
          print "Usuario No enrolado, intentar nuevamente"
	return
      if code == 0x3d: # Comando de imagen
        ILVCommand = code
#        print "Recibimos huella final"
        return {'status':'huellaf', 'data': self.processImage(buffer, offset)}
  '''
				
/*				if(status != ILV_OK){
					hRefresh.sendEmptyMessage(GUI_ENROL_FREE_ERROR);
					Log.v("PFfingerScan","Codigo de respuesta: "+Integer.toHexString(0xFF & status));
					if(status != ILVERR_CMDE_ABORTED)mostrarMensaje("Error del dispositivo biometrico, intente de nuevo");
					return;
				}
				if(buffer[offset+4]==ILVSTS_OK){
					hRefresh.sendEmptyMessage(GUI_ENROL_FREE);
					int dbIdx = buffer[offset+5]+(buffer[offset+6]<<8)+(buffer[offset+7]<<16)+(buffer[offset+8]<<24);
					Log.v("PFfingerScan","Usuario enrolado correctamente");
					ILVCommand = code;
					if(longitud>6)processILV(buffer, size, offset+9);
				}else{
					hRefresh.sendEmptyMessage(GUI_ENROL_FREE_ERROR);
					Log.v("PFfingerScan","Usuario No enrolado");
					mostrarMensaje("No enrolado, intente nuevamente");
//					mostrarResultadoHuella(false,"");
				}
*/
				return;
			}
			if(code == 0x04){ // ID de usuario
				int userID=0; //Los Ids los manejare numericos
				for(int i=(int)longitud; i>0; i--){
					userID=(userID<<8)+(((short)buffer[offset+2+i])&0xFF);
				}

				if(runningOP == OP_ENROLAR){
					if(userID == 50649){ //TODO: arreglar QD
						hRefresh.sendEmptyMessage(GUI_ADMIN_FREE);
						adminLoged = true;
					}else{
						mostrarMensaje("Usuario sin privilegios");
						hRefresh.sendEmptyMessage(GUI_MAIN_FREE);
						return;
					}
				}else{
			        Map<String, Object> params = new HashMap<String, Object>();
			        params.put("Pi_expediente", userID);
			        params.put("Pi_evento", runningOP);
			        params.put("Pi_ubicacion", 1);
			        try{
			        	RespuestaSiNo respuesta = servicio.llamarServicioSiNo("registrarEvento", params);
			        	Log.v("PFfingerScan","Respuesta registro evento: " + respuesta.respuesta);
			        }catch (Exception e) {
						// TODO: handle exception
					}
			        hRefresh.sendEmptyMessage(GUI_MAIN_FREE);
				}
				mostrarResultadoHuella(true,""+userID);
				Log.v("PFfingerScan", userID +" identificado correctamente");
//				mostrarMensaje(userID +" identificado correctamente");
				return;
			}
		}
	}
  '''
  def processImage(self, buffer, offset):
    headerSize		= buffer[offset+4]; # Debe ser 0x0A
    rowNumber		= (buffer[offset+5]&0xFF) + ((buffer[offset+6]<<8)&0xFF00)
    colNumber		= (buffer[offset+7]&0xFF) + ((buffer[offset+8]<<8)&0xFF00)
    vertRes		= (buffer[offset+9]&0xFF) + ((buffer[offset+10]<<8)&0xFF00)
    horzRes		= (buffer[offset+11]&0xFF) + ((buffer[offset+12]<<8)&0xFF00)
    compression		= buffer[offset+13]
    compressionParam 	= buffer[offset+14]
    imgSize		= rowNumber*colNumber
    offset+=15
#    print "----Datos imagen---- \nrowNumber: %d \ncolNumber: %d \nvertRes: %d \nhorzRes: %d \n%d \n%d" % (rowNumber, colNumber, vertRes, horzRes, compression, compressionParam)
    huella = buffer[offset:offset+imgSize]
    return {'rowNumber':rowNumber, 'colNumber':colNumber, 'huella':huella}

