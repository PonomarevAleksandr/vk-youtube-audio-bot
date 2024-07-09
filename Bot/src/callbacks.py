from typing import Optional

from aiogram.filters.callback_data import CallbackData


class LanguageSwitcher(CallbackData, prefix='language'):
    lang_select: str


class PlaylistNavigate(CallbackData, prefix='playlistNav'):
    cache_id: str
    offset: int
    index: Optional[int] = None


class Plug(CallbackData, prefix='Plug'):
    ...


class VkDownloadAudio(CallbackData, prefix='VK_download_audio'):
    cache_id: str
    index: int


class VkDownloadAudioPage(CallbackData, prefix='VK_download_audio_page'):
    cache_id: str
    index: int


class NewSongs(CallbackData, prefix='new_songs'):
    chart_type: str


class Start(CallbackData, prefix='start'):
    ...


class Help(CallbackData, prefix='help'):
    ...


class ChannelsAdmin(CallbackData, prefix='channels'):
    channel_id: int



class AddSponsor(CallbackData, prefix='sponsor'):
    edit: str
    channel_id: Optional[int] = None


class RemoveSponsor(CallbackData, prefix='remove_sponsor'):
    channel_id: int



class SponsorList(CallbackData, prefix='list_sponsor'):
    ...
