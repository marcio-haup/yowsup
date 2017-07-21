from yowsup.layers.interface                           import YowInterfaceLayer, ProtocolEntityCallback
import sys
from yowsup.common import YowConstants
import datetime
import os
import logging
import os.path
import requests
import json
import base64
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

    FAIL_OPT_PILLOW         = "No PIL library installed, try install pillow"
    FAIL_OPT_AXOLOTL        = "axolotl is not installed, try install python-axolotl"

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
        params = {
            'acao':'mensagem',
            'participante':messageProtocolEntity.getParticipant(),
            'autor':messageProtocolEntity.getAuthor(),
            'alvo':messageProtocolEntity.getFrom(),
            'mensagemDeGrupo':messageProtocolEntity.isGroupMessage(),
            'mensagem':messageProtocolEntity.getBody(),
#            novo=base64.b64encode(messageProtocolEntity.getBody().encode('utf-8'))
        }
#        resp = requests.get(url=url, params=params)
        resp = requests.post(url, data=params)

	try:
            data = json.loads(resp.text)
            self.processaRetornoRobert(data)
	except ValueError, e:
	    data = ''


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

        try:
            participante = notification.getParticipant()
        except AttributeError:
            participante = ''

        try:
            tipo = notification.getType()
        except AttributeError:
            tipo = ''

        try:
            alvo = notification.getFrom()
        except AttributeError:
            alvo = ''
        
        try:
            setBy = notification.getSubjectOwner()
        except AttributeError:
            setBy = ''

        try:
            titulo = notification.getSubject()
        except AttributeError:
            titulo = ''

        try:
            notify = notification.getNotify()
        except AttributeError:
            notify = ''

        url = "http://localhost/robert/index.php"
        params = dict(
            acao='notificacao',
            classType=type(notification),
            tipo=tipo,
            alvo=alvo,
            participante=participante,
            alteradoPor=setBy,
            titulo=titulo,
            notify=notify,
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

                if retorno['acao'] == 'trocarImagemGrupo':
                    print "trocarImagemGrupo para %s" % retorno['path']
                    self.group_picture(retorno['grupoId'], retorno['path'])

                if retorno['acao'] == 'removerParticipante':
                    print "removerParticipante %s do grupo %s" % (retorno['participante'], retorno['grupoId'])
                    entity = RemoveParticipantsIqProtocolEntity(self.aliasToJid(retorno['grupoId']), [self.aliasToJid(retorno['participante'])])
                    self.toLower(entity)

    def group_picture(self, group_jid, path):
        with PILOptionalModule(failMessage = self.__class__.FAIL_OPT_PILLOW) as imp:
            Image = imp("Image")

            def onSuccess(resultIqEntity, originalIqEntity):
                print "Group picture updated successfully"

            def onError(errorIqEntity, originalIqEntity):
                print "Error updating Group picture"

            #example by @aesedepece in https://github.com/tgalal/yowsup/pull/781
            #modified to support python3
            src = Image.open(path)
            pictureData = src.resize((640, 640)).tobytes("jpeg", "RGB")
            picturePreview = src.resize((96, 96)).tobytes("jpeg", "RGB")
            iq = SetPictureIqProtocolEntity(self.aliasToJid(group_jid), picturePreview, pictureData)
            self._sendIq(iq, onSuccess, onError)

    def media_send(self, number, path, mediaType, caption = None):
        jid = self.aliasToJid(number)
        entity = RequestUploadIqProtocolEntity(mediaType, filePath=path)
        successFn = lambda successEntity, originalEntity: self.onRequestUploadResult(jid, mediaType, path, successEntity, originalEntity, caption)
        errorFn = lambda errorEntity, originalEntity: self.onRequestUploadError(jid, path, errorEntity, originalEntity)
        self._sendIq(entity, successFn, errorFn)

        self._sendIq(entity, successFn, errorFn)

    def doSendMedia(self, mediaType, filePath, url, to, ip = None, caption = None):
        if mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE:
            entity = ImageDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to, caption = caption)
        elif mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_AUDIO:
            entity = AudioDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to)
        elif mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_VIDEO:
            entity = VideoDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to, caption = caption)
        self.toLower(entity)

    def __str__(self):
        return "CLI Interface Layer"

    ########### callbacks ############

    def onRequestUploadResult(self, jid, mediaType, filePath, resultRequestUploadIqProtocolEntity, requestUploadIqProtocolEntity, caption = None):

        if resultRequestUploadIqProtocolEntity.isDuplicate():
            self.doSendMedia(mediaType, filePath, resultRequestUploadIqProtocolEntity.getUrl(), jid,
                             resultRequestUploadIqProtocolEntity.getIp(), caption)
        else:
            successFn = lambda filePath, jid, url: self.doSendMedia(mediaType, filePath, url, jid, resultRequestUploadIqProtocolEntity.getIp(), caption)
            mediaUploader = MediaUploader(jid, self.getOwnJid(), filePath,
                                      resultRequestUploadIqProtocolEntity.getUrl(),
                                      resultRequestUploadIqProtocolEntity.getResumeOffset(),
                                      successFn, self.onUploadError, self.onUploadProgress, async=False)
            mediaUploader.start()

    def onRequestUploadError(self, jid, path, errorRequestUploadIqProtocolEntity, requestUploadIqProtocolEntity):
        logger.error("Request upload for file %s for %s failed" % (path, jid))

    def onUploadProgress(self, filePath, jid, url, progress):
        sys.stdout.write("%s => %s, %d%% \r" % (os.path.basename(filePath), jid, progress))
        sys.stdout.flush()
