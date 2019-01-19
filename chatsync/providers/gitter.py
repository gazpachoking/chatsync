import json


class Provider(object):
    name = "gitter"

    def __init__(self, config):
        self.config = config
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(self.config["token"])
        }

    async def send_message(self, client, message):
        msg = "<{user} ({source})> {text}".format(**message)
        r = await client.post('https://api.gitter.im/v1/rooms/{}/chatMessages'.format(self.config["room"]),
                              json={"text": msg}, headers=self.headers)

    async def get_messages(self, client):
        r = await client.get('https://api.gitter.im/v1/user/me', headers=self.headers)
        user_info = await r.json()
        bot_id = user_info["id"]
        r = await client.get('https://stream.gitter.im/v1/rooms/{}/chatMessages'.format(self.config["room"]),
                             headers=self.headers, timeout=None)
        while True:
            data = await r.content.readline()
            if not data.strip():
                continue
            gitter_msg = json.loads(data)
            if gitter_msg["fromUser"]["id"] == bot_id:
                continue
            yield {
                "user": gitter_msg["fromUser"]["username"],
                "user_avatar": gitter_msg["fromUser"]["avatarUrl"],
                "text": gitter_msg["text"]
            }
