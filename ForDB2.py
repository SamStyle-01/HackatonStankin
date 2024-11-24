import vk_api
from datetime import datetime

# Ваш токен доступа
ACCESS_TOKEN = 'd3eee9fed3eee9fed3eee9fe27d0ca01e1dd3eed3eee9feb4ac4b63ca68c4e49f1258d0'
USERNAME = 'sno_stankin'  # Краткий адрес группы (username)


def get_last_posts(username, count=5):
    # Авторизация через токен
    vk_session = vk_api.VkApi(token=ACCESS_TOKEN)
    vk = vk_session.get_api()

    # Получение ID группы
    group_info = vk.groups.getById(group_id=username)
    group_id = group_info[0]['id']

    # Получение постов
    posts = vk.wall.get(owner_id=-group_id, count=count)

    # Парсинг результата
    for post in posts['items']:
        print(f"ID поста: {post['id']}")
        print(f"Текст: {post['text']}")
        print(datetime.fromtimestamp(post['date']).strftime('%Y-%m-%d %H:%M:%S'))
        print("-" * 20)

# Вызов функции
get_last_posts(USERNAME)
