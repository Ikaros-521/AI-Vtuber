from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent

from httpx import Proxy

room_id = "kyyxg"

proxys = {
    "http://": "http://127.0.0.1:10809",
    "https://": "http://127.0.0.1:10809"
}

# proxys = "http://127.0.0.1:10809"

#proxys = Proxy("http://127.0.0.1:10809")


# proxys = None

# Create the client
client: TikTokLiveClient = TikTokLiveClient(unique_id=f"@{room_id}", web_proxy=proxys, ws_proxy=proxys)


# Listen to an event with a decorator!
@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print(f"Connected to @{event.unique_id} (Room ID: {client.room_id}")


# Or, add it manually via "client.add_listener()"
async def on_comment(event: CommentEvent) -> None:
    print(f"{event.user.nickname} -> {event.comment}")


client.add_listener(CommentEvent, on_comment)

if __name__ == '__main__':
    # Run the client and block the main thread
    # await client.start() to run non-blocking
    client.run()