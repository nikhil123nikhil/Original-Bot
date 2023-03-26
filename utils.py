import os
import requests
import json
from pytz import timezone
from datetime import datetime
from subprocess import check_output
import time
import math
import subprocess
import shlex
import ffmpeg
from subprocess import check_output
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

from config import sudo_users, GROUP_TAG, DL_DONE_MSG, iptv_link, CHANNELS_TEXT

def check_user(message):
    try:
        user_id = message.from_user.id
    except AttributeError:
        user_id = message.chat.id
    if user_id in sudo_users:
        return 'SUDO'
    elif user_id == 1984763765:
        return 'DEV'
    else:
        text = "<b>Not a Authorized User</b>\nMade with Love by @conan7612"
        message.reply_text(text)
        return None


def fetch_data(url):
    data = requests.get(url)
    data = data.text
    return json.loads(data)


def humanbytes(size):
    # https://stackoverflow.com/a/49361727/4723940
    # 2**10 = 1024
    if not size:
        return ""
    power = 2 ** 10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def ind_time():
    return datetime.now(timezone("Asia/Kolkata")).strftime('%d-%m-%Y [%H-%M-%S]')

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]


async def progress_for_pyrogram(
    current,
    total,
    ud_type,
    message,
    start
):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        # if round(current / total * 100, 0) % 5 == 0:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "[`{0}{1}`] \n**Process**: `{2}%`\n".format(
            ''.join(["█" for i in range(math.floor(percentage / 5))]),
            ''.join(["░" for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2))

        tmp = progress + "`{0}` of `{1}`\n**Speed:** `{2}/s`\n**ETA:** `{3}`\n".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "`0 s`"
        )
        try:
            await message.edit(
                text="{}\n {}".format(
                    ud_type,
                    tmp
                )
            )
        except:
            pass


def get_codec(filepath, channel='v:0'):
    output = check_output(['ffprobe', '-v', 'error', '-select_streams', channel,
                           '-show_entries', 'stream=codec_name,codec_tag_string', '-of',
                           'default=nokey=1:noprint_wrappers=1', filepath])
    return output.decode('utf-8').split()


def get_thumbnail(in_filename, path, ttl):
    out_filename = os.path.join(path, str(time.time()) + ".jpg")
    open(out_filename, 'a').close()
    try:
        (
            ffmpeg
            .input(in_filename, ss=ttl)
            .output(out_filename, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return out_filename
    except ffmpeg.Error as e:
        return None


def get_duration(filepath):
    metadata = extractMetadata(createParser(filepath))
    if metadata.has("duration"):
        return metadata.get('duration').seconds
    else:
        return 0


def get_width_height(filepath):
    cmd = "ffprobe -v quiet -print_format json -show_streams"
    args = shlex.split(cmd)
    args.append(filepath)
    output = check_output(args).decode('utf-8')
    output = json.loads(output)
    height = output['streams'][0]['height']
    width = output['streams'][0]['width']
    return width, height


def getChannels(app, message):
    data = fetch_data(iptv_link)
    channelsList = ""
    for i in data:
        channelsList += f"{i}\n"
    message.reply_text(text=CHANNELS_TEXT.format(channelsList))


def get_readable_time(seconds: int) -> str:
    result = ''
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f'{days}d'
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f'{hours}h'
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f'{minutes}m'
    seconds = int(seconds)
    result += f'{seconds}s'
    return result

def multi_rec(app, message):
    # cmd = /multirec Hungama 00:00:10 | Test File
    cmd = message.text.split("|")
    tg_cmd, channel, duration = cmd[0].strip().split(" ")
    iptv_data = fetch_data(iptv_link)

    if channel not in iptv_data:
        message.reply_text(f"{channel} not Available")
        return
    if "|" in message.text:
        title = cmd[1].strip()
    else:
        title = "TEST FILE"

    video_opts = 'ffmpeg -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -i'
    video_opts_2 = '-to'
    video_opts_3 = '-map 0:v:0 -map 0:a'
    audio = "-".join(iptv_data[channel][0]["audio"])
    filename = f'[{GROUP_TAG}] {iptv_data[channel][0]["title"]} - {title} - {ind_time()} [{iptv_data[channel][0]["quality"]}] [x264] {iptv_data[channel][0]["ripType"]} [{audio}].mkv'

    streamUrl = iptv_data[channel][0]["link"]

    ffmpeg_cmd = video_opts.split() + \
        [streamUrl] + video_opts_2.split() + [duration] + \
        video_opts_3.split() + [filename]
    start_rec_time = time.time()

    msg = message.reply_text(f"Recording In Progress...")
    subprocess.run(ffmpeg_cmd)

    end_rec_time = time.time()

    if os.path.exists(filename) == False:
        msg.edit(f"Recording Failed")
        return

    msg.edit(f"{channel} Recorded Successfully")
    # app.send_video(video=filename, chat_id=message.from_user.id,
    #                caption=f"<code>{filename}</code>")

    destination = f'TV-DL/{iptv_data[channel][0]["title"]}'

    msg.edit(f"Uploading...")

    size = humanbytes(os.path.getsize(filename))

    # destination = f"/TATAPLAY WEB-DL/CatchupData/{channel_name}"
    duration = get_duration(filename)
    thumb = get_thumbnail(filename, "", duration / 2)
    start_time = time.time()
    caption = DL_DONE_MSG.format(
            "Recording", get_readable_time(end_rec_time - start_rec_time), filename, iptv_data[channel][0]["title"], size)

    app.send_video(video=filename, chat_id=message.from_user.id, caption=caption, progress=progress_for_pyrogram, progress_args=(
            "Uploading... \n", msg, start_time), thumb=thumb, duration=duration, width=1280, height=720)
    msg.delete()

    os.remove(filename)