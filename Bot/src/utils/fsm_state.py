from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


class AddSponsorFSM(StatesGroup):
    send_name = State()
    send_url = State()
    send_chanel_id = State()


class EditSponsorFSM(StatesGroup):
    edit_name = State()
    edit_url = State()
    edit_chanel_id = State()
