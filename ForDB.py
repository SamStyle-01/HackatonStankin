from telethon import TelegramClient
from datetime import datetime, timedelta, timezone
from yandex_neural_api.client import YandexNeuralAPIClient
import logging
import sqlite3
import vk_api

# Данные учетной записи
api_id = 27543039  # Ваш API ID
api_hash = "a4e35522239110f86c5f89fa63eec1a6"  # Ваш API Hash

source_channel = "@cyberstankin"  # Канал, откуда пересылаем сообщения
destination_chat = "@marmadyk_123"  # Чат или канал, куда пересылаем сообщения

# Создаем Telethon-клиент
client = TelegramClient("session_name3", api_id, api_hash, system_version='4.16.30-vxCUSTOM')

posts = []

# Создаем или подключаемся к базе данных
connection = sqlite3.connect("telegram_posts.db")

# Создаем объект курсора
cursor = connection.cursor()

client2 = YandexNeuralAPIClient(
    iam_token = 't1.9euelZrNz8zLx5rKjI7Gi8eanY2MkO3rnpWalJiKz8eNyc6Qis6Km5PIlInl8_drJHVF-e9ZSgQV_t3z9ytTckX571lKBBX-zef1656VmpWWzcyXls6Oj82WismbjZeS7_zF656VmpWWzcyXls6Oj82WismbjZeS.p-YhEfvok-IGD0QGs5jXux4dAV9V-wWy-AI6hKS5gLLsfAKdKbeOPHWNTdfuuhZo1e2WmvX2DCms0su9jtdOAg',
    folder_id = 'b1gg47f99b5v3nsqckg0',
    model_type = 'pro',
    llm_temperature = 0.6,
    llm_max_tokens = 1000,
    image_mime_type = 'image/png',
    image_width_ratio = 1,
    image_height_ratio  = 1,
    embedding_model  = 'text-search-doc',
    log_level  = logging.INFO
)

ACCESS_TOKEN = 'd3eee9fed3eee9fed3eee9fe27d0ca01e1dd3eed3eee9feb4ac4b63ca68c4e49f1258d0'
USERNAME = 'sno_stankin'  # Краткий адрес группы (username)


def get_filtered_posts(username, days=30):
    vk_session = vk_api.VkApi(token=ACCESS_TOKEN)
    vk = vk_session.get_api()

    # Получить ID группы по username
    group = vk.utils.resolveScreenName(screen_name=username)
    group_id = -group['object_id']  # Отрицательное значение для группы

    # Параметры фильтрации
    now = datetime.now()
    date_threshold = now - timedelta(days=days)
    date_threshold_unix = int(date_threshold.timestamp())

    # Получить последние 100 постов
    posts = vk.wall.get(owner_id=group_id, count=100)['items']

    # Фильтрация по дате
    filtered_posts = [
        post for post in posts if post['date'] >= date_threshold_unix
    ]

    # Вывод отфильтрованных постов
    for post in filtered_posts:
        post_date = datetime.fromtimestamp(post['date']).strftime('%Y-%m-%d %H:%M:%S')

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
            print(prompt)

            cursor.execute(f"""
            INSERT INTO {USERNAME + "_vk"} (id, text, link, date) 
            VALUES (?, ?, ?, ?)
            """, (post['id'], prompt, f'https://vk.com/wall{USERNAME}_{post["id"]}', post_date))


if __name__ == "__main__":
    client.start()  # Авторизация
    with client:
        get_filtered_posts(USERNAME)
    connection.commit()
    connection.close()
    print(posts)