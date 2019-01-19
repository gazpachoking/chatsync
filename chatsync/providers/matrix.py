from urllib.parse import quote


class Provider(object):
    name = "matrix"

    def __init__(self, config):
        self.config = config
        self.token = None

    async def _api_call(self, client, method, endpoint, data=None, params=None):
        """Slack API call."""
        params = params or {}
        headers = {}
        if self.token:
            headers["Authorization"] = "Bearer {}".format(self.token)
        async with client.request(method,
                                  "{0}{1}".format(self.config["homeserver"], endpoint),
                                  json=data, params=params, headers=headers) as response:
            assert 200 == response.status, "{0} with {1} failed.".format(method, data)
            return await response.json()

    async def get_messages(self, client):
        data = {
            "type": "m.login.password",
            "identifier": {
                "user": self.config["username"],
                "type": "m.id.user"
            },
            "password": self.config["password"]
        }
        login_data = await self._api_call(client, 'post', "/_matrix/client/r0/login", data=data)
        self.token = login_data["access_token"]
        bot_id = login_data["user_id"]
        r = await self._api_call(client, 'get', "/_matrix/client/r0/sync",
                                 params={"filter": '{"room":{"timeline":{"limit":1}}}'})
        next_batch = r['next_batch']
        while True:
            r = await self._api_call(client, 'get', "/_matrix/client/r0/sync",
                                     params={"since": next_batch, "timeout": 200000})
            next_batch = r['next_batch']
            if self.config["room"] not in r["rooms"]["join"]:
                continue
            for event in r["rooms"]["join"][self.config["room"]]["timeline"]["events"]:
                if event["type"] != "m.room.message":
                    continue
                if event["sender"] == bot_id:
                    continue
                yield {
                    "user": event["sender"].split(":")[0][1:],
                    "text": event["content"]["body"]
                }

    async def send_message(self, client, message):
        data = {
            "msgtype": "m.text",
            "body": "<{user} ({source})> {text}".format(**message)
        }
        r = await self._api_call(client, "post",
                                 "/_matrix/client/r0/rooms/{}/send/m.room.message".format(quote(self.config["room"])),
                                 data=data)
