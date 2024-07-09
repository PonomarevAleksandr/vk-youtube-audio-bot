import json
import logging
import uuid
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, CallbackQuery, InlineKeyboardButton, InputMediaPhoto, InputMediaAnimation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bson import ObjectId
from fluentogram import TranslatorRunner

from main import t_hub
from src import callbacks
from src.callbacks import LanguageSwitcher, PlaylistNavigate, NewSongs, Start, Help, \
    VkDownloadAudio, ChannelsAdmin, RemoveSponsor, SponsorList, AddSponsor
from src.models.user import User
from src.utils.FSMState import AddSponsorFSM, EditSponsorFSM
from src.utils.db import db, rdb
from src.utils.db import raw_db
from src.utils.vk import audio_list, VK

router = Router()


async def start_message(locale, bot, user_id):

    keyboard = InlineKeyboardBuilder()
    keyboard.row(types.InlineKeyboardButton(text=locale.new(), callback_data=NewSongs(chart_type='news').pack()))
    keyboard.add(types.InlineKeyboardButton(text=locale.help(), callback_data=Help().pack()))
    keyboard.add(types.InlineKeyboardButton(text=locale.top(), callback_data=NewSongs(chart_type='top').pack()))

    await bot.send_animation(chat_id=user_id,
                             animation='https://telegra.ph/file/41a69dade6e7321e40971.mp4',
                             reply_markup=keyboard.as_markup())


@router.callback_query(Help.filter())
async def help_callback(callback_query: types.CallbackQuery, bot: Bot, locale: TranslatorRunner):


    await callback_query.answer('?')
    keyboard = InlineKeyboardBuilder()
    keyboard.row(types.InlineKeyboardButton(text=locale.menu(),
                                            callback_data=Start().pack()))
    await bot.edit_message_caption(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                   caption=locale.text.help(), parse_mode='html', reply_markup=keyboard.as_markup())

#check to subscribe
async def check_all_subs(bot: Bot, user_id, channels_list_map):
    for channel_info in channels_list_map:
        user_channel_status = await bot.get_chat_member(chat_id=channel_info['channel_id'], user_id=user_id)
        if user_channel_status.status not in ['administrator', 'owner', 'member', 'creator']:
            return False
    return True


@router.callback_query(Start.filter())
async def start_callback(callback_query: types.CallbackQuery, bot: Bot, locale: TranslatorRunner):
    channels_cursor = await db.channels.find({})
    channels_list_map = list(
        map(lambda channel: {'channel_id': channel.channel_id, 'url': channel.url, 'name': channel.name},
            channels_cursor))
    all_subscribed = await check_all_subs(bot, callback_query.from_user.id, channels_list_map)
    if all_subscribed:
        keyboard = InlineKeyboardBuilder()
        keyboard.row(types.InlineKeyboardButton(text=locale.new(), callback_data=NewSongs(chart_type='news').pack()))
        keyboard.add(types.InlineKeyboardButton(text=locale.help(), callback_data=Help().pack()))
        keyboard.add(types.InlineKeyboardButton(text=locale.top(), callback_data=NewSongs(chart_type='top').pack()))
        media = InputMediaAnimation(media='https://telegra.ph/file/41a69dade6e7321e40971.mp4', filename='start_gif')
        await bot.edit_message_media(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                     media=media,
                                     reply_markup=keyboard.as_markup())
    else:
        markup = InlineKeyboardBuilder()
        for channel in channels_list_map:
            markup.row(InlineKeyboardButton(text=channel['name'],
                                            url=channel['url'].replace(';', ':')))
        markup.row(InlineKeyboardButton(text=locale.checksub(), callback_data=Start().pack()))

        await bot.edit_message_caption(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                     caption=locale.checksub_fail(),
                                     reply_markup=markup.as_markup())


@router.callback_query(LanguageSwitcher.filter())
async def change_language(callback_query: CallbackQuery, bot: Bot, callback_data: LanguageSwitcher,
                          locale: TranslatorRunner):
    await callback_query.answer(locale.menu())

    language_code = str(callback_data.lang_select)
    await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)
    await db.users.update_one(f={'id': callback_query.from_user.id}, s={'language_code': language_code}, upsert=True)
    locale = t_hub.get_translator_by_locale(language_code)
    await start_message(locale, bot, callback_query.from_user.id)


@router.callback_query(PlaylistNavigate.filter())
async def navigate_callback(query: CallbackQuery, bot: Bot, user: User, callback_data: PlaylistNavigate,
                            locale: TranslatorRunner):
    page = round(callback_data.offset / 10) + 1

    cache = await raw_db['vk_cache'].find_one({'_id': ObjectId(callback_data.cache_id)})

    if cache['data'].get('items'):
        data_key = 'items'
    else:
        data_key = 'audios'

    builder = audio_list(callback_data.cache_id, cache['data'][data_key], callback_data.offset)

    btn_prev_page = InlineKeyboardButton(
        text=locale.back(),
        callback_data=callbacks.PlaylistNavigate(cache_id=callback_data.cache_id, index=callback_data.offset - 10,
                                                 offset=callback_data.offset - 10).pack())

    btn_current_page = InlineKeyboardButton(
        text=str(page),
        callback_data=callbacks.Plug().pack())

    btn_next_page = InlineKeyboardButton(
        text=locale.next(),
        callback_data=callbacks.PlaylistNavigate(cache_id=callback_data.cache_id, index=callback_data.offset + 10,
                                                 offset=callback_data.offset + 10).pack())

    btn_back = InlineKeyboardButton(
        text=locale.menu(),
        callback_data=Start().pack())

    navigate_row = []

    if callback_data.offset > 0:
        navigate_row.append(btn_prev_page)

    navigate_row.append(btn_current_page)

    if callback_data.offset + 10 < len(cache['data'][data_key]):
        navigate_row.append(btn_next_page)

    if len(navigate_row) > 0:
        builder.row(*navigate_row)
    builder.row(btn_back)
    await bot.edit_message_reply_markup(
        message_id=query.message.message_id,
        chat_id=query.from_user.id,
        reply_markup=builder.as_markup())

    await query.answer()

# VK_playlists (top, news)
@router.callback_query(NewSongs.filter())
async def handle_callback(callback_query: CallbackQuery, bot: Bot, callback_data: NewSongs, locale: TranslatorRunner):
    await callback_query.answer(text=locale.loading())

    if callback_data.chart_type == "news":
        params = {"example_params": 0}
        result = await VK.call("example.method", params=params)
        builder = audio_list(str(result['_id']), result['data']['items'])

        page = 1
        btn_current_page = InlineKeyboardButton(
            text=f"{page}",
            callback_data=callbacks.Plug().pack())

        btn_next_page = InlineKeyboardButton(
            text=locale.next(),
            callback_data=callbacks.PlaylistNavigate(cache_id=str(result['_id']), offset=10).pack())

        btn_back = InlineKeyboardButton(
            text=locale.menu(),
            callback_data=Start().pack())

        navigate_row = []

        if 10 < len(result['data']['items']):
            navigate_row.append(btn_current_page)
            navigate_row.append(btn_next_page)

        if navigate_row:
            builder.row(*navigate_row)

        builder.row(btn_back)
        caption = "Новинки 🔥" if callback_data.chart_type == 'news' else "Топ-Чарт ⭐"

        await bot.edit_message_caption(
            caption=caption,
            message_id=callback_query.message.message_id,
            chat_id=callback_query.from_user.id,
            reply_markup=builder.as_markup())
    elif callback_data.chart_type == "top":
        params = {"example.params": 0}

        result = await VK.call("example.method", params=params)
        builder = audio_list(str(result['_id']), result['data']['items'])

        page = 1
        btn_current_page = InlineKeyboardButton(
            text=f"{page}",
            callback_data=callbacks.Plug().pack())

        btn_next_page = InlineKeyboardButton(
            text=locale.next(),
            callback_data=callbacks.PlaylistNavigate(cache_id=str(result['_id']), offset=10).pack())

        btn_back = InlineKeyboardButton(
            text=locale.menu(),
            callback_data=Start().pack())

        navigate_row = []

        if 10 < len(result['data']['items']):
            navigate_row.append(btn_current_page)
            navigate_row.append(btn_next_page)

        if navigate_row:
            builder.row(*navigate_row)

        builder.row(btn_back)
        caption = "Новинки 🔥" if str(result['_id']) == 'news' else "Топ-Чарт ⭐"

        await bot.edit_message_caption(
            caption=caption,
            message_id=callback_query.message.message_id,
            chat_id=callback_query.from_user.id,
            reply_markup=builder.as_markup())

#VK download from playlists
@router.callback_query(VkDownloadAudio.filter())
async def on_track_callback(callback_query: types.CallbackQuery, callback_data: VkDownloadAudio, locale: TranslatorRunner,
                            bot: Bot):
    cached_result = await raw_db.vk_cache.find_one({'_id': ObjectId(callback_data.cache_id)})
    if cached_result:
        try:
            tracks = cached_result['data']['items']
        except KeyError:
            tracks = cached_result['data']['audios']
        track = tracks[callback_data.index]
        try:
            photo = track['album']['thumb']['photo_600']
        except:
            photo = None


        task_info = {
            'type': 'vk',
            'task_id': str(uuid.uuid4().hex),
            'user_id': callback_query.from_user.id,
            'track': {
                'url': track['url'],
                'artist': track['artist'],
                'title': track['title'],
                'photo': photo,
                'duration': track['duration'],
                'owner_id': track['owner_id'],
                'audio_id': track['id'],
                'caption': locale.ads(),

            }
        }

        rdb.lpush('tasks', json.dumps(task_info))

#Admin-panel
@router.callback_query(ChannelsAdmin.filter())
async def channels_admin(callback_query: types.CallbackQuery, callback_data: ChannelsAdmin, bot: Bot):
    info = await db.channels.find_one({'channel_id': callback_data.channel_id})
    await callback_query.answer(info.name)
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text='Удалить Спонсора',
                                      callback_data=RemoveSponsor(channel_id=int(callback_data.channel_id),
                                                                                           ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить Имя',
                                      callback_data=AddSponsor(edit='name', channel_id=callback_data.channel_id,
                                                                                    ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить ID',
                                      callback_data=AddSponsor(edit='id', channel_id=callback_data.channel_id,
                                                                                   ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить url',
                                      callback_data=AddSponsor(edit='url', channel_id=callback_data.channel_id,
                                                                                    ).pack()))
    keyboard.row(InlineKeyboardButton(text='Назад', callback_data=SponsorList().pack()))
    await bot.edit_message_text(chat_id=callback_query.from_user.id, text=f'Спонсор : {info.name}\n\n'
                                                                 f'Url : {info.url}\n'
                                                                 f'Channel_id : {callback_data.channel_id}',
                                message_id=callback_query.message.message_id,
                                reply_markup=keyboard.as_markup())

#Admin-panel
@router.callback_query(AddSponsor.filter())
async def channels_admin(callaback_query: types.CallbackQuery, callback_data: AddSponsor, bot: Bot, state: FSMContext):
    channel_id = await db.channels.find_one({'channel_id': callback_data.channel_id})

    if callback_data.edit == 'no':
        res = await bot.edit_message_text(chat_id=callaback_query.from_user.id, text='Укажите название:',
                                          message_id=callaback_query.message.message_id)
        await state.set_state(AddSponsorFSM.send_name)

    elif callback_data.edit == 'name':
        res = await bot.edit_message_text(chat_id=callaback_query.from_user.id, text='Укажите название:',
                                          message_id=callaback_query.message.message_id)
        await state.set_state(EditSponsorFSM.edit_name)

    elif callback_data.edit == 'id':
        res = await bot.edit_message_text(chat_id=callaback_query.from_user.id, text='Укажите ID канала:',
                                          message_id=callaback_query.message.message_id)
        await state.set_state(EditSponsorFSM.edit_chanel_id)
    elif callback_data.edit == 'url':
        res = await bot.edit_message_text(chat_id=callaback_query.from_user.id, text='Укажите url:',
                                          message_id=callaback_query.message.message_id)
        await state.set_state(EditSponsorFSM.edit_url)

    if edit == 'no':
        await state.update_data(message_id=res.message_id)
    else:
        await state.update_data(channel_id=channel_id, name=channel_id.name, url=channel_id.url,
                                message_id=res.message_id)


#Admin-panel
@router.callback_query(SponsorList.filter())
async def channels_admin(callback_query: types.CallbackQuery, bot: Bot, locale: TranslatorRunner):
    channels_cursor = await db.channels.find({})
    channels_list_map = list(
        map(lambda channel: {'channel_id': channel.channel_id, 'url': channel.url, 'name': channel.name},
            channels_cursor))
    markup = InlineKeyboardBuilder()
    for channel in channels_list_map:
        markup.row(InlineKeyboardButton(text=channel['name'],
                                        callback_data=ChannelsAdmin(channel_id=channel['channel_id'],
                                                                    url=channel['url'], name=channel['name']).pack()))
    markup.row(InlineKeyboardButton(text='Добавить спонсора', callback_data=AddSponsor(edit='no').pack()))

    await bot.edit_message_text(chat_id=callback_query.from_user.id, text="Админ панель:",
                                reply_markup=markup.as_markup(),
                                message_id=callback_query.message.message_id)


logging.basicConfig(level=logging.INFO)

#Admin-panel
@router.callback_query(RemoveSponsor.filter())
async def remove_sponsor(callback_query: types.CallbackQuery, bot: Bot, callback_data: RemoveSponsor):
    try:
        result = await db.channels.delete_one({'channel_id': callback_data.channel_id})
        if result.deleted_count > 0:
            logging.info(f'Удалено документов: {result.deleted_count}.')
        else:
            logging.info(f'Нет документов для удаления. : {result}')
    except Exception as e:
        logging.error(f'Ошибка при удалении документов: {e}')
    channels_cursor = await db.channels.find({})
    channels_list_map = list(
        map(lambda channel: {'channel_id': channel.channel_id, 'url': channel.url, 'name': channel.name},
            channels_cursor))
    markup = InlineKeyboardBuilder()
    for channel in channels_list_map:
        markup.row(InlineKeyboardButton(text=channel['name'],
                                        callback_data=ChannelsAdmin(channel_id=channel['channel_id'],
                                                                    url=channel['url'], name=channel['name']).pack()))
    markup.row(InlineKeyboardButton(text='Добавить спонсора', callback_data=AddSponsor(edit='no').pack()))

    await bot.edit_message_text(chat_id=callback_query.from_user.id, text="Админ панель:", reply_markup=markup.as_markup(),
                                message_id=callback_query.message.message_id)
