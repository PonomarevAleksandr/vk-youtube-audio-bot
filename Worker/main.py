import asyncio
import json
import os
import random
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process
import aiohttp
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.types import FSInputFile
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3, error
from yt_dlp import YoutubeDL
from config import load_env
from utils.db import db, rdb

load_env()


async def get_task(worker_id: str):
    try:

        destination_queue = f"tasks:processing:{worker_id}"
        task_data = rdb.brpoplpush(f'tasks', destination_queue, 0)

        if task_data:

            task = json.loads(task_data.decode())
            lock_key = f"lock-{task['task_id']}"
            acquired_lock = rdb.set(lock_key, worker_id, nx=True, ex=10)

            if acquired_lock:
                rdb.delete(lock_key)
                rdb.lrem(destination_queue, 1, task_data)
                return task

    except Exception as e:
        print(e, traceback.format_exc())

    return None


def add_cover(file_path, image_path):
    audio = MP3(file_path, ID3=ID3)

    try:
        audio.add_tags()
    except error:
        audio.delete()
        audio.save()
        audio.add_tags()

    with open(image_path, 'rb') as albumart:
        audio.tags.add(
            APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc=u'Cover',
                data=albumart.read()
            )
        )
    audio.save()

#VK DOWNLOAD
async def download(track_info, download_folder='files'):
    bot_token = os.getenv("BOT_TOKEN")
    api_server = TelegramAPIServer.from_base('http://tgapi:8081/')
    session = AiohttpSession(api=api_server)
    bot = Bot(token=bot_token, session=session)
    try:
        channel_id = random.choice(tuple(os.getenv("CHANNELS_LIST").split(','))).strip()
        file_name = f"{track_info['track'].get('artist')} - {track_info['track'].get('title')}.mp3"
        file_path = os.path.join(download_folder, file_name)
        download_url = track_info['track'].get('url')
        cover_name = f"{track_info['track'].get('artist')} - {track_info['track'].get('title')}.jpg"
        cover_patch = os.path.join(download_folder, cover_name)

        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status == 200:
                    with open(file_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            f.write(chunk)
            if track_info['track'].get('photo'):
                cover_url = track_info['track'].get('photo')
                async with session.get(cover_url) as response:
                    if response.status == 200:
                        with open(cover_patch, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                f.write(chunk)

        artist = track_info['track'].get('artist')
        title = track_info['track'].get('title')
        if track_info['track'].get('photo'):

            thumb = FSInputFile(cover_patch, filename='cover')
            input_file = FSInputFile(file_path, filename=f"{artist} - {title}.mp3")
            res = await bot.send_audio(chat_id=channel_id, audio=input_file, title=title, performer=artist,
                                       thumbnail=thumb,
                                       parse_mode='html')
        else:
            input_file = FSInputFile(file_path, filename=f"{artist} - {title}.mp3")
            res = await bot.send_audio(chat_id=channel_id, audio=input_file, title=title, performer=artist,
                                       duration=track_info['track'].get('duration'),
                                       parse_mode='html')


        await bot.copy_message(
            from_chat_id=channel_id,
            chat_id=track_info['user_id'],
            message_id=res.message_id, caption=track_info['track'].get('caption'), parse_mode='html'
        )
        db['tracks'].insert_one({
            'owner_id': track_info['track'].get('owner_id'),
            'audio_id': track_info['track'].get('audio_id'),
            'channel_id': channel_id,
            'message_id': res.message_id,
            'artist': artist,
            'title': title
        })
        print(f"Трек {file_name} успешно скачан и добавлен в базу данных.")
        os.remove(file_path)

    except Exception as e:
        print(f'Ошибка при скачивании трека: {e}', traceback.format_exc())
        return False
    await session.close()


async def download_thumbnail(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    async with aiohttp.ClientSession() as session_thumb:
        async with session_thumb.get(url) as response:
            if response.status == 200:
                with open(path, 'wb') as f:
                    f.write(await response.read())


def download_audio(video_url, ydl_opts):
    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=False)
        video_title = info_dict.get('title', 'Unknown Title')
        file_path = ydl.prepare_filename(info_dict)
        video_duration = info_dict.get('duration', 0)
        file_path_mp3 = file_path.replace('.webm', '.mp3')
        try:
            os.remove(file_path)
        except:
            pass

        if not os.path.exists(file_path_mp3):
            ydl.download([video_url])
            try:
                os.remove(file_path)
            except:
                pass
        return file_path_mp3, video_title, video_duration



async def download_youtube(task, download_folder='files'):
    bot_token = os.getenv("BOT_DOWNLOAD_TOKEN")
    api_server = TelegramAPIServer.from_base('http://tgapi:8081/')
    session = AiohttpSession(api=api_server)
    bot = Bot(token=bot_token, session=session)
    cover_folder = 'files/covers'
    try:
        channel_id = random.choice(tuple(os.getenv("CHANNELS_LIST").split(','))).strip()
        message_text = task['text']
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'{download_folder}/%(title)s.%(ext)s',
            'noplaylist': True,
            'audioformat': 'mp3',
            'keepvideo': True,
            'verbose': True,


        }
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(message_text, download=False)
            video_id = info_dict.get('id')

        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        with ThreadPoolExecutor(max_workers=10) as executor:
            future = executor.submit(download_audio, message_text, ydl_opts)
            file_path_mp3, video_title, video_duration = future.result()

        thumbnail_url = f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'
        thumbnail_path = f'{cover_folder}/{video_title}.jpg'
        await download_thumbnail(thumbnail_url, thumbnail_path)
        thumb = FSInputFile(thumbnail_path, filename=f"{video_title}.jpg")

        input_file = FSInputFile(file_path_mp3, filename=f"{video_title}.mp3")

        if os.path.exists(file_path_mp3):
            # await bot.delete_message(chat_id=task['chat_id'], message_id=int(task['message_id']))
            res = await bot.send_audio(chat_id=channel_id, audio=input_file, title=video_title, duration=video_duration,
                                       thumbnail=thumb)

            bot_token = os.getenv("BOT_TOKEN")
            api_server = TelegramAPIServer.from_base('http://tgapi:8081/')
            session = AiohttpSession(api=api_server)
            bot = Bot(token=bot_token, session=session)

            await bot.copy_message(
                from_chat_id=channel_id,
                chat_id=task['chat_id'],
                message_id=res.message_id,
                caption=task['caption'], parse_mode='html')

            db['videos'].insert_one({
                'video_id': video_id,
                'channel_id': channel_id,
                'message_id': res.message_id,
            })
        else:
            print(f"Файл {file_path_mp3} не найден.")

        # DELETE FILES
        os.remove(file_path_mp3)
        os.remove(thumbnail_path)


        print(f"Аудио {video_title} успешно скачано и отправлено.")

    except Exception as e:
        print(f'Ошибка при скачивании аудио: {e}', traceback.format_exc())
    await session.close()
    return False


async def send_video(task):
    bot_token = os.getenv("BOT_TOKEN")
    api_server = TelegramAPIServer.from_base('http://tgapi:8081/')
    session = AiohttpSession(api=api_server)
    bot = Bot(token=bot_token, session=session)
    ydl_opts = {
        'format': 'bestaudio/best',
    }
    message_text = task['text']
    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(message_text, download=False)
        video_id = info_dict.get('id', None)
    print(f"Ищем видео с ID: {video_id}")
    video = await db['videos'].find_one({
        'video_id': video_id
    })
    print(f"Результат поиска: {video}")

    if video:
        print(f"Видео найдено в кэше: {video}")
        channel_id = video['channel_id']
        channel_message_id = video['message_id']
        # await bot.delete_message(chat_id=task['chat_id'], message_id=int(task['message_id']))
        await bot.copy_message(
            from_chat_id=channel_id,
            chat_id=task['chat_id'],
            message_id=channel_message_id,
            caption=task['caption'], parse_mode='html')
    else:
        await download_youtube(task)
    await session.close()


async def send_track(task):
    bot_token = os.getenv("BOT_TOKEN")
    api_server = TelegramAPIServer.from_base('http://tgapi:8081/')
    session = AiohttpSession(api=api_server)
    bot = Bot(token=bot_token, session=session)
    track = await db['tracks'].find_one({
        'owner_id': task['track'].get('owner_id'),
        'audio_id': task['track'].get('audio_id')
    })

    if track:
        channel_id = track['channel_id']
        channel_message_id = track['message_id']

        await bot.copy_message(
            from_chat_id=channel_id,
            chat_id=task['user_id'],
            message_id=channel_message_id,
            caption=task['track'].get('caption'), parse_mode='html'
        )
    else:
        await download(task)
    await session.close()


def worker(worker_id: str):
    async def worker_async(worker_id: str):
        while True:
            task = await get_task(worker_id)
            if task is not None:
                if task['type'] == 'youtube':
                    await send_video(task)
                else:
                    await send_track(task)
            await asyncio.sleep(1)

    asyncio.run(worker_async(worker_id))


if __name__ == '__main__':

    processes = []

    for i in range(10):
        worker_id = str(uuid.uuid4().hex)
        processes.append(Process(target=worker, args=(worker_id,)))

    try:
        for p in processes:
            p.start()
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        for p in processes:
            p.terminate()
