import json
import telegram
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove,
                      KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters)
import logging
from availability import get_available_carparks_page, fetch_carpark_avail_all, retrieve_carpark_by_id, Position, Page
from utils import haversine
from secret import TELEGRAM_TOKEN
from config import PAGE_SIZE, DISTANCE_RADIUS_KM


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

car_emoji = "🚗"


def start(bot, update):
    user = update.message.from_user
    location_keyboard = KeyboardButton(
        text="Send current location", request_location=True)
    update.message.reply_text(
        "Hi {}, I will help you find nearby carparks, but first, please send me your location".format(
            user.first_name),
        reply_markup=ReplyKeyboardMarkup([[location_keyboard]]))


def help(bot, update):
    update.message.reply_text("Help?!")


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def format_carpark(carpark, distance=None):
    total_lots = carpark.total_lots if carpark.total_lots not in (
        0, None) else "Unknown"
    location_url = f"https://www.google.com/maps/search/?api=1&query={carpark.position.latitude},{carpark.position.longitude}"
    result = f"Carpark ID: [{carpark.id}]({location_url}) | Address: {carpark.address} | Lots left: {carpark.available_lots}/{total_lots}"
    if distance is None:
        return result
    else:
        return result + f" | Distance from here: {int(distance*1000)}m"


def format_reply(carparks, current_pos):
    reply = car_emoji + f" *Here are the nearest available carparks (within {DISTANCE_RADIUS_KM}km distance):* \n\n"
    reply += '\n'.join(["*" + str(index + 1) + ".* " + format_carpark(carpark, haversine(current_pos.latitude, current_pos.longitude, carpark.position.latitude, carpark.position.longitude))
                        for index, carpark in enumerate(carparks)])
    reply += "\n\n For more details for each carpark click one of the buttons below"
    return reply


def get_keyboard(carparks, current_page, lat, lon):
    carpark_info_kb = [InlineKeyboardButton(
        str(i + 1), callback_data=cp.id) for i, cp in enumerate(carparks)]
    nested_keyboard = []
    if current_page.has_prev():
        page = current_page.prev_page()
        callback_data = {
            "start": page.start,
            "end": page.end,
            "lat": lat,
            "lon": lon
        }
        nested_keyboard.append(InlineKeyboardButton(
            "⬅️ Previous Page", callback_data=json.dumps(callback_data)))
    if current_page.has_next():
        page = current_page.next_page()
        callback_data = {
            "start": page.start,
            "end": page.end,
            "lat": lat,
            "lon": lon
        }
        nested_keyboard.append(InlineKeyboardButton(
            "Next Page ➡️", callback_data=json.dumps(callback_data)))
    return [carpark_info_kb, nested_keyboard]


def nearest_carparks(bot, update):
    if not update.message:
        is_callback = True
        logger.info("callback message")
        callback_data = json.loads(update.callback_query.data)
        logger.info(f"callback data: {callback_data}")
        current_page = Page(callback_data['start'], callback_data['end'])
        latitude, longitude = callback_data['lat'], callback_data['lon']
    else:
        is_callback = False
        current_page = Page(0, PAGE_SIZE)
        user = update.message.from_user
        latitude, longitude = update.message.location.latitude, update.message.location.longitude
        logger.info("Location of %s: %f / %f", user.first_name, latitude,
                    longitude)

    current_pos = Position(latitude, longitude)
    carparks, current_page = get_available_carparks_page(current_pos, radius=DISTANCE_RADIUS_KM, limit=None, page=current_page)

    reply_kb = get_keyboard(carparks, current_page, latitude, longitude)
    reply_markup = InlineKeyboardMarkup(reply_kb)

    if is_callback:
        bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id,
            text=format_reply(carparks, current_pos),
            disable_web_page_preview=True,
            parse_mode=telegram.ParseMode.MARKDOWN,
            reply_markup=reply_markup)
    else:
        update.message.reply_markdown(
            text=format_reply(carparks, current_pos),
            disable_web_page_preview=True,
            reply_markup=reply_markup)


def format_carpark_details(carpark):
    return str(carpark)


def single_carpark_details(bot, update):
    carpark_id = update.callback_query.data
    logger.info(f"Retrieve single carpark details for carpark id {carpark_id}")
    cp = retrieve_carpark_by_id(carpark_id)
    bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        text=format_carpark_details(cp),
        parse_mode=telegram.ParseMode.MARKDOWN
    )


def handle_callback(bot, update):
    try:
        json.loads(update.callback_query.data)
        nearest_carparks(bot, update)
    except json.decoder.JSONDecodeError:
        single_carpark_details(bot, update)


def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CallbackQueryHandler(handle_callback))

    location_handler = MessageHandler(
        Filters.location, nearest_carparks, edited_updates=True)
    dp.add_handler(location_handler)

    dp.add_error_handler(error)

    updater.start_polling()
    logger.info('----- Bot running -----')
    j = updater.job_queue
    j.run_repeating(lambda bot, job: fetch_carpark_avail_all(),
                    interval=90, first=0)
    updater.idle()


if __name__ == '__main__':
    main()
