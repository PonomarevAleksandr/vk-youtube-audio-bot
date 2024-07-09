# Audio-VK-YT-bot
![cover](https://github.com/PonomarevAleksandr/Audio-VK-YT-bot/assets/155808976/4e2f43db-dfe2-44dd-b216-43ad1dca2931)

## Описание
Audio-VK-YT-bot - это телеграм-бот для скачивания музыки с VK и YouTube. Бот использует `vk_api` и `yt-dlp` для извлечения музыкальных треков и предоставляет простой интерфейс для пользователей для скачивания их любимых песен.

## Технологии
- **Python**: Язык программирования, используемый для написания бота.
- **Aiogram**: Асинхронный фреймворк для Telegram Bot API.
- **Redis**: Хранилище данных в памяти, используемое для управления состоянием пользователя.
- **MongoDB**: База данных для хранения информации о пользователях и их запросах.
- **Proxy**: Используется для обхода блокировок и ограничений.
- **yt-dlp**: Инструмент командной строки для скачивания видео.
- **aiohttp**: Асинхронный HTTP клиент/сервер.
- **fluentogram**: Библиотека для удобной работы с локализацией в aiogram.
- **Docker:** Платформа для разработки, доставки и запуска приложений в контейнерах.


## Как это работает
**Видео-инструкция:**
- https://github.com/PonomarevAleksandr/Audio-VK-YT-bot/assets/155808976/ea5b33ac-0d53-4abd-8c17-276782644dd6
- https://github.com/PonomarevAleksandr/Audio-VK-YT-bot/assets/155808976/90f29e68-c5d5-41f4-9f86-fc2dfaebe94c
- https://github.com/PonomarevAleksandr/Audio-VK-YT-bot/assets/155808976/6bad27f3-6ecd-4f19-8953-8a0e1e3268bd

Когда пользователь отправляет боту название трека, имя исполнителя или ссылку на YouTube, процесс работы бота начинается. Вот шаги, которые следует бот:

1. **Получение запроса**: Бот принимает запрос от пользователя и использует Redis для отправки задания воркеру.
2. **Обработка задания**: Воркер, работающий на мультипроцессинге, берёт задание и определяет источник: VK или YouTube.
   - **Для VK**: Используются методы `vk_api` для поиска и скачивания трека.
   - **Для YouTube**: Используется `yt-dlp` для извлечения аудиодорожки из видео.
3. **Кэширование**: Скачанный контент отправляется в один из 10 каналов Telegram, которые служат хранилищем для уже скаченных треков.
4. **Эффективное использование ресурсов**: Если трек уже был скачан ранее, он не скачивается заново. Вместо этого бот извлекает его из кэша, что экономит время и ресурсы.
5. **Доставка**: После обработки запроса бот отправляет пользователю аудио файл трека.

Эта система не только обеспечивает быстрое и эффективное скачивание музыки, но и оптимизирует использование сетевых и вычислительных ресурсов за счёт кэширования популярного контента.


## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/PonomarevAleksandr/Audio-VK-YT-bot.git
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения в файле `.env`:
```
API_TOKEN=ваш_токен_телеграм_бота
REDIS_URL=redis://localhost:6379
MONGO_URI=mongodb://localhost:27017
PROXY_URL=ваш_http_proxy
```

4. Запустите бота:
```bash
python bot.py
```


**Примечание**: Версия кода, доступная в репозитории, не содержит некоторые зависимости и методы, связанные с VK, в целях сохранения конфиденциальности. Пожалуйста, учитывайте это при настройке и использовании бота. Для полной функциональности вам потребуется добавить соответствующие компоненты в соответствии с вашими требованиями.


## Использование

Отправьте боту ссылку на видео в VK или YouTube, и он предоставит вам возможность скачать аудиодорожку.

# Благодарности

Отдельное спасибо [AntiCodingCodingLab](https://t.me/AntiCodingCodingLab) за неоценимую помощь в разработке этого проекта и содействие в решении технических проблем.


