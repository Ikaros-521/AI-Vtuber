import asyncio

from TikTokLive import TikTokLiveClient
from TikTokLive.client.logger import LogLevel
from TikTokLive.events import ConnectEvent

room_id = "osmatrix23"

proxys = {
    "http://": "http://127.0.0.1:10809",
    "https://": "http://127.0.0.1:10809"
}

proxys = None

# 代理软件开启TUN模式进行代理，由于库的ws不走传入的代理参数，只能靠代理软件全代理了
client: TikTokLiveClient = TikTokLiveClient(unique_id=f"@{room_id}", web_proxy=proxys, ws_proxy=proxys)



@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    client.logger.info(f"Connected to @{event.unique_id}!")


async def check_loop():
    # Run 24/7
    while True:

        # Check if they're live
        while not await client.is_live():
            client.logger.info("Client is currently not live. Checking again in 60 seconds.")
            await asyncio.sleep(60)  # Spamming the endpoint will get you blocked

        # Connect once they become live
        client.logger.info("Requested client is live!")
        await client.connect()

        # client.run()


if __name__ == '__main__':
    client.logger.setLevel(LogLevel.INFO.value)
    asyncio.run(check_loop())