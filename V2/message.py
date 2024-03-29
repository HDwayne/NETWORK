import base64
import json


class Message:
    def __init__(self, type, sequence_num=0, content=None, hash=None):
        self.type = type
        self.sequence_num = sequence_num
        self.content = content
        self.hash = hash

    def serialize(self):
        if isinstance(self.content, bytes):
            content_encoded = base64.b64encode(self.content).decode("utf-8")
        else:
            content_encoded = self.content

        message_data = {
            "type": self.type,
            "sequence_num": self.sequence_num,
            "content": content_encoded,
            "hash": self.hash,
        }

        serialized_data = json.dumps(message_data).encode("utf-8")
        length_prefix = len(serialized_data).to_bytes(4, byteorder="big")

        return length_prefix + serialized_data

    @staticmethod
    def deserialize(data):
        obj = json.loads(data.decode("utf-8"))
        content_decoded = obj["content"]

        if content_decoded is not None and obj["type"] == "DATA":
            content_decoded = base64.b64decode(content_decoded)

        return Message(
            obj["type"], obj.get("sequence_num"), content_decoded, obj.get("hash")
        )

    def send(self, socket):
        serialized_message = self.serialize()
        try:
            socket.send(serialized_message)
        except socket.error:
            raise
