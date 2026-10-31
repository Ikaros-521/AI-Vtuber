from TikTokLive import TikTokLiveClient
from TikTokLive.types.events import CommentEvent, ConnectEvent, DisconnectEvent, JoinEvent, GiftEvent
from TikTokLive.types.errors import LiveNotFound

# proxies = {
#     "http://": "http://127.0.0.1:10809",
#     "https://": "http://127.0.0.1:10809"
# }

proxies = None


# 代理软件开启TUN模式进行代理，由于库的ws不走传入的代理参数，只能靠代理软件全代理了
client: TikTokLiveClient = TikTokLiveClient(unique_id="@blacktiebreaks", proxies=proxies)


# Define how you want to handle specific events via decorator
@client.on("connect")
async def on_connect(_: ConnectEvent):
    print("Connected to Room ID:", client.room_id)

@client.on("disconnect")
async def on_disconnect(event: DisconnectEvent):
    print("Disconnected")

@client.on("join")
async def on_join(event: JoinEvent):
    print(f"@{event.user.unique_id} joined the stream!")

# Notice no decorator?
@client.on("comment")
async def on_comment(event: CommentEvent):
    print(f"{event.user.nickname} -> {event.comment}")

@client.on("gift")
async def on_gift(event: GiftEvent):
    """
    This is an example for the "gift" event to show you how to read gift data properly.

    Important Note:

    Gifts of type 1 can have streaks, so we need to check that the streak has ended
    If the gift type isn't 1, it can't repeat. Therefore, we can go straight to printing

    """

    # Streakable gift & streak is over
    if event.gift.streakable and not event.gift.streaking:
        print(f"{event.user.unique_id} sent {event.gift.count}x \"{event.gift.info.name}\"")

    # Non-streakable gift
    elif not event.gift.streakable:
        print(f"{event.user.unique_id} sent \"{event.gift.info.name}\"")

# Define handling an event via a "callback"
# client.add_listener("comment", on_comment)

if __name__ == '__main__':
    # Run the client and block the main thread
    # await client.start() to run non-blocking
    try:
        client.run()

    except LiveNotFound:
        print(f"User `@{client.unique_id}` seems to be offline, retrying after 1 minute...")
        
