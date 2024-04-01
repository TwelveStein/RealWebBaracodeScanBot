import telebot
from pyzbar.pyzbar import decode
from PIL import Image
from io import BytesIO
import requests
import eventlet

eventlet.monkey_patch()

#Открываем файл token.txt для чтения токена
with open('token.txt', 'r') as file:
    TOKEN = file.read().strip()

bot = telebot.TeleBot(TOKEN)
@bot.message_handler(content_types=['photo'])
def handle_docs_photo(message):
    try:
        success = process_image(message)  # Если функция вернула True, значит, операция была успешной
    except Exception as e:
        bot.reply_to(message, "Произошла системная ошибка, попробуйте снова")  # Если что-то пошло не так, отправляем сообщение об ошибке

@bot.message_handler(commands=['start'])
def send_welcome(message):
    with open('TextMessages/start.txt', 'r', encoding='utf-8') as file:
        welcome_text = file.read().strip()
    bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(commands=['help'])
def send_help(message):
    with open('TextMessages/help.txt', 'r', encoding='utf-8') as file:
        help_text = file.read().strip()
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['vendors'])
def send_vendors_info(message):
    with open('TextMessages/vendors.txt', 'r', encoding='utf-8') as file:
       vendors_info_text = file.read().strip()
    bot.send_message(message.chat.id, vendors_info_text, parse_mode='HTML')



@bot.message_handler(commands=['barcode'])
def send_barcode_info(message):
    with open('TextMessages/barcode.txt', 'r', encoding='utf-8') as file:
        barcode_info_text = file.read().strip()
    bot.send_message(message.chat.id, barcode_info_text)


def process_image(message):
    try:
        with eventlet.Timeout(10):
            file_info = bot.get_file(message.photo[-1].file_id)
            url='https://api.telegram.org/file/bot{0}/{1}'
            file = requests.get(url.format(TOKEN, file_info.file_path), verify=False)

        if file.status_code == 200:
            def process_zte(data):
                return data.replace("ztxg", "5a545847")

            def process_huawei(data):
                return data

            def process_cdata(data):
                mac_address = None
                p_sn = None
                if "hwtc" in data:  # Предполагаем, что "hwtc" присутствует в MAC и P-SN
                    mac_address = data.replace("hwtc", "70a5")
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

            if not barcodes:
                bot.reply_to(message, "На изображении не обнаружено штрих-кодов. Пожалуйста, попробуйте снова или выделите область со штрих-кодами на фото")
                return False
            

            results = []
            for barcode in barcodes:
                decoded_data = barcode.data.decode('utf-8').lower()
                for code, (v, processor) in vendor_codes.items():
                    if code in decoded_data:
                        edited_data = processor(decoded_data)
                        results.append((v, edited_data))

            barcode_success = False
            for v, data in results:
                if v == "CData":
                    mac, psn = data
                    if mac is not None or psn is not None:  # Успех, если найден хотя бы один параметр
                        bot.reply_to(message, f"Вендор: <b>{v}</b>\n\nEPON: <code>{mac}</code>\nGPON: <code>{psn}</code>\nПароль: <code>IPoE-Opt82</code> \n\n<b>Обратите внимание!</b>\nКопируйте логин, в зависимости от типа ONU, он обычно указан на фотографии.\nПодробнее в /vendors", parse_mode='HTML')
                        barcode_success = True
                        break
                else:
                    vendor = v
                    login = data
                    bot.reply_to(message, f"Вендор: <b>{vendor}</b>\n\nЛогин: <code>{login}</code>\nПароль: <code>IPoE-Opt82</code>", parse_mode='HTML')
                    barcode_success = True
                    break

            if not barcode_success:
                data = "\n".join([f"Найден штрих-код <code>{barcode.data.decode('utf-8').lower()}</code>" for barcode in barcodes])
                bot.reply_to(message, f"Неизвестное ONU устройство\n\n{data}\n\nПароль: <code>IPoE-Opt82</code>", parse_mode='HTML')
                barcode_success = True
                
            return barcode_success
        else:
            print("Не удалось получить изображение.")
    except eventlet.Timeout:
        print("Превышено время ожидания при получении файла.")
    
bot.polling(none_stop=True, interval=5)