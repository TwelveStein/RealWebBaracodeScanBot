import telebot
from pyzbar.pyzbar import decode
from PIL import Image
from io import BytesIO
import requests

#Открываем файл token.txt для чтения токена
with open('token.txt', 'r') as file:
    TOKEN = file.read().strip()

bot = telebot.TeleBot(TOKEN)

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


@bot.message_handler(content_types=['photo'])
def handle_docs_photo(message):
    try:
        process_image(message)
    except Exception as e:
        bot.reply_to(message, "Произошла системная ошибка, попробуйте снова")

def process_image(message):
    file_info = bot.get_file(message.photo[-1].file_id)
    url='https://api.telegram.org/file/bot{0}/{1}'
    file = requests.get(url.format(TOKEN, file_info.file_path), timeout=120)

    def process_zte(data):
        return data.replace("ztxg", "5a545847")

    def process_huawei(data):
        return data

    def process_cdata(data):
        mac_address = None
        p_sn = None
        if "70a5" in data:  # Предполагаем, что "70a5" присутствует в MAC
            mac_address = data
        if "hwtc" in data:  # Предполагаем, что "hwtc" присутствует в P-SN
            p_sn = data.replace("hwtc", "48575443")
        return mac_address, p_sn



    def process_stels(data):
        return data

    vendor_codes = {
        "ztxg": ("ZTE", process_zte),
        "hwtc": ("CData", process_cdata),
        "e067": ("STELS", process_stels),
        "48575443": ("Huawei", process_huawei)
    }

    img = Image.open(BytesIO(file.content))
    barcodes = decode(img)

    mac_address = None
    p_sn = None
    vendor = None
    for barcode in sorted(barcodes, key=lambda b: "70a5" in b.data.decode('utf-8').lower(), reverse=True):
        decoded_data = barcode.data.decode('utf-8').lower()
        for code, (v, processor) in vendor_codes.items():
            if code in decoded_data:
                edited_data = processor(decoded_data)
                if v == "CData":
                    mac, psn = edited_data
                    if mac is not None:
                        mac_address = mac
                    if psn is not None:
                        p_sn = psn
                    vendor = v
                else:
                    vendor = v
                    login = edited_data

    if vendor == "CData":
        bot.reply_to(message, f"Вендор: <b>{vendor}</b>\n\nMAC адресс: <code>{mac_address}</code>\nP-SN: <code>{p_sn}</code>\nПароль: <code>IPoE-Opt82</code>", parse_mode='HTML')
    elif vendor is not None:
        bot.reply_to(message, f"Вендор: <b>{vendor}</b>\n\nЛогин: <code>{login}</code>\nПароль: <code>IPoE-Opt82</code>", parse_mode='HTML')
    else:
        data = "\n".join([f"Найден штрих-код <code>{barcode.data.decode('utf-8').lower()}</code>" for barcode in barcodes])
        bot.reply_to(message, f"Неизвестное ONU устройство\n\n{data}\n\nПароль: <code>IPoE-Opt82</code>", parse_mode='HTML')


bot.polling(none_stop=True, interval=5)
