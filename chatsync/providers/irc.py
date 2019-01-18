import asyncio

import irc
from irc.client_aio import AioSimpleIRCClient


class IRCClient(AioSimpleIRCClient):
    def __init__(self, target):
        self.msg_queue = asyncio.Queue()
        self.target = target
        super().__init__()

    def on_welcome(self, connection, event):
        connection.join(self.target)

    def on_pubmsg(self, connection, event):
        if event.source.nick == self.connection.nickname:
            return
        msg = {
            "user": event.source.nick,
            "text": event.arguments[0]
        }
        self.msg_queue.put_nowait(msg)


class Provider(object):
    def __init__(self, config):
        self.config = config
        self.irc_client = IRCClient(self.config["channel"])

    async def get_messages(self, client):
        try:
            await self.irc_client.connection.connect(
                self.config["server"], self.config["port"], self.config["nick"]
            )
        except irc.client.ServerConnectionError as x:
            print(x)

        while True:
            yield await self.irc_client.msg_queue.get()

    async def send_message(self, client, message):
        msg = "<{user} ({source})> {text}".format(**message)
        self.irc_client.connection.privmsg(self.irc_client.target, msg)
