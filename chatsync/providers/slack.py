import json
import logging

import aiohttp


log = logging.getLogger('chatsync.slack')


class Provider(object):
    name = "slack"

    def __init__(self, config):
        self.token = config["token"]
        self.channel = config["channel"]

    async def _api_call(self, client, method, data=None):
        """Slack API call."""
        form = aiohttp.FormData(data or {})
        form.add_field("token", self.token)
        async with client.post(
            "https://slack.com/api/{0}".format(method), data=form, raise_for_status=True
        ) as response:
            return await response.json()

    async def send_message(self, client, message):
        data = {
            "channel": self.channel,
            "text": message["text"],
            "username": "{user} ({source})".format(**message),
        }
        if message.get("user_avatar"):
            data["icon_url"] = message["user_avatar"]
        try:
            await self._api_call(client, "chat.postMessage", data=data)
        except aiohttp.ClientError as e:
            log.exception('Error sending message.')

    async def get_messages(self, client):
        user_cache = {}
        while True:
            try:
                rtm = await self._api_call(client, "rtm.connect")
                assert rtm["ok"], "Error connecting to RTM."
                async with client.ws_connect(rtm["url"]) as ws:
                    async for msg in ws:
                        assert msg.type == aiohttp.WSMsgType.text
                        data = json.loads(msg.data)
                        if data["type"] != "message" or data.get("subtype") == "bot_message":
                            continue
                        if data["channel"] != self.channel:
                            continue
                        if data["user"] not in user_cache:
                            user_data = await self._api_call(
                                client, "users.info", data={"user": data["user"]}
                            )
                            user_cache[data["user"]] = {
                                "user": user_data["user"]["profile"]["display_name"] or
                                        user_data["user"]["profile"]["real_name"],
                                "user_email": user_data["user"]["profile"]["email"],
                                "user_avatar": user_data["user"]["profile"]["image_512"]
                            }
                        message = {"text": data["text"]}
                        message.update(user_cache[data["user"]])
                        yield message
            except aiohttp.ClientError as e:
                log.exception('Error getting messages. Restarting connection.')
