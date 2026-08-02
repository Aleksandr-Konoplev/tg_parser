from aiogram.fsm.state import State, StatesGroup


# FSM-состояния добавления аккаунта (пошаговый ввод через бота)
class AddAccountStates(StatesGroup):
    phone = State()     # ждём номер телефона
    api_id = State()    # ждём api_id
    api_hash = State()  # ждём api_hash


# FSM-состояния добавления канала
class AddChannelStates(StatesGroup):
    username = State()


class AddTaskStates(StatesGroup):
    name = State()          # название
    account = State()       # выбор аккаунта
    channels = State()      # выбор каналов
    keywords = State()      # ключевые слова (можно пропустить)
    interval = State()      # интервал в секундах
