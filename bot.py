import telegram
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters)
import logging
from availability import get_available_lots
from secret import TELEGRAM_TOKEN


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def start(bot, update):
    user = update.message.from_user
    location_keyboard = KeyboardButton(
        text="Send current location", request_location=True)
    update.message.reply_text(
        "Hi {}, I will help you find nearby carparks, but first, please send me your location".format(user.first_name),
        reply_markup=ReplyKeyboardMarkup([[location_keyboard]]))


def help(bot, update):
    update.message.reply_text("Help?!")


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def format_reply(carparks):
    reply = "Here are the carparks nearby: \n"
    return reply + '\n'.join([str(carpark) for carpark in carparks])


def location(bot, update):
    user = update.message.from_user
    user_location = update.message.location
    logger.info("Location of %s: %f / %f", user.first_name, user_location.latitude,
                user_location.longitude)
    carparks = get_available_lots(
        user_location.latitude, user_location.longitude)
    update.message.reply_text(
        text=format_reply(carparks), parse_mode=telegram.ParseMode.MARKDOWN)


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
    updater.idle()


if __name__ == '__main__':
    main()
