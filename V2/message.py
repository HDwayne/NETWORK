import json
import base64

class Message:
    def __init__(self, type, sequence_num=0, content=None, hash=None):
        self.type = type
        self.sequence_num = sequence_num
        self.content = content
        self.hash = hash

    def serialize(self):
        if isinstance(self.content, bytes):
            content_encoded = base64.b64encode(self.content).decode('utf-8')
        else:
            content_encoded = self.content

        message_data = {
            'type': self.type,
            'sequence_num': self.sequence_num,
            'content': content_encoded,
        }
        
        if self.hash is not None:
            message_data['hash'] = self.hash

        return json.dumps(message_data).encode('utf-8')

    @staticmethod
    def deserialize(data):
        obj = json.loads(data.decode('utf-8'))
        content_decoded = obj['content']

        # Décodage du contenu de Base64 uniquement pour les types de messages où c'est attendu
        if content_decoded is not None and obj['type'] == 'DATA':
            content_decoded = base64.b64decode(content_decoded)

        # Création de l'instance Message avec ou sans hash
        return Message(obj['type'], obj.get('sequence_num', 0), content_decoded, obj.get('hash'))
