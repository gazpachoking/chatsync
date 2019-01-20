import asyncio
import logging

from irc.client_aio import AioSimpleIRCClient


log = logging.getLogger('chatsync.irc')


class IRCClient(AioSimpleIRCClient):
    def __init__(self, config):
        self.msg_queue = asyncio.Queue()
        self.config = config
        self.ready = asyncio.Event()
        super().__init__()

    async def connect(self):
        """Connect to the server and wait until we have joined the selected channel."""
        if not self.connection.connected:
            log.info('Connecting to IRC server %s', self.config["server"])
            self.ready.clear()
            await self.connection.connect(
                self.config["server"], self.config["port"], self.config["nick"], self.config.get("password")
            )
        await self.ready.wait()

    def send_message(self, message):
        self.connection.privmsg(self.config["channel"], message)

    def on_welcome(self, connection, event):
        connection.join(self.config["channel"])

    def on_join(self, connection, event):
        log.info("Joined channel %s", self.config["channel"])
        self.ready.set()

    def on_pubmsg(self, connection, event):
        if event.source.nick == self.connection.nickname:
            return
        msg = {
            "user": event.source.nick,
            "text": event.arguments[0]
        }
        self.msg_queue.put_nowait(msg)


class Provider(object):
    name = "irc"

    def __init__(self, config):
        self.config = config
        self.irc_client = IRCClient(self.config)

    async def get_messages(self, client):
        await self.irc_client.connect()
        while True:
            yield await self.irc_client.msg_queue.get()

    async def send_message(self, client, message):
        await self.irc_client.connect()
        msg = "<{user} ({source})> {text}".format(**message)
        self.irc_client.send_message(msg)
