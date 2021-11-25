import asyncio
import aiogram
from aiogram import Bot, Dispatcher, types
from aiogram.types.input_file import InputFile
import utils
import traceback
pack = None

async def pack_updater(bot):
    global pack
    me = await bot.get_me()
    while True:
        if pack is None:
            try:
                pack = await bot.get_sticker_set(utils.config['stickerset_id'] + '_by_' + me.username)
            except:
                print('Stickerset not found. Creating the new one.')
                await bot.create_new_sticker_set(
                    utils.config['user_id'], utils.config['stickerset_id'] + '_by_' + me.username,
                    utils.config['stickerset_title'], png_sticker = InputFile(utils.config['sticker_template']), emojis='💵')
                pack = await bot.get_sticker_set(utils.config['stickerset_id'] + '_by_' + me.username)
        try:
            utils.GenerateStickers(utils.GetTopCoinPricesPlusDAO(n=utils.config['amount_of_stickers']-1),'usd')
        except Exception as e:
            print(f"\nSomething went wrong while generating stickers.\nInstead of updating sticker set I will halt for a minute. Probably error with the API.\n{traceback.format_exc()}")
            await asyncio.sleep(30)
            continue
        i = len(pack.stickers) - 1
        flag = False
        while i >= 0:
            try:
                await bot.delete_sticker_from_set(pack.stickers[i]['file_id'])
            except aiogram.utils.exceptions.BadRequest:
                pack = await bot.get_sticker_set(utils.config['stickerset_id'] + '_by_' + me.username)
            except Exception as e:
                print(f'Unhandled exception while deleting sticker from set: {traceback.format_exc()}')
                if not flag:
                    print('Waiting and trying to delete the sticker again..')
                    i += 1
                    pack = await bot.get_sticker_set(utils.config['stickerset_id'] + '_by_' + me.username)
                    await asyncio.sleep(5)
                    flag = True
                    continue
                flag = False
                print('Skipping...')
            i = len(pack.stickers)-1
            if flag:
                flag = False
                print("Success!")
        
        i = 0
        while i < utils.config['amount_of_stickers']:
            t = InputFile(f'stickers/{i}.png')
            try:
                await bot.add_sticker_to_set(utils.config['user_id'], utils.config['stickerset_id'] + '_by_' + me.username, png_sticker = t, emojis = '💵')
                await asyncio.sleep(0.1)
            except:
                print(f'Unhandled exception while loading sticker {i} to sticker set: {traceback.format_exc()}')
                if not flag:
                    print(f'\nWaiting and trying to load it again..')
                    i -= 1
                    pack = await bot.get_sticker_set(utils.config['stickerset_id'] + '_by_' + me.username)
                    await asyncio.sleep(3)
                    flag = True
                    continue
                flag = False
                print('Skipping...')
            i += 1
            if flag:
                flag = False
                print("Success!")
            
        await asyncio.sleep(utils.config['update_time']*60)

async def get_pack(event: types.Message):
    await event.answer_sticker(
        pack.stickers[0]['file_id']
    )

async def main():
    bot = Bot(token=utils.config['bot_token'])
    try:
        disp = Dispatcher(bot=bot, loop=asyncio.get_event_loop())
        disp.register_message_handler(get_pack, commands={"get_pack", "restart"})
        disp.loop.create_task(pack_updater(bot))
        await disp.start_polling()
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())