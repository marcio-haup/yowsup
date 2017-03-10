from yowsup.structs import ProtocolEntity, ProtocolTreeNode
from .notification import NotificationProtocolEntity
class PictureNotificationProtocolEntity(NotificationProtocolEntity):
    '''
    <notification offline="0" id="{{NOTIFICATION_ID}}" notify="{{NOTIFY_NAME}}" type="picture" 
            t="{{TIMESTAMP}}" from="{{SENDER_JID}}">
    </notification>
    '''

    def __init__(self, _id,  _from, status, timestamp, notify, offline, setJid, setId):
        super(PictureNotificationProtocolEntity, self).__init__("picture", _id, _from, timestamp, notify, offline)
        self.setData(setJid, setId)

    def getNotify(self):
        return self.notify

    def getParticipant(self, full = True):
        return self._participant if full else self._participant.split('@')[0]

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = NotificationProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = PictureNotificationProtocolEntity
        return entity