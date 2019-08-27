#!/usr/bin/env python 
# -*- coding:utf-8 -*-
__author__ = 'Michael Liao'

import asyncio, os, inspect, logging, functools

from urllib import parse

from aiohttp import web

from apis import APIError

def get(path):
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

def post(path):
    '''
    Define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

# 运用inspect模块，创建几个函数用以获取URL处理函数与request参数之间的关系
# 收集没有默认值的命名关键字参数
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters   #值为一个有序字典
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

#inspect.Parameter对象的kind属性是一个_ParameterKind枚举类型的对象，值为这个参数的类型（可变参数，关键词参数，etc）
#inspect.Parameter对象的default属性：如果这个参数有默认值，即返回这个默认值，如果没有，返回一个inspect._empty类。

# 获取命名关键字参数
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

# 判断有没有命名关键字参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

# 判断有没有关键字参数
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

# 判断是否含有名叫'request'参数，且该参数是否为最后一个参数
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

# RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，
# 调用URL函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求：
# RequestHandler是一个类，由于定义了__call__()方法，因此可以将其实例视为函数。

# 正式向request参数获取URL处理函数所需的参数
class RequestHandler(object):

    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    async def __call__(self, request):
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct = request.content_type.lower() #大写字符为小写
                if ct.startswith('application/json'): #检查字符串是否是以指定子字符串开头
                    #POST 提交数据方式,服务端消息主体是序列化后的 JSON 字符串
                    params = await request.json()
                    if not isinstance(params, dict):  #判断一个对象是否是一个dict（字典）类型
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params
                    # 键值对或表单
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                    # 内置函数dict(**kwarg)从一个字典参数构造一个新字典
                    # 以两个*开头的参数，就会收集成字典形式
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                # remove all unamed kw:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
                # urllib.parse.parse_qs(qs, keep_blank_values, strict_parsing=False)
                # 解析qs给出的查询字符串(例如'foo=bar&baz=qux'), 数据作为字典返回，保留空白字符串。
        if self._has_request_arg:
            kw['request'] = request
        # check required kw:
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

# 添加静态资源路径
def add_static(app):
    # os.path.abspath()返回绝对路径, os.path.dirname()返回path的目录名, os.path.join()将多个路径组合
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    # add_static(处理的静态资源的URL路径前缀, 文件系统中包含处理的静态资源的文件夹路径)
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))


# 注册URL处理函数
def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))
    # inspect.isgeneratorfunction(fn)判断是否为python生成器函数
    # inspect.signature(fn)将返回一个inspect.Signature类型的对象, 值为fn这个函数的所有参数
    # inspect.Signature对象的paramerters属性是一个mappingproxy(映射)类型的对象，值为一个有序字典(Orderdict)。
    # 这个字典里的key即为参数名，str类型; value是一个inspect.Parameter类型的对象，包含的一个参数的各种信息

    #这里出现了一个RequestHandler类，它具有call魔术方法，所以可以像调用函数一样调用其实例，
    # 这里RequestHandler类主要是对handler进行封装，获取request中传入的参数并传入handler中。

def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)