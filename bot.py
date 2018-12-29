import telegram
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters)
import logging
from availability import get_available_carparks, fetch_carpark_avail_all, Position
from secret import TELEGRAM_TOKEN
from config import NNEAREST, DISTANCE_RADIUS_KM


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
    result = f"Carpark ID: [{carpark.id}]({location_url}) | Address: {carpark.address} | Lots left: {carpark.available_lots} | Total lots: {total_lots}"
    if distance is None:
        return result
    else:
        return result + f" | Distance from here: {int(distance*1000)}m"


def format_reply(carparks):
    reply = car_emoji + f" *Here are the nearest {NNEAREST} available carparks (within {DISTANCE_RADIUS_KM}km distance):* \n\n"
    reply += '\n'.join([str(index + 1) + ". " + format_carpark(carpark)
                        for index, carpark in enumerate(carparks)])
    reply += "\n\n For more details for each carpark"
    return reply


def location(bot, update):
    user = update.message.from_user
    user_location = update.message.location
    logger.info("Location of %s: %f / %f", user.first_name, user_location.latitude,
                user_location.longitude)
    carparks = get_available_carparks(
        Position(user_location.latitude, user_location.longitude), radius=DISTANCE_RADIUS_KM, limit=NNEAREST)
    update.message.reply_markdown(text=format_reply(carparks))


def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help))

    location_handler = MessageHandler(
        Filters.location, location, edited_updates=True)
    dp.add_handler(location_handler)

    dp.add_error_handler(error)

    updater.start_polling()
    logger.info('----- Bot running -----')
    j = updater.job_queue
    j.run_repeating(lambda bot, job: fetch_carpark_avail_all(),
                    interval=60, first=0)
    updater.idle()


if __name__ == '__main__':
    main()
