import asyncio
import logging
import config
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, RPCError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

message_queue = asyncio.Queue()

async def handle_flood(func, **kwargs):
    while True:
        try:
            return await func(**kwargs)
        except FloodWait as e:
            logger.warning(f"FloodWait detected. Sleeping for {e.value} seconds.")
            await asyncio.sleep(e.value + 1)
        except RPCError as e:
            logger.error(f"RPCError: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise e

async def process_queue(client):
    while True:
        try:
            message = await message_queue.get()
            if not message:
                message_queue.task_done()
                continue

            for chat_id in config.TARGET_CHANNELS:
                try:
                    kwargs = {
                        "chat_id": chat_id,
                        "from_chat_id": message.chat.id,
                        "message_id": message.id,
                    }

                    if message.caption:
                        kwargs["caption"] = message.caption
                        kwargs["caption_entities"] = message.caption_entities

                    await handle_flood(client.copy_message, **kwargs)
                    logger.info(f"✅ Forwarded message {message.id} from {message.chat.id} to {chat_id}")

                except Exception as e:
                    logger.error(f"❌ Error forwarding message {message.id} to {chat_id}: {e}")

            message_queue.task_done()
            
            await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"❌ Queue processing error: {e}")
            message_queue.task_done()
            await asyncio.sleep(1)

@Client.on_message(
    filters.chat(config.SOURCE_CHANNELS) & 
    (filters.video | filters.document) & 
    ~filters.sticker & 
    ~filters.photo & 
    ~filters.animation
)
async def forward_content(client, message):
    try:
        await message_queue.put(message)
        logger.info(f"✅ Queued message: {message.id} from {message.chat.id}")
    except Exception as e:
        logger.error(f"❌ Error queuing message: {e}")
