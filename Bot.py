import asyncio
import logging
import sys
import speech_recognition as sr
from io import BytesIO
from pydub import AudioSegment

import requests

from aiogram import Bot, Dispatcher, types, F, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup

from telethon import TelegramClient
from datetime import datetime, timedelta, timezone
from yandex_neural_api.client import YandexNeuralAPIClient
import sqlite3
import json
import vk_api

# Данные учетной записи
api_id = 27543039  # Ваш API ID
api_hash = "a4e35522239110f86c5f89fa63eec1a6"  # Ваш API Hash

vk_service = "d3eee9fed3eee9fed3eee9fe27d0ca01e1dd3eed3eee9feb4ac4b63ca68c4e49f1258d0"

# Создаем Telethon-клиент
client = TelegramClient("session_name3", api_id, api_hash, system_version='4.16.30-vxCUSTOM')

# Создаем или подключаемся к базе данных
connection = sqlite3.connect("posts.db")

# Создаем объект курсора
cursor = connection.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
# Извлекаем результат
tables = cursor.fetchall()
tables = [table[0] for table in tables]

change_period = False
users = dict()
client2 = YandexNeuralAPIClient(
    iam_token='t1.9euelZrNz8zLx5rKjI7Gi8eanY2MkO3rnpWalJiKz8eNyc6Qis6Km5PIlInl8_drJHVF-e9ZSgQV_t3z9ytTckX571lKBBX-zef1656VmpWWzcyXls6Oj82WismbjZeS7_zF656VmpWWzcyXls6Oj82WismbjZeS.p-YhEfvok-IGD0QGs5jXux4dAV9V-wWy-AI6hKS5gLLsfAKdKbeOPHWNTdfuuhZo1e2WmvX2DCms0su9jtdOAg',
    folder_id='b1gg47f99b5v3nsqckg0',
    model_type='pro',
    llm_temperature=0.6,
    llm_max_tokens=1000,
    image_mime_type='image/png',
    image_width_ratio=1,
    image_height_ratio =1,
    embedding_model='text-search-doc',
    log_level=logging.INFO
)

TOKEN = '8105348683:AAHt1_Yn-NY9aw28RiChMCI4hZ9Mm16q6Fw'
dp = Dispatcher()

# Авторизация через токен
vk_session = vk_api.VkApi(token=vk_service)
vk = vk_session.get_api()


# Функция для сохранения словаря
def save_users_to_file():
    with open("users.json", "w", encoding="utf-8") as file:
        json.dump(users, file, ensure_ascii=False, indent=4)


# Функция для загрузки словаря
def load_users_from_file():
    global users
    try:
        with open("users.json", "r", encoding="utf-8") as file:
            users = json.load(file)
    except FileNotFoundError:
        users = {}


load_users_from_file()


async def update_db():
    while True:
        for table in tables:
            # Выполнение запроса для получения наибольшего числа
            cursor.execute(f"SELECT MAX(id) FROM {table};")
            result = cursor.fetchone()
            # Вывод результата
            result = result[0]
            if not table.endswith('_vk'):
                async for message in client.iter_messages("@" + table, limit=50):
                    if message.id != result:
                        if message.text != "":
                            prompt = client2.generate_text(
                                "Сделай выжимку текста на 7 слов. Без излишней формальности и вводных слов, "
                                "только ключевые события и даты. Текст должен быть "
                                "сфокусирован на описании мероприятия или события, "
                                "а не на истории. Избегай субъективных оценок вроде \"круто\" или \"классно\". "
                                "Только суть: \"" + message.text + "\""
                            )

                            message_link = f"https://t.me/{table}/{message.id}"
                            cursor.execute(f"""
                            INSERT INTO {table} (id, text, link, date) 
                            VALUES (?, ?, ?, ?)
                            """, (message.id, prompt, message_link, message.date))
                    else:
                        break
            else:
                # Получить ID группы по username
                group_name = table.split("_vk")[0]
                group = vk.utils.resolveScreenName(screen_name=group_name)
                group_id = -group['object_id']  # Отрицательное значение для группы

                # Получить последние 100 постов
                posts = vk.wall.get(owner_id=group_id, count=100)['items']

                # Вывод отфильтрованных постов
                for post in posts:
                    post_date = datetime.fromtimestamp(post['date']).strftime('%Y-%m-%d %H:%M:%S')
                    if post["id"] != result:
                        if post["text"] != "":
                            prompt = client2.generate_text(
                                "Сделай выжимку текста на 7 слов. Без излишней формальности и вводных слов, "
                                "только ключевые события и даты. Текст должен быть "
                                "сфокусирован на описании мероприятия или события, "
                                "а не на истории. Избегай субъективных оценок вроде \"круто\" или \"классно\". "
                                "Только суть: \"" + post["text"] + "\""
                            )

                            prompt = prompt.replace("\n\n\n", "\n")
                            prompt = prompt.replace("\n\n", "\n")

                            cursor.execute(f"""
                                INSERT INTO {table} (id, text, link, date) 
                                VALUES (?, ?, ?, ?)
                                """, (post['id'], prompt,
                                f'https://vk.com/wall{group_name}_{post["id"]}', post_date))
                    else:
                        break
        connection.commit()
        await asyncio.sleep(300)  # Каждые 5 минут


def get_day_word(days: int) -> str:
    """
    Возвращает корректную форму слова "день" для заданного числа.

    :param days: Число дней
    :return: Строка с правильным склонением слова "день"
    """
    if 11 <= days % 100 <= 19:  # Исключение для чисел 11-19
        return "дней"
    elif days % 10 == 1:        # Числа, оканчивающиеся на 1 (кроме 11)
        return "день"
    elif 2 <= days % 10 <= 4:   # Числа, оканчивающиеся на 2, 3, 4 (кроме 12-14)
        return "дня"
    else:                       # Все остальные случаи
        return "дней"


def recognize_speech_from_audio(audio_bytes, audio_format="ogg"):
    audio = AudioSegment.from_file(BytesIO(audio_bytes), format=audio_format)

    wav_io = BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.seek(0)

    recognizer = sr.Recognizer()
    text = ""
    with sr.AudioFile(wav_io) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language="ru-RU")
        except sr.UnknownValueError:
            text = "Не удалось распознать голос."
        except sr.RequestError:
            text = "Ошибка сервиса распознавания речи."
    return text


# Устанавливаем список команд
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="add_channel", description="Добавить доступный канал"),
        BotCommand(command="remove_channel", description="Отключить канал"),
        BotCommand(command="time_period", description="Изменить период времени"),
    ]
    await bot.set_my_commands(commands)


async def find_entity(group):
    entity = ""
    if not group.endswith('_vk'):
        entity = await client.get_entity("@" + group)
        entity = entity.title
    else:
        # Параметры запроса
        url = "https://api.vk.com/method/groups.getById"
        params = {
            "group_id": f"{group.replace('_vk', '')}",  # Короткое имя или ID группы
            "fields": "name",
            "access_token": f"{vk_service}",
            "v": "5.131"
        }

        response = requests.get(url, params=params)
        data = response.json()
        if "response" in data:
            entity = data["response"][0]["name"]
    return entity


@dp.message(CommandStart())
async def command_start_handler(message: Message):
    if str(message.from_user.id) not in users.keys():
        users[str(message.from_user.id)] = {'groups': list(range(len(tables))), 'duration': 3}
        save_users_to_file()
    await message.answer(
        f"Привет, {message.from_user.full_name}! Я - Вестник Станкина. Ищу для тебя интересные штуки.\n"
        f"Что тебя интересует?")


@dp.message(Command("add_channel"))
async def command_add_channel_handler(message: Message):
    if str(message.from_user.id) not in users.keys():
        users[str(message.from_user.id)] = {'groups': list(range(len(tables))), 'duration': 3}
        save_users_to_file()

    # Создаём массив кнопок для добавления
    buttons = []
    for el in range(len(tables)):
        if el not in users[str(message.from_user.id)]['groups']:
            entity = await find_entity(tables[el])
            buttons.append([InlineKeyboardButton(text=entity, callback_data=f"add_{el}")])

    if buttons:
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("Выбери подходящие группы.", reply_markup=keyboard)
    else:
        await message.answer("Все группы уже добавлены.")


@dp.message(Command("remove_channel"))
async def command_remove_channel_handler(message: Message):
    if str(message.from_user.id) not in users.keys():
        users[str(message.from_user.id)] = {'groups': list(range(len(tables))), 'duration': 3}
        save_users_to_file()

    # Создаём массив кнопок для удаления
    buttons = []
    for el in users[str(message.from_user.id)]['groups']:
        entity = await find_entity(tables[el])
        buttons.append([InlineKeyboardButton(text=entity, callback_data=f"remove_{el}")])

    if buttons:
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("Выбери группы, которые хочешь отключить.", reply_markup=keyboard)
    else:
        await message.answer("Все группы уже удалены.")


@dp.callback_query(F.data.startswith("add_"))
async def process_add_button(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    group_index = int(callback_query.data.split("_")[1])

    # Добавляем группу
    if group_index not in users[str(user_id)]['groups']:
        users[str(user_id)]['groups'].append(group_index)
        save_users_to_file()

    await callback_query.answer("Группа добавлена!")
    await callback_query.message.delete()


@dp.callback_query(F.data.startswith("remove_"))
async def process_remove_button(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    group_index = int(callback_query.data.split("_")[1])

    # Удаляем группу
    if group_index in users[str(user_id)]['groups']:
        users[str(user_id)]['groups'].remove(group_index)
        save_users_to_file()

    await callback_query.answer("Группа удалена!")
    await callback_query.message.delete()


@dp.message(Command("time_period"))
async def command_change_time_period_handler(message: Message):
    if str(message.from_user.id) not in users.keys():
        users[str(message.from_user.id)] = {'groups': list(range(len(tables))), 'duration': 3}
        save_users_to_file()
    global change_period
    change_period = True
    await message.answer(f"Сколько дней взять в следующей подборке новостей для тебя? До 14 дней, предупреждаю. "
                         f"Побереги мои нервы.")


@dp.message(F.voice)
async def handle_voice(message: Message, bot: Bot):
    voice = await bot.download(message.voice.file_id)
    audio_bytes = voice.read()
    recognized_text = recognize_speech_from_audio(audio_bytes)
    await message.reply(recognized_text)
    global change_period
    if str(message.from_user.id) not in users.keys():
        users[str(message.from_user.id)] = {'groups': list(range(len(tables))), 'duration': 3}
        save_users_to_file()
    if change_period:
        try:
            num = int(recognized_text)
            if num > 14:
                await message.answer(
                    "Не, дружище, так не пойдёт. Приходи в следующий раз.")
            elif num <= 0:
                await message.answer(
                    "В будущее смотреть я так и не научился. Не выдумывай всякую ерунду.")
            else:
                users[str(message.from_user.id)]['duration'] = num
                await message.answer(f"Будет сделано, босс.")
        except Exception as e:
            await message.answer(f"Ошибка. Тебе надо выбрать число, а не эту "
                                 f"белиберду. Попробуй ещё раз вызвать команду.")
        change_period = False
    else:
        try:
            if len(users[str(message.from_user.id)]['groups']) != 0:
                for num in users[str(message.from_user.id)]['groups']:
                    group = tables[num]
                    # Получаем текущую дату и время (UTC)
                    time_start = datetime.now(timezone.utc) - timedelta(days=users[str(message.from_user.id)]['duration'])
                    time_start_str = time_start.isoformat()  # Формат ISO 8601: YYYY-MM-DDTHH:MM:SS+00:00

                    # Выполняем параметризованный запрос
                    query = f"SELECT id, text, link FROM {group} WHERE date > ? ORDER BY id DESC;"
                    cursor.execute(query, (time_start_str,))
                    events = cursor.fetchall()

                    events_filter = "".join(f"id: {event[0]}.\npost: {event[1]}" for event in events)
                    prompt = client2.generate_text(
                        "Проанализируй запрос пользователя и на основе этого подбери посты, которые могут ему подойти. "
                        "Предоставь список id постов, которые наиболее соответствуют запросу. Используй ключевые слова, "
                        "совпадение по смыслу. Запрос пользователя: " + recognized_text + ". Сборник постов: " + events_filter
                        + ". В ответном сообщение только перечисли id через запятую. Никаких комментариев. "
                          "Это сломает программу."
                          "Если в запросе полная бессмыслица, то верни в ответном сообщении слово "
                          "None."
                    )[:-1].split(", ")

                    events_ids = []
                    try:
                        events_ids = [int(id_event) for id_event in prompt]
                    except Exception as e:
                        events_ids = []

                    events = list(filter(lambda item: item[0] in events_ids, events))

                    # Проверяем, есть ли данные
                    if not events:
                        entity = await find_entity(group)

                        await message.answer(f"Канал {entity}:\nЗаписей за последние "
                                             f"{users[str(message.from_user.id)]['duration']} "
                                             f"{get_day_word(users[str(message.from_user.id)]['duration'])} не найдено.")
                    else:
                        entity = await find_entity(group)
                        events_text = f"Канал {entity}:\n\n"
                        after_texts = [event[1].replace('\n\n', '\n') for event in events]
                        len_message = 0
                        for idx, event in enumerate(events, start=1):
                            var_str = f"{idx}: {after_texts[idx - 1]}\nСсылка: {event[2]}\n\n\n"
                            len_message += len(var_str)
                            if len_message >= 4000:
                                len_message = len(var_str)
                                await message.answer(events_text)
                                events_text = ""
                            events_text += var_str
                        await message.answer(events_text)
            else:
                await message.answer("Ты решил подшутить надо мной? Ты же не выбрал ни один канал.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка базы данных: {e}")
            await message.answer("Нам кранты! База данных сбоит!")
        except Exception as e:
            logging.error(f"Неизвестная ошибка: {e}")
            await message.answer("Мы не поняли друг друга. Попробуй ещё раз объяснить, что ты хочешь.")


@dp.message(F.text)
async def text_handler(message: Message) -> None:
    global change_period
    if str(message.from_user.id) not in users.keys():
        users[str(message.from_user.id)] = {'groups': list(range(len(tables))), 'duration': 3}
        save_users_to_file()
    if change_period:
        try:
            num = int(message.text)
            if num > 14:
                await message.answer(
                    "Не, дружище, так не пойдёт. Приходи в следующий раз.")
            elif num <= 0:
                await message.answer(
                    "В будущее смотреть я так и не научился. Не выдумывай всякую ерунду.")
            else:
                users[str(message.from_user.id)]['duration'] = num
                await message.answer(f"Будет сделано, босс.")
        except Exception as e:
            await message.answer(f"Ошибка. Тебе надо выбрать число, а не эту "
                                 f"белиберду. Попробуй ещё раз вызвать команду.")
        change_period = False
    else:
        try:
            if len(users[str(message.from_user.id)]['groups']) != 0:
                for num in users[str(message.from_user.id)]['groups']:
                    group = tables[num]
                    # Получаем текущую дату и время (UTC)
                    time_start = datetime.now(timezone.utc) - timedelta(days=users[str(message.from_user.id)]['duration'])
                    time_start_str = time_start.isoformat()  # Формат ISO 8601: YYYY-MM-DDTHH:MM:SS+00:00

                    # Выполняем параметризованный запрос
                    query = f"SELECT id, text, link FROM {group} WHERE date > ? ORDER BY id DESC;"
                    cursor.execute(query, (time_start_str,))
                    events = cursor.fetchall()

                    events_filter = "".join(f"id: {event[0]}.\npost: {event[1]}" for event in events)
                    prompt = client2.generate_text(
                        "Проанализируй запрос пользователя и на основе этого подбери посты, которые могут ему подойти. "
                        "Предоставь список id постов, которые наиболее соответствуют запросу. Используй ключевые слова, "
                        "совпадение по смыслу. Запрос пользователя: " + message.text + ". Сборник постов: " + events_filter
                        + ". В ответном сообщение только перечисли id через запятую. Никаких комментариев. "
                        "Это сломает программу."
                        "Если в запросе полная бессмыслица, то верни в ответном сообщении слово "
                        "None."
                    )[:-1].split(", ")

                    events_ids = []
                    try:
                        events_ids = [int(id_event) for id_event in prompt]
                    except Exception as e:
                        events_ids = []

                    events = list(filter(lambda item: item[0] in events_ids, events))

                    # Проверяем, есть ли данные
                    if not events:
                        entity = await find_entity(group)
                        await message.answer(f"Канал {entity}:\nЗаписей за последние "
                                             f"{users[str(message.from_user.id)]['duration']} "
                                             f"{get_day_word(users[str(message.from_user.id)]['duration'])} не найдено.")
                    else:
                        entity = await find_entity(group)
                        events_text = f"Канал {entity}:\n\n"
                        after_texts = [event[1].replace('\n\n', '\n') for event in events]
                        len_message = 0
                        for idx, event in enumerate(events, start=1):
                            var_str = f"{idx}: {after_texts[idx-1]}\nСсылка: {event[2]}\n\n\n"
                            len_message += len(var_str)
                            if len_message >= 4000:
                                len_message = len(var_str)
                                await message.answer(events_text)
                                events_text = ""
                            events_text += var_str
                        await message.answer(events_text)
            else:
                await message.answer("Ты решил подшутить надо мной? Ты же не выбрал ни один канал.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка базы данных: {e}")
            await message.answer("Нам кранты! База данных сбоит!")
        except Exception as e:
            logging.error(f"Неизвестная ошибка: {e}")
            await message.answer("Мы не поняли друг друга. Попробуй ещё раз объяснить, что ты хочешь.")


async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await client.start()
    await set_commands(bot)
    # Start the bot polling
    asyncio.create_task(dp.start_polling(bot))
    # Run the update_db task
    await asyncio.gather(
        update_db()  # Only the periodic task needs to be awaited here
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())