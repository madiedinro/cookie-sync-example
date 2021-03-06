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



@expose.handler(alias='cs', name='i')
async def init(uid, data, **params):
    """
    Will be redirected to partner `sync` location.
    Otherwice pixel will be returned and written error to logs.
    """
    partner_name = data.get('p', None)
    partner = state.get_partner(partner_name)
    if partner and partner.init:
        logger.info('init: partner and init link found. redirecting')
        pix = partner.init.format(partner_id=uid)
        return response.redirect(pix)
    logger.warn('partner not found', p=partner_name)
    return response.pixel()


@expose.handler(alias='cs', name='s')
async def sync(uid, data, **params):
    """
    Will be redirected to partner `done` location.
    If error occur will be returned pixel.
    """
    partner_name = data.pop('p', None)
    partner_id = data.pop('pi', None)
    partner = state.get_partner(partner_name)
    if partner and partner_id:
        logger.info('sync: partner found. saving match', p=partner_name)
        await save_match(uid, partner_name, partner_id)
        if partner.sync:
            logger.info('sync: sync pixel configured. redirecting')
            pix = partner.sync.format(partner_id=uid, user_id=partner_id)
            return response.redirect(pix)
    logger.warn('partner not found', p=partner_name)
    return response.pixel()


@expose.handler(alias='cs', name='d')
async def done(uid, data, **params):
    """
    Receiving syncronization results and show pixel
    """
    partner_name = data.pop('p', None)
    partner_id = data.pop('pi', None)
    partner = state.get_partner(partner_name)
    user_id = data.pop('ui', None)
    if uid != user_id:
        logger.warn('user ids not equal')
        return response.pixel()
    if partner and partner_id and user_id:
        logger.info('done: params given. saving', p=partner_name, pid=partner_id, u=user_id)
        await save_match(uid, partner_name, partner_id)
    else:
        logger.warn('not enough params', p=partner_name, pid=partner_id, u=user_id)
    return response.pixel()


@worker()
async def startup():
    state.redis_pool = await redis_factory.create_pool()


@cleanup()
async def shutdown():
    state.redis_pool.close()
    await state.redis_pool.wait_closed()


