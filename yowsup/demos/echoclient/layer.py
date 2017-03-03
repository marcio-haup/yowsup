from yowsup.layers.interface                           import YowInterfaceLayer, ProtocolEntityCallback
import sys
from yowsup.common import YowConstants
import datetime
import os
import logging
import os.path
import requests
import json
from pprint import pprint
from yowsup.layers.protocol_groups.protocolentities      import *
from yowsup.layers.protocol_presence.protocolentities    import *
from yowsup.layers.protocol_messages.protocolentities    import *
from yowsup.layers.protocol_ib.protocolentities          import *
from yowsup.layers.protocol_iq.protocolentities          import *
from yowsup.layers.protocol_contacts.protocolentities    import *
from yowsup.layers.protocol_chatstate.protocolentities   import *
from yowsup.layers.protocol_privacy.protocolentities     import *
from yowsup.layers.protocol_media.protocolentities       import *
from yowsup.layers.protocol_media.mediauploader import MediaUploader
from yowsup.layers.protocol_profiles.protocolentities    import *
from yowsup.common.tools import Jid
from yowsup.common.optionalmodules import PILOptionalModule, AxolotlOptionalModule

class EchoLayer(YowInterfaceLayer):

    def __init__(self):
        # super(YowsupCliLayer, self).__init__()
        YowInterfaceLayer.__init__(self)
        # self.accountDelWarnings = 0
        # self.connected = False
        # self.username = None
        self.sendReceipts = True
        self.sendRead = True
        # self.disconnectAction = self.__class__.DISCONNECT_ACTION_PROMPT
        # self.credentials = None

        #add aliases to make it user to use commands. for example you can then do:
        # /message send foobar "HI"
        # and then it will get automaticlaly mapped to foobar's jid
        self.jidAliases = {
            # "NAME": "PHONE@s.whatsapp.net"
        }


    def aliasToJid(self, calias):
        for alias, ajid in self.jidAliases.items():
            if calias.lower() == alias.lower():
                return Jid.normalize(ajid)

        return Jid.normalize(calias)

    def jidToAlias(self, jid):
        for alias, ajid in self.jidAliases.items():
            if ajid == jid:
                return alias
        return jid

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):

        if messageProtocolEntity.getType() == 'text':
            self.onTextMessage(messageProtocolEntity)
        elif messageProtocolEntity.getType() == 'media':
            self.onMediaMessage(messageProtocolEntity)

        # self.toLower(messageProtocolEntity.forward(messageProtocolEntity.getFrom()))
        self.toLower(messageProtocolEntity.ack())
        self.toLower(messageProtocolEntity.ack(True))


    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        self.toLower(entity.ack())

    def onTextMessage(self,messageProtocolEntity):
        # just print info
        # print("Echoing %s to %s" % (messageProtocolEntity.getBody(), messageProtocolEntity.getFrom(False)))
        url = "http://localhost/robert/index.php"
        params = dict(
            acao='mensagem',
            participante=messageProtocolEntity.getParticipant(),
            autor=messageProtocolEntity.getAuthor(),
            alvo=messageProtocolEntity.getFrom(),
            mensagemDeGrupo=messageProtocolEntity.isGroupMessage(),
            mensagem=messageProtocolEntity.getBody(),
        )
        resp = requests.get(url=url, params=params)
        data = json.loads(resp.text)

        self.processaRetornoRobert(data)

    def onMediaMessage(self, messageProtocolEntity):
        # just print info
        if messageProtocolEntity.getMediaType() == "image":
            print("Echoing image %s to %s" % (messageProtocolEntity.url, messageProtocolEntity.getFrom(False)))

        elif messageProtocolEntity.getMediaType() == "location":
            print("Echoing location (%s, %s) to %s" % (messageProtocolEntity.getLatitude(), messageProtocolEntity.getLongitude(), messageProtocolEntity.getFrom(False)))

        elif messageProtocolEntity.getMediaType() == "vcard":
            print("Echoing vcard (%s, %s) to %s" % (messageProtocolEntity.getName(), messageProtocolEntity.getCardData(), messageProtocolEntity.getFrom(False)))

    @ProtocolEntityCallback("notification")
    def onNotification(self, notification):
        notificationData = notification.__str__()

        participante = notification.getParticipant()
        alvo = notification.getFrom()
        tipo = notification.getType()
        try:
            setBy = notification.getSubjectOwner()
        except AttributeError:
            setBy = ''
	
	try:
            titulo = notification.getSubject()
	except AttributeError:
            titulo = ''

        url = "http://localhost/robert/index.php"
        params = dict(
            acao='notificacao',
            tipo=tipo,
            alvo=alvo,
            participante=participante,
            alteradoPor=setBy,
            titulo=titulo
        )
        resp = requests.get(url=url, params=params)
        data = json.loads(resp.text)

        self.processaRetornoRobert(data)

        if self.sendReceipts:
            self.toLower(notification.ack())

    def processaRetornoRobert(self, data):
        if data['sucesso'] == 1:
            for retorno in data['retornos']:
                if retorno['acao'] == 'enviarMensagem':
                    content = retorno['mensagem']
                    destino = retorno['destino']
                    outgoingMessage = TextMessageProtocolEntity(content.encode("utf-8") if sys.version_info >= (3,0) else content, to = self.aliasToJid(destino))
                    self.toLower(outgoingMessage)

                if retorno['acao'] == 'trocarNomeGrupo':
                    print "trocarNomeGrupo para %s" % retorno['nome']
                    entity = SubjectGroupsIqProtocolEntity(self.aliasToJid(retorno['grupoId']), retorno['nome'])
                    self.toLower(entity)
