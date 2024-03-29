import telebot
from pyzbar.pyzbar import decode
from PIL import Image
from io import BytesIO
import requests

#Открываем файл token.txt для чтения токена
with open('token.txt', 'r') as file:
    TOKEN = file.read().strip()

bot = telebot.TeleBot(TOKEN)
@bot.message_handler(content_types=['photo'])
def handle_docs_photo(message):
    success = False  # Инициализируем флаг успеха
    try:
        success = process_image(message)  # Если функция вернула True, значит, операция была успешной
    except Exception as e:
        bot.reply_to(message, "Произошла системная ошибка, попробуйте снова")  # Если что-то пошло не так, отправляем сообщение об ошибке
    finally:
        if not success:  # Если операция не была успешной, отправляем сообщение о неудачной расшифровке
            #bot.reply_to(message, "Не удалось обработать изображение!")
            bot.reply_to(message, "Ошибка: не могу прочесть штрих код(\n\nПопробуйте выделить скриншотом область штрих-кода на фотографии и повторить попытку")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
    Привет! Я бот, который может помочь вам расшифровать штрих-коды ONU устройств. Вот как вы можете меня использовать:
    
    1. Отправьте мне фотографию с штрих-кодом, используя обычное сообщение или пересланное сообщение из другого чата.
    2. Я попытаюсь расшифровать штрих-код и отправлю вам информацию о нем.
    3. Если у вас возникнут проблемы или вопросы, вы можете использовать команду /help для получения дополнительной информации.
    
    Надеюсь, я смогу вам помочь!
    """
    bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
    Привет! Вот как вы можете использовать этого бота:
    
    1. Отправьте фотографию ONU устройства, где видно штрих-код, и я попытаюсь его расшифровать.
    2. Если я смогу расшифровать штрих-код, я отправлю вам логин и пароль для добавления ONU в UTM.
    3. Если я не смогу расшифровать штрих-код, я сообщу вам об этом.
    4. Причины, по которым я не смогу расшифровать штрих-код ты можешь узнать тут: /barcode.
    5. Я могу обрабатывать сразу несколько фото, а данные буду высылать по порядку, отвечая на каждое отдельное фото.
    6. Информацию о вендорах, с которыми я умею работать можно узнать тут: /vendors
    7. По другим вопросам или если вы нашли баг обращайтесь к моему создателю: @Twelve_Stein


    Версия бота: 1.0 
    Последнее обновление: 28.03.2024
    """
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['vendors'])
def send_vendors_info(message):
    vendors_info_text = """
    Вот список вендоров, штрих-коды которых я могу расшифровать:
    
    1. <b>ZTE</b>: Штрих-коды этих устройств обычно содержат "ztxg".
    2. <b>Huawei</b>: Штрих-коды этих устройств обычно содержат "48575443".
    3. <b>CData</b>: Штрих-коды этих устройств обычно содержат "hwtc".
    4. <b>STELS</b>: Штрих-коды этих устройств обычно содержат "e067".
    
    Если штрих-код, который вы отправили, не соответствует ни одному из этих вендоров, я сообщу вам об этом.
    """
    bot.send_message(message.chat.id, vendors_info_text, parse_mode='HTML')



@bot.message_handler(commands=['barcode'])
def send_barcode_info(message):
    barcode_info_text = """
    Чтобы я мог расшифровать штрих-код, вам нужно отправить мне фотографию с ним. Вот несколько советов:
    
    1. Убедитесь, что штрих-код четко виден на фотографии. Избегайте мыльных, маленьких или размытых изображений.
    2. Попробуйте избегать бликов и теней на штрих-коде.
    3. Штрих-код должен быть расположен прямо перед камерой, а не под углом.
    4. Если штрих-код поврежден или частично скрыт, я могу не суметь его расшифровать.
    5. Если вы считаете, что с фотографией всё нормально, но я не могу её обработать, то просто выделите облась со штрих-кодами на фото, и отправьте мне ещё раз уже скриншот.
    
    После того, как вы отправите фотографию, я попытаюсь расшифровать штрих-код и отправлю вам информацию о нем.
    """
    bot.send_message(message.chat.id, barcode_info_text)


def process_image(message):
    file_info = bot.get_file(message.photo[-1].file_id)  # Получаем информацию о файле
    file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(TOKEN, file_info.file_path))  # Скачиваем файл

    img = Image.open(BytesIO(file.content))  # Открываем изображение
    barcodes = decode(img)  # Распознаем штрих-коды
    vendorONU = "Неизвестное ONU устройство"
    for barcode in barcodes:
        decoded_data = barcode.data.decode('utf-8').lower()
        if "ztxg" in decoded_data:
            vendorONU = "ZTE"
        elif "hwtc" in decoded_data:
            vendorONU = "CData"
        elif "e067" in decoded_data:
            vendorONU = "STELS"
        elif "48575443" in decoded_data:
            vendorONU = "Huawei"
        if vendorONU == "Неизвестное ONU устройство":
            #bot.reply_to(message, "ERR: не могу прочесть штрих код(\n\nПопробуйте выделить скриншотом область штрих-кода на фотографии и повторить попытку")
            data = "\n".join([f"Найден штрих-код <code>{barcode.data.decode('utf-8').lower()}</code>" for barcode in barcodes])
            # Отправляем информацию о всех штрих-кодах пользователю в одном сообщении
            bot.reply_to(message, f"{vendorONU}\n\n{data}\n\nПароль: <code>IPoE-Opt82</code>", parse_mode='HTML')
            return True  # Возвращаем True, так как операция была успешной
        elif "70a5" not in decoded_data or "ztxg" in decoded_data or "hwtc" in decoded_data or "48575443" in decoded_data:
            # Заменяем определенные словосочетания вендора и отправляем только отредактированную строку
            edited_data = decoded_data.replace("hwtc", "48575443").replace("ztxg", "5a545847")
            bot.reply_to(message, f"Вендор: <b>{vendorONU}</b>\n\nЛогин: <code>{edited_data}</code>\nПароль: <code>IPoE-Opt82</code>", parse_mode='HTML')
            return True  # Возвращаем True, так как операция была успешной
        elif "70a5" in decoded_data:
            bot.reply_to(message, f"Вендор: <b>ZTE</b>\n\n</b>\n\nЛогин(MAC): <code>{decoded_data}</code>\nПароль: <code>IPoE-Opt82</code>", parse_mode='HTML')
            return True  # Возвращаем True, так как операция была успешной
        elif "e067" in decoded_data:
            bot.reply_to(message, f"Вендор: <b>STELS</b>\n\n</b>\n\nЛогин(MAC): <code>{decoded_data}</code>\nПароль: <code>IPoE-Opt82</code>", parse_mode='HTML')
            return True  # Возвращаем True, так как операция была успешной
        else:
            data = "\n".join([f"Найден штрих-код <code>{barcode.data.decode('utf-8').lower()}</code>" for barcode in barcodes])
            # Отправляем информацию о всех штрих-кодах пользователю в одном сообщении
            bot.reply_to(message, f"{data}\n\nПароль: <code>IPoE-Opt82</code>", parse_mode='HTML')
            return True  # Возвращаем True, так как операция была успешной

bot.polling()
