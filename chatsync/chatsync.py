import asyncio
import hashlib
import importlib

import aiohttp
import yaml


def gravatar_url(email):
    hash = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash}"


async def watch_channel(client, sender, receivers):
    async for msg in sender.get_messages(client):
        msg["source"] = sender.name
        if "user_email" in msg and "user_avatar" not in msg:
            msg["user_avatar"] = gravatar_url(msg["user_email"])
        for receiver in receivers:
            # We aren't awaiting the results of these, which means even
            # if one receiver dies (or has delays) the rest will continue to work.
            asyncio.create_task(receiver.send_message(client, msg))


async def main():
    with open("chatsync.yaml") as f:
        config = yaml.safe_load(f.read())
    channels = []
    for channel_config in config["providers"]:
        try:
            provider = importlib.import_module(
                "." + channel_config["type"], ".providers"
            )
        except Exception as e:
            raise
        p = provider.Provider(channel_config)
        channels.append(p)
    coros = []
    async with aiohttp.ClientSession() as client:
        for index, channel in enumerate(channels):
            receivers = channels[:index] + channels[index + 1:]
            coros.append(watch_channel(client, channel, receivers))
        await asyncio.gather(*coros)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(main())
    loop.close()
