import asyncio
import logging
import random
import pickle
import time
import climage
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from vkbottle import API, BaseMiddleware
from vkbottle.user import User, Message
from vkbottle.user import UserLabeler
from vkbottle.exception_factory import VKAPIError

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="bot_log.log",
    filemode="w"
)

with open("login.txt", 'r', encoding="utf-8") as file:
    login = file.read().strip()
with open("password.txt", 'r', encoding="utf-8") as file:
    password = file.read().strip()

# Чтение данных из файлов
def read_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Ошибка чтения файла {filename}: {e}")
        return ""

# Скроллим вниз по чуть-чуть, пока элемент не станет видим
def scroll_until_visible(driver, xpath, timeout=15):
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            element = driver.find_element(By.XPATH, xpath)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            return element  # Успех
        except Exception:
            driver.execute_script("window.scrollBy(0, 300);")  # Прокручиваем вниз
            time.sleep(0.5)
    raise TimeoutError(f"Элемент с xpath {xpath} не найден в течение {timeout} секунд")
    
# Получение токена через Selenium
def get_token():
    global token
    try:
        options = Options()
        # options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        if os.path.exists("vk_cookies_1.pkl"):
            driver.get("https://oauth.vk.com/authorize?client_id=6287487&scope=1073737727&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1")  
            time.sleep(10)
            with open("vk_cookies_1.pkl", "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    cookie.pop('sameSite', None)
                    driver.add_cookie(cookie)
            driver.get("https://oauth.vk.com/authorize?client_id=6287487&scope=1073737727&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1")
            driver.delete_all_cookies()
            time.sleep(5)
            driver.execute_script("window.scrollBy(0, 500);")
            WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Разрешить"]')))
            button = driver.find_element(By.XPATH, '//button[text()="Разрешить"]')
            with open("vk_cookies_2.pkl", "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    cookie.pop('sameSite', None)
                    driver.add_cookie(cookie)
            button.click()
            logging.debug("Get Token: Redirect")
            redirected_url = driver.current_url
            start = redirected_url.split("access_token=")[1]
            token = start.split("&expires_in")[0]
            with open("token.txt", "w", encoding="utf-8") as file:
                file.write(token)
                logging.debug("Get Token: Successfully wrote token to file")
            print(f"\n\n\nТокен: {token}")
            logging.debug("Get Token: Successfully")
            driver.quit()
            return
        driver.get("https://oauth.vk.com/authorize?client_id=6287487&scope=1073737727&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, 'email')))
        login_form = driver.find_element(By.NAME, 'email')
        login_form.send_keys(read_file("login.txt"))
        password_form = driver.find_element(By.NAME, 'pass')
        password_form.send_keys(read_file("password.txt"))
        accept_button = driver.find_element(By.ID, 'install_allow')
        accept_button.click()
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, 'code')))
            phone_code = input("Введите последние 4 цифры номера телефона входящего звонка либо смс: ")
            code_input = driver.find_element(By.NAME, 'code')
            code_input.send_keys(phone_code)
            confirm_button = driver.find_element(By.CLASS_NAME, 'button')
            confirm_button.click()
            logging.debug("Get Token: Phone confirmation submitted")
        except Exception:
            logging.debug("Get Token: No phone confirmation")
            logging.debug("Get Token: Login")
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'oauth_captcha')))
            logging.debug("Get Token: Captcha")

            captcha_image = driver.find_elements(By.CLASS_NAME, 'oauth_captcha')
            for image in captcha_image:
                image_data = image.screenshot_as_png
                with open('captcha.png', 'wb') as file:
                    file.write(image_data)
                print(climage.convert('captcha.png', is_unicode=True, width=150))

            # Ввод текста с капчи
            captcha_text = input("Введите текст с капчи: ")
            captcha_form = driver.find_element(By.NAME, 'captcha_key')
            captcha_form.clear()
            captcha_form.send_keys(captcha_text)

            # Повторно вводим логин и пароль 
            login_form = driver.find_element(By.NAME, 'email')
            login_form.clear()
            login_form.send_keys(read_file("login.txt"))

            password_form = driver.find_element(By.NAME, 'pass')
            password_form.clear()
            password_form.send_keys(read_file("password.txt"))

            # Нажимаем кнопку войти
            login_button = driver.find_element(By.CLASS_NAME, 'flat_button') 
            login_button.click()

            logging.debug("Get Token: Captcha and login form resubmitted")
        except Exception:
            print("Кажется, капчи не было.")
        with open("vk_cookies_1.pkl", "wb") as file:
            pickle.dump(driver.get_cookies(), file)
        xpath = '//*[@id="oauth_wrap_content"]/div[3]/div/div[1]/button[1]'
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, '//*[@id="oauth_wrap_content"]/div[3]/div/div[1]/button[1]')))
        button = driver.find_element(By.XPATH, '//*[@id="oauth_wrap_content"]/div[3]/div/div[1]/button[1]')
        button.click()
        logging.debug("Get Token: Redirect")
        redirected_url = driver.current_url
        start = redirected_url.split("access_token=")[1]
        token = start.split("&expires_in")[0]
        with open("token.txt", "w", encoding="utf-8") as file:
            file.write(token)
            logging.debug("Get Token: Successfully wrote token to file")
        print(f"\n\n\nТокен: {token}")
        logging.debug("Get Token: Successfully")
    except Exception as e:
        logging.debug(f"Get Token: Error: {e}")
        print(e)
    finally:
        driver.quit()
    

# Фоновое обновление токена
async def token_reget_async(first_get=True):
    logging.debug("Token Reget: Started")
    
    def sync_get_token():
        get_token()

    loop = asyncio.get_running_loop()
    
    if first_get:
        await loop.run_in_executor(None, sync_get_token)
        logging.debug("Token Reget: First token received")

    # Фоновая задача обновления токена каждые 12 часов
    async def regetter():
        while True:
            await asyncio.sleep(12 * 3600)
            await loop.run_in_executor(None, sync_get_token)
            logging.debug("Token Reget: Refreshed")

    asyncio.create_task(regetter())

# Глобальные переменные
waiting_for_reply = set()
token = ""
stopped = True
users = []
limit = 24 * 3600  # Пауза после достижения дневного лимита (в секундах)
mlimit = 1  # Лимит сообщений в день
latency = [50, 120]  # Задержка между сообщениями (в секундах)
number = 0  # Счетчик отправленных сообщений


# Чтение и обработка users.txt
def read_users():
    try:
        with open("users.txt", "r", encoding="utf-8") as file:
            logging.debug("Main Cycle: users.txt opened")
            users_list = []
            for line in file:
                line = line.strip()
                if not line:
                    continue
                if "id" in line:
                    user_id = line.split("id")[1]
                else:
                    user_id = line
                try:
                    users_list.append(int(user_id))
                except ValueError:
                    logging.warning(f"Недействительный ID: {user_id}")
            logging.debug("Main Cycle: users.txt read")
            return users_list
    except Exception as e:
        logging.error(f"Ошибка чтения users.txt: {e}")
        return []

# Проверка валидности ID пользователей
async def validate_users(api: API, user_ids):
    valid_ids = []
    for user_id in user_ids:
        try:
            await api.users.get(user_ids=user_id)
            valid_ids.append(user_id)
        except Exception as e:
            logging.warning(f"Недействительный ID {user_id}: {e}")
    return valid_ids

# Основной цикл рассылки
async def main_cycle(api: API):
    global stopped, number, mlimit, users
    logging.debug("Main Cycle: Started")

    message_text = read_file("message.txt")
    messages = [part.strip() for part in message_text.split("#") if part.strip()]
    users = read_users()
    valid_ids = await validate_users(api, users)

    try:
        for user_id in valid_ids:
            if number >= mlimit and mlimit != -1:
                logging.debug(f"Main Cycle: Limit exceeded, number={number}, mlimit={mlimit}, pausing...")
                number = 0
                await asyncio.sleep(limit)
            if stopped:
                logging.debug("Main Cycle: Bot stopped")
                break

            try:
                selected_message = random.choice(messages)

                await api.messages.send(
                    peer_id=user_id,
                    message=selected_message,
                    random_id=random.randint(1, 1000000)
                )
                # Пометить, что ждём ответ
                waiting_for_reply.add(user_id)
                number += 1
                logging.debug(f"Main Cycle: Sent message to {user_id}: {selected_message[:30]}")
                

                await asyncio.sleep(random.randint(latency[0], latency[1]))

            except Exception as e:
                logging.error(f"Main Cycle: Error sending to {user_id}: {e}")
                if "captcha" in str(e).lower():
                    logging.debug("Main Cycle: Captcha needed, waiting 20 sec...")
                    await asyncio.sleep(20)

        print("Все успешно отправлено, выход...")
        logging.debug("Main Cycle: Breaking...")
    except Exception as e:
        logging.error(f"Main Cycle: Error: {e}")
        print(f"Ошибка: {e}")

class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler()
        except VKAPIError as error:
            if error.code == 5:
                print("Ошибка 5: Недействительный токен доступа!")
                # Проверка login и password 
                if not login or not password:
                    print("Файлы password.txt и login.txt пусты, заполните их и перезапустите бота, либо получите вечный токен")
                    return  
                await token_reget_async(first_get=True)
                print("Токен обновлен, продолжаем работу.")
                return
            else:
                print(f"VK API Error {error.code}: {error.message}")
                raise
        except Exception as e:
            print(f"Другая ошибка: {e}")
            raise

# Инициализация бота
async def start_bot():
    global token, stopped, number, mlimit, latency, limit

    token = read_file("token.txt")
    if not token:
        print("Токен отсутствует. Получите токен вручную через OAuth и сохраните в token.txt.")
        print("URL: https://oauth.vk.com/authorize?client_id=6287487&scope=1073737727&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1")
        print("Попытка получить временный токен...")
                
        # Проверка login и password (пример)
        if not login or not password:
            print("Файлы password.txt и login.txt пусты, заполните их и перезапустите бота, либо получите вечный токен")
            return  
        await token_reget_async(first_get=True)
        token = read_file("token.txt")  
    user = User(token=token)
    user.labeler.message_view.register_middleware(ErrorHandlerMiddleware)

    # Обработка всех входящих сообщений
    @user.on.message(blocking=False)
    async def on_user_message(message: Message):
        # if message.peer_id == message.from_id:
        #     # Игнорируем сообщения из Избранного
        #     return
        user_id = message.from_id
        if user_id in waiting_for_reply:
            print(f"Пользователь {user_id} ответил — запускаем отправку второго сообщения")
            asyncio.create_task(send_second_message(user_id))

    async def send_second_message(user_id: int):
        await asyncio.sleep(random.randint(30, 90))  # задержка перед отправкой

        second_message_text = read_file("second_message.txt")
        second_messages = [part.strip() for part in second_message_text.split("#") if part.strip()]

        try:
            await user.api.messages.send(
                peer_id=user_id,
                message=random.choice(second_messages),
                random_id=random.randint(1, 1_000_000)
            )
            print(f"Второе сообщение отправлено пользователю {user_id}")
        except Exception as e:
            print(f"Ошибка при отправке второго сообщения пользователю {user_id}: {e}")
        finally:
            waiting_for_reply.discard(user_id)


    @user.on.message(text="/start")
    async def start_handler(message: Message):
        global stopped
        logging.debug("Longpoll: Got command /start")
        print(f"Получена команда /start от {message.from_id}")
        if stopped == True:
            stopped = False
            user_id = message.from_id

            asyncio.create_task(main_cycle(user.api))
            await message.answer("Запущено.")
        else:
            await message.answer("Уже запущено.")

    @user.on.message(text="/stop")
    async def stop_handler(message: Message):
        global stopped, number
        logging.debug("Longpoll: Got command /stop")
        if stopped == False:
            stopped = True
            number = 0
            await message.answer("Остановлено")
        else:
            await message.answer("Не запущено!")

    @user.on.message(text="/limit <value>")
    async def limit_handler(message: Message, value: int):
        global limit
        logging.debug(f"Longpoll: Got command /limit {value}")
        limit = value * 3600
        await message.answer(f"Бот будет ждать {value} часов после достижения дневного лимита")

    @user.on.message(text="/mlimit <value>")
    async def mlimit_handler(message: Message, value: int):
        global mlimit
        logging.debug(f"Longpoll: Got command /mlimit {value}")
        mlimit = int(value)
        await message.answer(f"Лимит количества сообщений в день теперь равен: {value} сообщений")

    @user.on.message(text="/latency <value> <value2>")
    async def latency_handler(message: Message, value: int, value2: int):
        global latency
        logging.debug(f"Longpoll: Got command /latency {value}")
        latency[0] = value
        latency[1] = value2
        await message.answer(f"Бот будет ждать {value} секунд перед отправкой сообщения")

    @user.on.message(text="/info")
    async def info_handler(message: Message):
        global stopped, number, mlimit, users, waiting_for_reply
        users = read_users()
        await message.answer(f"""Список команд:
/start - Запускает рассылку
/stop - Отстанавливает рассылку
/limit <value> (кол-во часов ожидания сброса дневного лимита)
    Пример: /limit 5
/mlimit <value> (значение кол-ва сообщений в день)
    Пример: /mlimit 100
/latency <value> <value> (значения задержки между сообщениями, рекомендуется оставить как есть
        Пример: /latency 50 90
                Первая цифра - минимальное значение задержки
                Вторая цифра - максимальное значение задержки)
    Пользователей в users.txt: {len(users)}
    Отправленных сообщений: {number} из {mlimit}""")
    
  
    
    logging.debug("Starter: First VK Session started")
    print("BOT STARTED")
    await user.run_polling()

# Основная точка входа
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    loop.run_forever()