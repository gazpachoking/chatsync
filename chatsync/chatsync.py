import asyncio
import hashlib
import importlib
import pprint

import aiohttp
import yaml


def gravatar_url(email):
    hash = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash}"


async def watch_channel(client, sender, receivers):
    async for msg in sender.get_messages(client):
        msg["source"] = sender.type
        if "user_email" in msg and "user_avatar" not in msg:
            msg["user_avatar"] = gravatar_url(msg["user_email"])
        for receiver in receivers:
            await receiver.send_message(client, msg)


async def main():
    with open("chatsync.yaml") as f:
        config = yaml.load(f.read())
    channels = []
    for channel_config in config["providers"]:
        try:
            provider = importlib.import_module(
                "." + channel_config["type"], ".providers"
            )
        except Exception as e:
            raise
        p = provider.Provider(channel_config)
        p.type = channel_config["type"]
        channels.append(p)
    tasks = []
    async with aiohttp.ClientSession() as client:
        for index, channel in enumerate(channels):
            receivers = channels[:index] + channels[index + 1:]
            tasks.append(asyncio.create_task(watch_channel(client, channel, receivers)))
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(main())
    loop.close()
