import json
import logging
import re
import traceback
import uuid


from aiogram import Router, Bot, types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, InputFile, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluentogram import TranslatorRunner


from src import callbacks
from src.callbacks import LanguageSwitcher, NewSongs, Start, Help, ChannelsAdmin, AddSponsor, RemoveSponsor, SponsorList

from src.models.user import User
from src.utils.FSMState import AddSponsorFSM, EditSponsorFSM
from src.utils.db import db, rdb

from src.utils.vk import VK, audio_list

router = Router()


async def check_all_subs(bot: Bot, user_id, channels_list_map):
    for channel_info in channels_list_map:
        user_channel_status = await bot.get_chat_member(chat_id=channel_info['channel_id'], user_id=user_id)
        if user_channel_status.status not in ['administrator', 'owner', 'member', 'creator']:
            return False
    return True

#Create users.txt file
@router.message(Command('users'))
async def export_users_command(message: Message, bot: Bot):
    if message.from_user.id == 103095353:
        users_cursor = await db.users.find({})
        user_list_map = list(
            map(lambda user: {'user_id': user.id},
                users_cursor))
        txt = ''
        for user in user_list_map:
            txt += f"{user['user_id']}\n"

        with open('users.txt', 'w') as f:
            f.write(txt)

        await bot.send_document(chat_id=message.chat.id, document=FSInputFile('users.txt'))

@router.message(Command('start'))
async def start_command(message: Message, bot: Bot, locale: TranslatorRunner):
    channels_cursor = await db.channels.find({})
    channels_list_map = list(
        map(lambda channel: {'channel_id': channel.channel_id, 'url': channel.url, 'name': channel.name},
            channels_cursor))
    all_subscribed = await check_all_subs(bot, message.from_user.id, channels_list_map)
    if all_subscribed:
        keyboard = InlineKeyboardBuilder()
        keyboard.row(types.InlineKeyboardButton(text=locale.new(), callback_data=NewSongs(chart_type='news').pack()))
        keyboard.add(types.InlineKeyboardButton(text=locale.help(), callback_data=Help().pack()))
        keyboard.add(types.InlineKeyboardButton(text=locale.top(), callback_data=NewSongs(chart_type='top').pack()))

        await bot.send_animation(chat_id=message.from_user.id,
                                 animation='https://telegra.ph/file/41a69dade6e7321e40971.mp4',
                                 reply_markup=keyboard.as_markup())
    else:
        markup = InlineKeyboardBuilder()
        for channel in channels_list_map:
            markup.row(InlineKeyboardButton(text=channel['name'],
                                            url=channel['url'].replace(';', ':')))
        markup.row(InlineKeyboardButton(text='✅ Проверить Подписку', callback_data=Start().pack()))

        await bot.send_animation(chat_id=message.from_user.id,
                                 animation='https://telegra.ph/file/41a69dade6e7321e40971.mp4',
                                 caption=locale.subscheck(),
                                 reply_markup=markup.as_markup())


@router.message(Command('help'))
async def help_command(message: Message, bot: Bot, locale: TranslatorRunner):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(types.InlineKeyboardButton(text=locale.menu(),
                                            callback_data=Start().pack()))
    await bot.send_animation(chat_id=message.from_user.id,
                             animation='https://telegra.ph/file/92e0e6e31518fd3b9c61e.gif',
                             caption=locale.text.help(), parse_mode='html', reply_markup=keyboard.as_markup())


@router.message(Command('language'))
async def language_switch(message: Message, bot: Bot, locale: TranslatorRunner):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text='RU 🇷🇺', callback_data=LanguageSwitcher(lang_select='ru').pack()))
    keyboard.add(InlineKeyboardButton(text='EN 🇬🇧', callback_data=LanguageSwitcher(lang_select='en').pack()))
    keyboard.add(InlineKeyboardButton(text='UZ 🇺🇿', callback_data=LanguageSwitcher(lang_select='uz').pack()))
    keyboard.add(InlineKeyboardButton(text='UA 🇺🇦', callback_data=LanguageSwitcher(lang_select='uk').pack()))
    keyboard.add(InlineKeyboardButton(text='KZ 🇰🇿', callback_data=LanguageSwitcher(lang_select='kk').pack()))

    await bot.send_message(chat_id=message.from_user.id, text=locale.langchoose(), reply_markup=keyboard.as_markup())

#Admin-panel
@router.message(Command('admin'))
async def admin_panel(message: types.Message, locale: TranslatorRunner):
    if message.from_user.id == 103095353:
        channels_cursor = await db.channels.find({})
        channels_list_map = list(
            map(lambda channel: {'channel_id': channel.channel_id, 'url': channel.url, 'name': channel.name},
                channels_cursor))
        markup = InlineKeyboardBuilder()
        for channel in channels_list_map:
            markup.row(InlineKeyboardButton(text=channel['name'],
                                            callback_data=ChannelsAdmin(channel_id=channel['channel_id']
                                                                        ).pack()))
        markup.row(InlineKeyboardButton(text='Добавить спонсора', callback_data=AddSponsor(edit='no').pack()))

        await message.answer("Админ панель:", reply_markup=markup.as_markup())



#Admin-panel
@router.message(EditSponsorFSM.edit_name)
async def change_name(message: types.Message, bot: Bot, state: FSMContext):
    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)
    data = await state.get_data()
    try:
        result = await db.channels.update_one(
            {'channel_id': int(data.get('channel_id'))},
            {'name': message.text}
        )
        if result.modified_count > 0:
            logging.info('Документ успешно обновлен.')
        else:
            logging.info('Документ для обновления не найден.')
    except Exception as e:
        logging.error(f'Ошибка при обновлении документа: {e}')

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text='Удалить Спонсора',
                                      callback_data=RemoveSponsor(channel_id=data.get('channel_id'),
                                                                                           ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить Имя',
                                      callback_data=AddSponsor(edit='name', channel_id=data.get('channel_id'),
                                                                                    ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить ID',
                                      callback_data=AddSponsor(edit='id', channel_id=data.get('channel_id'),
                                                                                   ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить url',
                                      callback_data=AddSponsor(edit='url', channel_id=data.get('channel_id'),
                                                                                   ).pack()))
    keyboard.row(InlineKeyboardButton(text='Назад', callback_data=SponsorList().pack()))
    await bot.edit_message_text(chat_id=message.from_user.id, text=f'Спонсор : {data.get('name')}\n\n'
                                                                   f'Url : {data.get('url')}\n'
                                                                   f'Channel_id : {data.get('channel_id')}',
                                message_id=data.get('message_id'),
                                reply_markup=keyboard.as_markup())
    await state.clear()

#Admin-panel
@router.message(EditSponsorFSM.edit_chanel_id)
async def change_channel_id(message: types.Message, bot: Bot, state: FSMContext):
    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)
    data = await state.get_data()
    try:
        result = await db.channels.update_one(
            {'channel_id': int(data.get('channel_id'))},
            {'channel_id': message.text}
        )
        if result.modified_count > 0:
            logging.info('Документ успешно обновлен.')
        else:
            logging.info('Документ для обновления не найден.')
    except Exception as e:
        logging.error(f'Ошибка при обновлении документа: {e}')

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text='Удалить Спонсора',
                                      callback_data=RemoveSponsor(channel_id=data.get('channel_id'),
                                                                  ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить Имя',
                                      callback_data=AddSponsor(edit='name', channel_id=data.get('channel_id'),
                                                               ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить ID',
                                      callback_data=AddSponsor(edit='id', channel_id=data.get('channel_id'),
                                                               ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить url',
                                      callback_data=AddSponsor(edit='url', channel_id=data.get('channel_id'),
                                                               ).pack()))
    keyboard.row(InlineKeyboardButton(text='Назад', callback_data=SponsorList().pack()))
    await bot.edit_message_text(chat_id=message.from_user.id, text=f'Спонсор : {data.get('name')}\n\n'
                                                                   f'Url : {data.get('url')}\n'
                                                                   f'Channel_id : {data.get('channel_id')}',
                                message_id=data.get('message_id'),
                                reply_markup=keyboard.as_markup())
    await state.clear()

#Admin-panel
@router.message(EditSponsorFSM.edit_url)
async def change_url(message: types.Message, bot: Bot, state: FSMContext):
    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)
    data = await state.get_data()

    try:
        result = await db.channels.update_one(
            {'channel_id': int(data.get('channel_id'))},
            {'url': message.text.replace(':', ';')}
        )
        if result.modified_count > 0:
            logging.info('Документ успешно обновлен.')
        else:
            logging.info('Документ для обновления не найден.')
    except Exception as e:
        logging.error(f'Ошибка при обновлении документа: {e}')

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text='Удалить Спонсора',
                                      callback_data=RemoveSponsor(channel_id=data.get('channel_id'),
                                                                  ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить Имя',
                                      callback_data=AddSponsor(edit='name', channel_id=data.get('channel_id'),
                                                               ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить ID',
                                      callback_data=AddSponsor(edit='id', channel_id=data.get('channel_id'),
                                                               ).pack()))
    keyboard.row(InlineKeyboardButton(text='Изменить url',
                                      callback_data=AddSponsor(edit='url', channel_id=data.get('channel_id'),
                                                               ).pack()))
    keyboard.row(InlineKeyboardButton(text='Назад', callback_data=SponsorList().pack()))
    await bot.edit_message_text(chat_id=message.from_user.id, text=f'Спонсор : {data.get('name')}\n\n'
                                                                   f'Url : {data.get('url')}\n'
                                                                   f'Channel_id : {data.get('channel_id')}',
                                message_id=data.get('message_id'),
                                reply_markup=keyboard.as_markup())
    await state.clear()

#Admin-panel
@router.message(AddSponsorFSM.send_name)
async def upload_name(message: types.Message, bot: Bot, state: FSMContext):
    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)
    data = await state.get_data()
    res = await bot.edit_message_text(chat_id=message.from_user.id, text='Укажите id канала:',
                                      message_id=int(data.get('message_id')))
    await state.set_state(AddSponsorFSM.send_chanel_id)
    await state.update_data(message_id=res.message_id, name=message.text)

#Admin-panel
@router.message(AddSponsorFSM.send_chanel_id)
async def upload_channel_id(message: types.Message, bot: Bot, state: FSMContext):
    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)
    data = await state.get_data()
    res = await bot.edit_message_text(chat_id=message.from_user.id, text='Укажите url канала:',
                                      message_id=int(data.get('message_id')))
    await state.set_state(AddSponsorFSM.send_url)
    await state.update_data(message_id=res.message_id)
    await state.update_data(name=data.get('name'))
    await state.update_data(channel_id=message.text)

#Admin-panel
@router.message(AddSponsorFSM.send_url)
async def upload_url(message: types.Message, bot: Bot, state: FSMContext):
    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)

    data = await state.get_data()
    await db.channels.insert_one({'channel_id': int(data.get('channel_id')), 'name': str(data.get('name')),
                                  'url': str(message.text.replace(':', ';'))})
    channels_cursor = await db.channels.find({})
    channels_list_map = list(
        map(lambda channel: {'channel_id': channel.channel_id, 'url': channel.url, 'name': channel.name},
            channels_cursor))
    markup = InlineKeyboardBuilder()
    for channel in channels_list_map:
        markup.row(InlineKeyboardButton(text=channel['name'],
                                        callback_data=ChannelsAdmin(channel_id=channel['channel_id'],
                                                                    ).pack()))
    markup.row(InlineKeyboardButton(text='Добавить спонсора', callback_data=AddSponsor(edit='no').pack()))

    await bot.edit_message_text(chat_id=message.from_user.id, text="Админ панель:", reply_markup=markup.as_markup(),
                                message_id=int(data.get('message_id')))
    await state.clear()

#VK,YT SEARCH
@router.message()
async def search_music(message: Message, bot: Bot, user: User, locale: TranslatorRunner):
    channels_cursor = await db.channels.find({})
    channels_list_map = list(
        map(lambda channel: {'channel_id': channel.channel_id, 'url': channel.url, 'name': channel.name},
            channels_cursor))
    all_subscribed = await check_all_subs(bot, message.from_user.id, channels_list_map)
    if all_subscribed:
        #Youtube
        if re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+', message.text):
            res = await bot.send_message(chat_id=message.from_user.id, text='Ожидайте')
            task = {'type': 'youtube', 'task_id': str(uuid.uuid4().hex),
                    'chat_id': message.chat.id, 'text': message.text, 'caption': locale.ads(),
                    'message_id': res.message_id,
                    }
            serialized_task = json.dumps(task)
            rdb.lpush('tasks', serialized_task)
        #VK
        else:
            try:
                result = await VK.call("example.method", {"q": message.text, "count": 200, "offset": 0})

            except Exception as e:
                print(f'error vk.search {e}: ', traceback.format_exc())


            else:

                if "error" in result:

                    if result['error']['error_code'] == 14:
                        print('captcha error: ', result)
                    else:
                        print('other error: ', result)

                else:

                    try:
                        cache_id = str(result['_id'])

                        builder = audio_list(cache_id, result['data']['items'])

                        btn_current_page = InlineKeyboardButton(text='1',
                                                                callback_data=callbacks.Plug().pack())

                        btn_next_page = InlineKeyboardButton(text=locale.next(),
                                                             callback_data=callbacks.PlaylistNavigate(cache_id=cache_id,
                                                                                                      offset=10).pack())

                        navigate_row = [btn_current_page]

                        if len(result['data']['items']) == 0:
                            print(f'search error e: ', traceback.format_exc())

                        if len(result['data']['items']) > 10:
                            navigate_row.append(btn_next_page)

                        if len(navigate_row) > 0:
                            builder.row(*navigate_row)

                        await message.delete()
                        photo = False

                        for audio in result['data']['items']:

                            for photo_size in ['600', '300']:
                                try:
                                    photo = audio["album"]["thumb"][f"photo_{photo_size}"]
                                    break
                                except KeyError:
                                    pass

                        if photo is not False:
                            await bot.send_photo(photo=photo, chat_id=user.id, reply_markup=builder.as_markup())
                        # else:
                        #     await bot.send_photo(photo=locale.picture.search_default_photo(), chat_id=user.id,
                        #                          reply_markup=builder.as_markup())
                    except Exception as e:
                        print(f'vk.search error {e}: ', traceback.format_exc())
    else:
        markup = InlineKeyboardBuilder()
        for channel in channels_list_map:
            markup.row(InlineKeyboardButton(text=channel['name'],
                                            url=channel['url'].replace(';', ':')))
        markup.row(InlineKeyboardButton(text='✅ Проверить Подписку', callback_data=Start().pack()))

        await bot.send_animation(chat_id=message.from_user.id,
                                 animation='https://telegra.ph/file/41a69dade6e7321e40971.mp4',
                                 caption=locale.subscheck(),
                                 reply_markup=markup.as_markup())
