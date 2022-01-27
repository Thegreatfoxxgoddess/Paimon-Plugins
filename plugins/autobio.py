""" Auto Update Bio """

# By @Krishna_Singhal

import time
import asyncio

from pyrogram.errors import FloodWait

from resources.quotes import ENGLISH_QUOTES, MUSIC_LIST
from paimon import paimon, Message, get_collection

BIO_UPDATION = False
AUTOBIO_TIMEOUT = 300
BIO_QUOTES = ENGLISH_QUOTES

USER_DATA = get_collection("CONFIGS")

CHANNEL = paimon.getCLogger(__name__)
LOG = paimon.getLogger(__name__)


async def _init() -> None:
    global BIO_UPDATION, AUTOBIO_TIMEOUT  # pylint: disable=global-statement
    data = await USER_DATA.find_one({'_id': 'BIO_UPDATION'})
    if data:
        BIO_UPDATION = data['on']
    b_t = await USER_DATA.find_one({'_id': 'AUTOBIO_TIMEOUT'})
    if b_t:
        AUTOBIO_TIMEOUT = b_t['data']


@paimon.on_cmd("autobio", about={
    'header': "Auto Updates your Profile Bio with 2 languages.",
    'usage': "{tr}autobio (for eng)\n{tr}autobio Hi (for hindi)"})
async def auto_bio(msg: Message):
    """ Auto Update Your Bio """
    global BIO_UPDATION, BIO_QUOTES  # pylint: disable=global-statement
    if BIO_UPDATION:
        if isinstance(BIO_UPDATION, asyncio.Task):
            BIO_UPDATION.cancel()
        BIO_UPDATION = False
        USER_DATA.update_one({'_id': 'BIO_UPDATION'},
                             {"$set": {'on': False}}, upsert=True)
        await asyncio.sleep(1)

        await msg.edit(
            "Auto Bio Updation is **Stopped** Successfully...", log=__name__, del_in=5)
        return

    if 'm' in msg.input_str.lower():
        BIO_QUOTES = MUSIC_LIST
    else:
        BIO_QUOTES = ENGLISH_QUOTES

    USER_DATA.update_one({'_id': 'BIO_UPDATION'},
                         {"$set": {'on': True}}, upsert=True)
    await msg.edit(
        "Auto Bio Updation is **Started** Successfully...", log=__name__, del_in=3)
    BIO_UPDATION = asyncio.get_event_loop().create_task(_autobio_worker())


@paimon.on_cmd("sabto", about={
    'header': "Set auto bio timeout",
    'usage': "{tr}sabto [timeout in seconds]",
    'examples': "{tr}sabto 500"})
async def set_bio_timeout(message: Message):
    """ set auto bio timeout """
    global AUTOBIO_TIMEOUT  # pylint: disable=global-statement
    t_o = int(message.input_str)
    if t_o < 60:
        await message.err("too short! (minimum 60 sec)")
        return
    await message.edit("`Setting auto bio timeout...`")
    AUTOBIO_TIMEOUT = t_o
    await USER_DATA.update_one(
        {'_id': 'AUTOBIO_TIMEOUT'}, {"$set": {'data': t_o}}, upsert=True)
    await message.edit(
        f"`Set auto bio timeout as {t_o} seconds!`", del_in=5)


@paimon.on_cmd("vabto", about={'header': "View auto bio timeout"})
async def view_bio_timeout(message: Message):
    """ view bio timeout """
    await message.edit(
        f"`Profile picture will be updated after {AUTOBIO_TIMEOUT} seconds!`",
        del_in=5)


@paimon.add_task
async def _autobio_worker():
    while BIO_UPDATION:
        for quote in BIO_QUOTES:
            if not BIO_UPDATION:
                break
            try:
                await paimon.update_profile(bio=quote)
            except FloodWait as s_c:
                LOG.warn(s_c)
                time.sleep(s_c.x)
                await CHANNEL.log(s_c)
            except Exception as e_x:  # pylint: disable=broad-except
                LOG.error(e_x)
            await asyncio.sleep(AUTOBIO_TIMEOUT)
            await CHANNEL.log("Updating Next Quote...")
