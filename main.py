import os
from dotenv import load_dotenv
import telebot
import requests
import jsons
from Class_ModelResponse import ModelResponse

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

bot = telebot.TeleBot(API_TOKEN)

user_contexts = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я ваш Telegram бот с поддержкой контекста.\n"
        "Доступные команды:\n"
        "/start - вывод всех доступных команд\n"
        "/model - выводит название используемой языковой модели\n"
        "/clear - очищает историю диалога\n"
        "Отправьте любое сообщение, и я отвечу с помощью LLM модели, помня предыдущие сообщения."
    )
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=['model'])
def send_model_name(message):
    try:
        response = requests.get('http://localhost:1234/v1/models')
        response.raise_for_status()

        model_info = response.json()
        model_name = model_info['data'][0]['id']
        bot.reply_to(message, f"Используемая модель: {model_name}")
    except requests.exceptions.RequestException as e:
        bot.reply_to(message,
                     f'Не удалось получить информацию о модели. Убедитесь, что LM Studio запущен и модель загружена. Ошибка: {e}')
    except IndexError:
        bot.reply_to(message, 'LM Studio запущен, но не найдено загруженных моделей.')


@bot.message_handler(commands=['clear'])
def handle_clear(message):
    user_id = message.chat.id
    if user_id in user_contexts:
        del user_contexts[user_id]
        bot.reply_to(message, "История диалога очищена. Можете начать новый разговор.")
    else:
        bot.reply_to(message, "История диалога уже пуста.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_query = message.text

    if user_id not in user_contexts:
        user_contexts[user_id] = []

    user_contexts[user_id].append({"role": "user", "content": user_query})

    request = {
        "messages": user_contexts[user_id],
        # "temperature": 0.7
    }

    try:
        response = requests.post(
            'http://localhost:1234/v1/chat/completions',
            json=request
        )
        response.raise_for_status()

        model_response: ModelResponse = jsons.loads(response.text, ModelResponse)
        assistant_response = model_response.choices[0].message.content

        user_contexts[user_id].append({"role": "assistant", "content": assistant_response})

        bot.reply_to(message, assistant_response)

    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f'Произошла ошибка при обращении к модели. Убедитесь, что LM Studio запущен. Ошибка: {e}')
        user_contexts[user_id].pop()
    except Exception as e:
        bot.reply_to(message, f'Произошла непредвиденная ошибка: {e}')
        user_contexts[user_id].pop()


if __name__ == '__main__':
    print("Бот запущен. Ожидание сообщений...")
    bot.polling(none_stop=True)
