#!/usr/bin/env python 
# -*- coding:utf-8 -*-
__author__ = 'Rambo'

'''
Models for user, blog, comment.
'''

import orm
import asyncio,random,string
from models import User, Blog, Comment,next_id

def random_email():
    qq = random.randint(100000000, 999999999)
    return str(qq)+'@qq.com'

def random_name():
    return ''.join(random.sample(string.ascii_letters, 5))
async def test(loop):
    await orm.create_pool(loop=loop, user='www-data', password='password', db='awesome')

    u = User(name='Rambo', email='1434284872@qq.com', passwd='123456', image='about:blank')
    #1. 测试插入方法
    #for x in range(100):
    #    u['id'] = next_id()
    #    u['email'] = random_email()
    #    u['name'] = random_name()
    #    await u.save()

    #2. 测试根据主键查询方法
    #u = await User.find('001566390616379ed737289365a45369bb5c38e6c4e8f6b000')

    #3. 测试根据参数查询方法
    #u = await User.findAll(where='name like ?', args=['%a%'], orderBy='name asc', limit=(0, 10))

    #4. 测试findNumber方法，不知道这个方法有什么用
    #u = await User.findNumber('name')

    #5. 测试更新方法
    u = await User.find('0015663792976551f2b1435dd66457fa058724b6c2355fb000')
    u['passwd'] = '123'
    await u.update()

    #6. 测试删除方法
    #u = await User.find('00156637739231922c18a8775804bb29dfff7a6f79981c6000')
    #await u.remove()

    print(u)
loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.run_forever()

for x in test(loop):
    pass