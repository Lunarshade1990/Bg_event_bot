from aiogram import Router

from bot.app.handlers import games, imports, meetups, profile, random_game, start

router = Router()
router.include_router(start.router)
router.include_router(profile.router)
router.include_router(games.router)
router.include_router(imports.router)
router.include_router(meetups.router)
router.include_router(random_game.router)
