import orm
import asyncio
from models import User, Blog, Comment


async def test(loop):
    await orm.create_pool(loop=loop, user='www-data', password='password', db='awesome')

    u = User(name='lifangfang', email='fangfangli@example.com',
             passwd='password', image='about:blank')
    u = User(name='Rambo', email='1434284872@qq.com', passwd='123456', image='about:blank')
    await u.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.run_forever()

for x in test(loop):
    pass