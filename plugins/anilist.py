""" Search for Anime related Info """

# Module Capable of fetching Anime, Airing, Character Info &
# Anime Reverse Search made for paimon.
# AniList Api (GitHub: https://github.com/AniList/ApiV2-GraphQL-Docs)
# Anime Reverse Search Powered by tracemoepy.
# TraceMoePy (GitHub: https://github.com/DragSama/tracemoepy)
# (C) Author: Phyco-Ninja (https://github.com/Phyco-Ninja) (@PhycoNinja13b)

import os
from datetime import datetime

import flag as cflag
import humanize
import tracemoepy
from aiohttp import ClientSession
from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from paimon import Message, paimon
from paimon.utils import media_to_image, check_owner
from paimon.utils import post_to_telegraph as post_to_tp

# Logging Errors
CLOG = paimon.getCLogger(__name__)

# Default templates for Query Formatting
ANIME_TEMPLATE = """{name}

**ID | MAL ID:** `{idm}` | `{idmal}`
➤ **SOURCE:** `{source}`
➤ **TYPE:** `{formats}`{dura}{chrctrsls}
{status_air}
➤ **ADULT RATED:** `{adult}`
🎬 {trailer_link}
📖 [Synopsis & More]({synopsis_link})

{additional}"""

# GraphQL Queries.
ANIME_QUERY = """
query ($id: Int, $idMal:Int, $search: String, $type: MediaType, $asHtml: Boolean) {
    Media (id: $id, idMal: $idMal, search: $search, type: $type) {
        id
        idMal
        title {
            romaji
            english
            native
        }
        format
        status
        description (asHtml: $asHtml)
        startDate {
            year
            month
            day
        }
        episodes
        duration
        countryOfOrigin
        source (version: 2)
        trailer {
          id
          site
          thumbnail
        }
        relations {
            edges {
                node {
                    title {
                        romaji
                        english
                    }
                    id
                }
                relationType
            }
        }
        bannerImage
        nextAiringEpisode {
            airingAt
            timeUntilAiring
            episode
        }
        isAdult
        characters (role: MAIN, page: 1, perPage: 10) {
            nodes {
                id
                name {
                    full
                    native
                }
                image {
                    large
                }
                description (asHtml: $asHtml)
                siteUrl
            }
        }
        studios (isMain: true) {
            nodes {
                name
                siteUrl
            }
        }
        siteUrl
    }
}
"""

AIRING_QUERY = """
query ($id: Int, $mediaId: Int, $notYetAired: Boolean) {
  Page(page: 1, perPage: 50) {
    airingSchedules (id: $id, mediaId: $mediaId, notYetAired: $notYetAired) {
      id
      airingAt
      timeUntilAiring
      episode
      mediaId
      media {
        title {
          romaji
          english
          native
        }
        duration
        coverImage {
          extraLarge
        }
        nextAiringEpisode {
          airingAt
          timeUntilAiring
          episode
        }
        bannerImage
        averageScore
        siteUrl
      }
    }
  }
}
"""

CHARACTER_QUERY = """
query ($search: String, $asHtml: Boolean) {
  Character (search: $search) {
    id
    name {
      full
      native
    }
    image {
      large
    }
    description (asHtml: $asHtml)
    siteUrl
    media (page: 1, perPage: 25) {
      nodes {
        id
        idMal
        title {
          romaji
          english
          native
        }
        type
        siteUrl
        coverImage {
          extraLarge
        }
        bannerImage
        averageScore
        description (asHtml: $asHtml)
      }
    }
  }
}
"""

MANGA_QUERY = """
query ($search: String, $type: MediaType) {
    Media (search: $search, type: $type) {
        id
        title {
            romaji
            english
            native
        }
        format
        countryOfOrigin
        source (version: 2)
        status
        description(asHtml: true)
        chapters
        volumes
        averageScore
        siteUrl
    }
}
"""

async def return_json_senpai(query, vars_):
    """ Makes a Post to https://graphql.anilist.co. """
    url_ = "https://graphql.anilist.co"
    async with ClientSession() as session:
        async with session.post(
            url_, json={"query": query, "variables": vars_}
        ) as post_con:
            json_data = await post_con.json()
    return json_data


def make_it_rw(time_stamp, as_countdown=False):
    """ Converting Time Stamp to Readable Format """
    if as_countdown:
        now = datetime.now()
        air_time = datetime.fromtimestamp(time_stamp)
        return str(humanize.naturaltime(now - air_time))
    return str(humanize.naturaldate(datetime.fromtimestamp(time_stamp)))


@paimon.on_cmd(
    "anime",
    about={
        "header": "Anime Search",
        "description": "Search for Anime using AniList API",
        "flags": {"-mid": "Search Anime using MAL ID", "-wp": "Get webpage previews "},
        "usage": "{tr}anime [flag] [anime name | ID]",
        "examples": [
            "{tr}anime 98444",
            "{tr}anime -mid 39576",
            "{tr}anime Asterisk war",
        ],
    },
)
async def anim_arch(message: Message):
    """ Search Anime Info """
    query = message.filtered_input_str
    if not query:
        await message.err("NameError: 'query' not defined")
        return
    vars_ = {"search": query, "asHtml": True, "type": "ANIME"}
    if query.isdigit():
        vars_ = {"id": int(query), "asHtml": True, "type": "ANIME"}
        if "-mid" in message.flags:
            vars_ = {"idMal": int(query), "asHtml": True, "type": "ANIME"}
    result = await get_ani(vars_)
    if len(result)!=1:
        title_img, finals_ = result[0], result[1]
    else:
        return await message.err(result[0])
    buttons = []
    if result[2]=="None":
        if result[3]!="None":
            buttons.append([InlineKeyboardButton(text="Sequel", callback_data=f"btn_{result[3]}")])
        else:
            if result[4]!=False:
                await message.reply_photo(title_img, caption=finals_)
                await message.delete()
                return
    else:
        if result[3]!="None":
            buttons.append(
                [
                    InlineKeyboardButton(text="Prequel", callback_data=f"btn_{result[2]}"),
                    InlineKeyboardButton(text="Sequel", callback_data=f"btn_{result[3]}")
                ]
            )
        else:
            buttons.append([InlineKeyboardButton(text="Prequel", callback_data=f"btn_{result[2]}")])
    if result[4]==False:
        buttons.append([InlineKeyboardButton(text="Download", switch_inline_query_current_chat=f"anime {result[5]}")])
    if "-wp" in message.flags:
        finals_ = f"[\u200b]({title_img}) {finals_}"
        await message.edit(finals_)
        return
    await message.reply_photo(title_img, caption=finals_, reply_markup=InlineKeyboardMarkup(buttons))
    await message.delete()


@paimon.on_cmd(
    "manga",
    about={
        "header": "Manga Search",
        "description": "Search for Manga using AniList API",
        "usage": "{tr}manga [manga name]",
        "examples": "{tr}manga Ao Haru Ride",
    },
)
async def manga_arch(message: Message):
    """ Search Manga Info """
    query = message.input_str
    if not query:
        await message.err("NameError: 'query' not defined")
        return
    vars_ = {"search": query, "asHtml": True, "type": "MANGA"}
    result = await return_json_senpai(MANGA_QUERY, vars_)
    error = result.get("errors")
    if error:
        await CLOG.log(f"**ANILIST RETURNED FOLLOWING ERROR:**\n\n`{error}`")
        error_sts = error[0].get("message")
        await message.err(f"[{error_sts}]")
        return

    data = result["data"]["Media"]

    # Data of all fields in returned json
    # pylint: disable=possibly-unused-variable
    idm = data.get("id")
    romaji = data["title"]["romaji"]
    english = data["title"]["english"]
    native = data["title"]["native"]
    status = data.get("status")
    synopsis = data.get("description")
    description = synopsis[:500]
    if len(synopsis) > 500:
      description += "..."
    volumes = data.get("volumes")
    chapters = data.get("chapters")
    score = data.get("averageScore")
    url = data.get("siteUrl")
    format_ = data.get("format")
    country = data.get("countryOfOrigin")
    source = data.get("source")
    c_flag = cflag.flag(country)

    name = f"""[{c_flag}]**{romaji}**
        __{english}__
        {native}"""
    if english==None:
        name = f"""[{c_flag}]**{romaji}**
        {native}"""
    finals_ = f"{name}\n\n"
    finals_ += f"➤ **ID:** `{idm}`\n"
    finals_ += f"➤ **STATUS:** `{status}`\n"
    finals_ += f"➤ **VOLUMES:** `{volumes}`\n"
    finals_ += f"➤ **CHAPTERS:** `{chapters}`\n"
    finals_ += f"➤ **SCORE:** `{score}`\n"
    finals_ += f"➤ **FORMAT:** `{format_}`\n"
    finals_ += f"➤ **SOURCE:** `{source}`\n\n"
    finals_ += f"Description: `{description}`\n\n"
    finals_ += f"For more info <a href='{url}'>click here</a>"
    pic = f"https://img.anili.st/media/{idm}"
    await message.reply_photo(pic, caption=finals_)
    await message.delete()


@paimon.on_cmd(
    "airing",
    about={
        "header": "Airing Info",
        "description": "Fetch Airing Detail of a Anime",
        "usage": "{tr}airing [Anime Name | Anilist ID]",
        "examples": "{tr}airing 108632",
    },
)
async def airing_anim(message: Message):
    """ Get Airing Detail of Anime """
    query = message.input_str
    if not query:
        await message.err("NameError: 'query' not defined")
        return
    vars_ = {"search": query, "asHtml": True, "type": "ANIME"}
    if query.isdigit():
        vars_ = {"id": int(query), "asHtml": True, "type": "ANIME"}
    result = await return_json_senpai(ANIME_QUERY, vars_)
    error = result.get("errors")
    if error:
        await CLOG.log(f"**ANILIST RETURNED FOLLOWING ERROR:**\n\n`{error}`")
        error_sts = error[0].get("message")
        await message.err(f"[{error_sts}]")
        return

    data = result["data"]["Media"]

    # Airing Details
    mid = data.get("id")
    romaji = data["title"]["romaji"]
    english = data["title"]["english"]
    native = data["title"]["native"]
    status = data.get("status")
    episodes = data.get("episodes")
    country = data.get("countryOfOrigin")
    c_flag = cflag.flag(country)
    source = data.get("source")
    coverImg = f"https://img.anili.st/media/{mid}"
    air_on = None
    if data["nextAiringEpisode"]:
        nextAir = data["nextAiringEpisode"]["airingAt"]
        episode = data["nextAiringEpisode"]["episode"]
        air_on = make_it_rw(nextAir, True)

    title_ = english or romaji
    out = f"[{c_flag}] **{native}** \n   (`{title_}`)"
    out += f"\n\n**ID:** `{mid}`"
    out += f"\n**Status:** `{status}`\n"
    out += f"**Source:** `{source}`\n"
    if air_on:
        out += f"**Airing Episode:** `[{episode}/{episodes}]`\n"
        out += f"\n`{air_on}`"
    if len(out) > 1024:
        await message.edit(out)
        return
    await message.reply_photo(coverImg, caption=out)
    await message.delete()


@paimon.on_cmd(
    "scheduled",
    about={
        "header": "Scheduled Animes",
        "description": "Fetch a list of Scheduled Animes from "
        "AniList API. [<b>Note:</b> If Query exceeds "
        "Limit (i.e. 9 aprox) remaining Animes from "
        "will be directly posted to Log Channel "
        "to avoid Spam of Current Chat.]",
        "usage": "{tr}scheduled",
    },
)
async def get_schuled(message: Message):
    """ Get List of Scheduled Anime """
    var = {"notYetAired": True}
    await message.edit("`Fetching Scheduled Animes`")
    result = await return_json_senpai(AIRING_QUERY, var)
    error = result.get("errors")
    if error:
        await CLOG.log(f"**ANILIST RETURNED FOLLOWING ERROR:**\n\n{error}")
        error_sts = error[0].get("message")
        await message.err(f"[{error_sts}]")
        return

    data = result["data"]["Page"]["airingSchedules"]
    c = 0
    totl_schld = len(data)
    out = ""
    for air in data:
        romaji = air["media"]["title"]["romaji"]
        english = air["media"]["title"]["english"]
        mid = air["mediaId"]
        epi_air = air["episode"]
        air_at = make_it_rw(air["airingAt"], True)
        site = air["media"]["siteUrl"]
        title_ = english or romaji
        out += f"<p>[🇯🇵]{title_}</p>"
        out += f" • <b>ID:</b> {mid}<br>"
        out += f" • <b>Airing Episode:</b> {epi_air}<br>"
        out += f" • <b>Next Airing:</b> {air_at}<br>"
        out += f" • <a href='{site}'>[Visit on anilist.co]</a><br><br>"
        c += 1
    if out:
        out_p = f"<p>Showing [{c}/{totl_schld}] Scheduled Animes:</p><br><br>{out}"
        link = post_to_tp("Scheduled Animes", out_p)
        await message.edit(f"[Open in Telegraph]({link})")


@paimon.on_cmd(
    "character",
    about={
        "header": "Anime Character",
        "description": "Get Info about a Character and much more",
        "usage": "{tr}character [Name of Character]",
        "examples": "{tr}character Subaru Natsuki",
    },
)
async def character_search(message: Message):
    """ Get Info about a Character """
    query = message.input_str
    if not query:
        await message.err("NameError: 'query' not defined")
        return
    var = {"search": query, "asHtml": True}
    result = await return_json_senpai(CHARACTER_QUERY, var)
    error = result.get("errors")
    if error:
        await CLOG.log(f"**ANILIST RETURNED FOLLOWING ERROR:**\n\n`{error}`")
        error_sts = error[0].get("message")
        await message.err(f"[{error_sts}]")
        return

    data = result["data"]["Character"]

    # Character Data
    id_ = data["id"]
    name = data["name"]["full"]
    native = data["name"]["native"]
    img = data["image"]["large"]
    site_url = data["siteUrl"]
    description = data["description"]
    featured = data["media"]["nodes"]
    snin = "\n"
    sninal = ""
    sninml = ""
    for ani in featured:
        k = ani["title"]["english"] or ani["title"]["romaji"]
        kk = ani["type"]
        if kk=="MANGA":
            sninml += f"    • {k}\n"
    for ani in featured:
        kkk = ani["title"]["english"] or ani["title"]["romaji"]
        kkkk = ani["type"]
        if kkkk=="ANIME":
            sninal += f"    • {kkk}\n"
    sninal += "\n"
    sninm = "  `MANGAS`\n" if len(sninml)!=0 else ""
    snina = "  `ANIMES`\n" if len(sninal)!=0 else ""
    snin = f"\n{snina}{sninal}{sninm}{sninml}"
    sp = 0
    cntnt = ""
    for cf in featured:
        out = "<br>"
        out += f"""<img src="{cf['coverImage']['extraLarge']}"/>"""
        out += "<br>"
        title = cf["title"]["english"] or cf["title"]["romaji"]
        out += f"<p>{title}</p>"
        out += f"[🇯🇵] {cf['title']['native']}<br>"
        out += f"""<a href="{cf['siteUrl']}>{cf['type']}</a><br>"""
        out += f"<b>Media ID:</b> {cf['id']}<br>"
        out += f"<b>SCORE:</b> {cf['averageScore']}/100<br>"
        out += cf.get("description", "N/A") + "<br>"
        cntnt += out
        sp += 1
        out = ""
        if sp > 5:
            break

    html_cntnt = f"<img src='{img}' title={name}/>"
    html_cntnt += f"<p>[🇯🇵] {native}</p>"
    html_cntnt += "<p>About Character:</p>"
    html_cntnt += description
    html_cntnt += "<br>"
    if cntnt:
        html_cntnt += "<p>Top Featured Anime</p>"
        html_cntnt += cntnt
        html_cntnt += "<br><br>"
    url_ = post_to_tp(name, html_cntnt)
    cap_text = f"""[🇯🇵] __{native}__
    (`{name}`)
**ID:** {id_}

**Featured in:** __{snin}__

[About Character]({url_})
[Visit Website]({site_url})"""

    if len(cap_text) <= 1023:
        await message.reply_photo(img, caption=cap_text)
    else:
        await message.reply(cap_text)
    await message.delete()



async def get_ani(vars_):
    result = await return_json_senpai(ANIME_QUERY, vars_)
    error = result.get("errors")
    if error:
        await CLOG.log(f"**ANILIST RETURNED FOLLOWING ERROR:**\n\n`{error}`")
        error_sts = error[0].get("message")
        return [f"[{error_sts}]"]

    data = result["data"]["Media"]

    # Data of all fields in returned json
    # pylint: disable=possibly-unused-variable
    idm = data.get("id")
    idmal = data.get("idMal")
    romaji = data["title"]["romaji"]
    english = data["title"]["english"]
    native = data["title"]["native"]
    formats = data.get("format")
    status = data.get("status")
    synopsis = data.get("description")
    duration = data.get("duration")
    country = data.get("countryOfOrigin")
    c_flag = cflag.flag(country)
    source = data.get("source")
    prqlsql = data.get("relations").get('edges')
    bannerImg = data.get("bannerImage")
    s_date = data.get("startDate")
    adult = data.get("isAdult")
    trailer_link = "N/A"
    if data["title"]["english"] is not None:
        name = f'''[{c_flag}]**{romaji}**
        __{english}__
        {native}'''
    else:
        name = f'''[{c_flag}]**{romaji}**
        {native}'''
    prql, prql_id, sql, sql_id = "", "None", "", "None"
    for i in prqlsql:
        if i['relationType']=="PREQUEL":
            pname = i["node"]["title"]["english"] if i["node"]["title"]["english"] is not None else i["node"]["title"]["romaji"]
            prql += f"**PREQUEL:** `{pname}`\n"
            prql_id = f"{i['node']['id']}"
            break
    for i in prqlsql:
        if i['relationType']=="SEQUEL":
            sname = i["node"]["title"]["english"] if i["node"]["title"]["english"] is not None else i["node"]["title"]["romaji"]
            sql += f"**SEQUEL:** `{sname}`\n"
            sql_id = f"{i['node']['id']}"
            break
    additional = f"{prql}{sql}"
    dura = f"\n➤ **DURATION:** `{duration} min/ep`" if duration!=None else ""
    charlist = []
    for char in data["characters"]["nodes"]:
        charlist.append(f"    •{char['name']['full']}")
    chrctrs = "\n"
    chrctrs += ("\n").join(charlist[:10])
    chrctrsls = f"\n➤ **CHARACTERS:** `{chrctrs}`" if len(charlist)!=0 else ""
    air_on = None
    if data["nextAiringEpisode"]:
        nextAir = data["nextAiringEpisode"]["airingAt"]
        air_on = make_it_rw(nextAir)
        eps = data['nextAiringEpisode']['episode']
        ep_ = list(str(data['nextAiringEpisode']['episode']))
        x = ep_.pop()
        th = "th"
        if len(ep_)>=1:
            if ep_.pop()!="1":
                th = pos_no(x)
        else:
            th = pos_no(x)
        air_on += f" | {eps}{th} eps"
    if air_on==None:
        status_air = f"➤ <b>STATUS:</b> `{status}`"
    else:
        status_air = f"➤ <b>STATUS:</b> `{status}`\n➤ <b>NEXT AIRING:</b> `{air_on}`"
    if data["trailer"] and data["trailer"]["site"] == "youtube":
        trailer_link = f"[Trailer](https://youtu.be/{data['trailer']['id']})"
    html_char = ""
    for character in data["characters"]["nodes"]:
        html_ = ""
        html_ += "<br>"
        html_ += f"""<a href="{character['siteUrl']}">"""
        html_ += f"""<img src="{character['image']['large']}"/></a>"""
        html_ += "<br>"
        html_ += f"<p>{character['name']['full']}</p>"
        html_ += f"{c_flag} {character['name']['native']}<br>"
        html_ += f"<b>Character ID</b>: {character['id']}<br>"
        html_ += (
            f"<p>About Character and Role:</p>{character.get('description', 'N/A')}"
        )
        html_char += f"{html_}<br><br>"
    studios = "".join("<a href='{}'>• {}</a> ".format(studio["siteUrl"], studio["name"]) for studio in data["studios"]["nodes"])
    url = data.get("siteUrl")
    title_img = f"https://img.anili.st/media/{idm}"
    # Telegraph Post mejik
    html_pc = ""
    html_pc += f"<img src='{title_img}' title={romaji}/>"
    html_pc += f"<p>[{c_flag}] {native}</p>"
    html_pc += "<p>Synopsis:</p>"
    html_pc += synopsis
    html_pc += "<br>"
    if html_char:
        html_pc += "<p>Main Characters:</p>"
        html_pc += html_char
        html_pc += "<br><br>"
    html_pc += "<p>More Info:</p>"
    html_pc += f"<b>Started On:</b> {s_date['day']}/{s_date['month']}/{s_date['year']}"
    html_pc += f"<br><b>Studios:</b> {studios}<br>"
    html_pc += f"<a href='https://myanimelist.net/anime/{idmal}'>View on MAL</a>"
    html_pc += f"<a href='{url}'> View on anilist.co</a>"
    html_pc += f"<img src='{bannerImg}'/>"
    title_h = english or romaji
    html_pc = html_pc.replace("span", "")
    synopsis_link = post_to_tp(str(title_h), str(html_pc))
    try:
        finals_ = ANIME_TEMPLATE.format(**locals())
    except KeyError as kys:
        return [f"{kys}"]
    return title_img, finals_, prql_id, sql_id, adult, romaji


def pos_no(x):
    th = "st" if x=="1" else "nd" if x=="2" else "rd" if x=="3" else "th"
    return th


@paimon.bot.on_callback_query(filters.regex(pattern=r"btn_(.*)"))
@check_owner
async def present_res(cq: CallbackQuery):
    idm = cq.data.split("_")[1]
    vars_ = {"id": int(idm), "asHtml": True, "type": "ANIME"}
    result = await get_ani(vars_)
    pic, msg = result[0], result[1]
    btns = []
    if result[2]=="None":
        if result[3]!="None":
            btns.append([InlineKeyboardButton(text="Sequel", callback_data=f"btn_{result[3]}")])
    else:
        if result[3]!="None":
            btns.append(
                [
                    InlineKeyboardButton(text="Prequel", callback_data=f"btn_{result[2]}"),
                    InlineKeyboardButton(text="Sequel", callback_data=f"btn_{result[3]}")
                ]
            )
        else:
            btns.append([InlineKeyboardButton(text="Prequel", callback_data=f"btn_{result[2]}")])
    if result[4]==False:
        btns.append([InlineKeyboardButton(text="Download", switch_inline_query_current_chat=f"anime {result[5]}")])
    await cq.edit_message_media(InputMediaPhoto(pic, caption=msg), reply_markup=InlineKeyboardMarkup(btns))
