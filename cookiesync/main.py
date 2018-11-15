from band import expose, cleanup, worker, settings, logger, response, redis_factory
from .structs import State
from .helpers import pairs, gen_key


state = State(partners=settings.partners)


async def save_match(uid, partner, partner_id):
    if state.redis_pool:
        with await state.redis_pool as conn:
            return await conn.execute('HMSET', gen_key(uid), partner, partner_id)
    logger.warn('redis pool not ready')


@expose()
async def matches(uid):
    # не пананятнааааа
    if state.redis_pool:
        with await state.redis_pool as conn:
            matches = await conn.execute('HGETALL', gen_key(uid))
            return {k: v for k, v in pairs(matches or [])}

# Перенести остальное, попутно разобравшись с переносимым...

