import json
import logging

import aiohttp


log = logging.getLogger('chatsync.gitter')


class Provider(object):
    name = "gitter"

    def __init__(self, config):
        self.config = config
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(self.config["token"])
        }
        self.connected = False
        self.bot_id = None
        self.room_id = None

    async def connect(self, client):
        if self.connected:
            return
        try:
            r = await client.get('https://api.gitter.im/v1/user/me', headers=self.headers, raise_for_status=True)
            user_info = await r.json()
        except aiohttp.ClientError as e:
            log.exception("Error connecting to gitter.")
            raise
        log.info("Connected to gitter with user %s", user_info["username"])
        self.bot_id = user_info["id"]
        try:
            r = await client.post("https://api.gitter.im/v1/rooms", json={"uri": self.config["room"]},
                                 raise_for_status=True, headers=self.headers)
            room_info = await r.json()
        except aiohttp.ClientError as e:
            log.exception("Error joining gitter room %s", self.config["room"])
            raise
        log.info("Joined gitter room %s", room_info["name"])
        self.room_id = room_info["id"]
        self.connected = True

    async def send_message(self, client, message):
        await self.connect(client)
        msg = "<{user} ({source})> {text}".format(**message)
        try:
            r = await client.post('https://api.gitter.im/v1/rooms/{}/chatMessages'.format(self.room_id),
                                  json={"text": msg}, headers=self.headers, raise_for_status=True)
        except aiohttp.ClientError as e:
            log.exception('Error sending message.')

    async def get_messages(self, client):
        await self.connect(client)
        while True:
            try:
                r = await client.get('https://stream.gitter.im/v1/rooms/{}/chatMessages'.format(room_id),
                                     headers=self.headers, timeout=None, raise_for_status=True)
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
            except aiohttp.ClientError as e:
                log.exception('Error getting messages. Restarting connection.')
