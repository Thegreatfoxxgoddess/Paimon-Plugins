
from aiofiles import os
from telegraph import upload_file

from paimon import paimon, Config, Message, pool


@paimon.on_cmd("yrs", about={
    'header': "Yandex Reverse Search",
    'description': "Reverse Search any Image/sticker",
    'usage': "{tr}yrs [Reply to image | sticker]",
    'note': "Gif & Animated Stickers won't work!"}, check_downpath=True)
async def labstack(message: Message):
    replied = message.reply_to_message
    if replied and (replied.sticker or replied.photo or replied.video or replied.gif):
        await message.edit("`processing ...`")
        dl_loc = await message.client.download_media(
            message=message.reply_to_message,
            file_name=Config.DOWN_PATH,
        )
    else:
        return await message.err("Media not found!")

    try:
        response = await pool.run_in_thread(upload_file)(dl_loc)
    except Exception as t_e:
        await message.err(str(t_e))
    else:
        media_link = f"https://telegra.ph{response[0]}"
        yandex_link = f"https://yandex.com/images/search?rpt=imageview&url={media_link}"
        await message.edit(f"**[Yandex Search Results]({yandex_link})**")
    finally:
        await os.remove(dl_loc)




@paimon.on_cmd("grs", about={
    'header': "google Reverse Search",
    'description': "Reverse Search any Image/sticker",
    'usage': "{tr}yrs [Reply to image | sticker]",
    'note': "Gif & Animated Stickers won't work!"}, check_downpath=True)
async def labstack(message: Message):
    replied = message.reply_to_message
    if replied and (replied.sticker or replied.photo or replied.video or replied.gif):
        await message.edit("`processing ...`")
        dl_loc = await message.client.download_media(
            message=message.reply_to_message,
            file_name=Config.DOWN_PATH,
        )
    else:
        return await message.err("Media not found!")

    try:
        response = await pool.run_in_thread(upload_file)(dl_loc)
    except Exception as t_e:
        await message.err(str(t_e))
    else:
        media_link = f"https://telegra.ph{response[0]}"
        google_link = f"https://www.google.com/searchbyimage?={media_link}"
        await message.edit(f"**[google Search Results]({google_link})**")
    finally:
        await os.remove(dl_loc)
