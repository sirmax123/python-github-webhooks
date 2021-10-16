======================
Python GitHub Webhooks
======================

Это форк репозитория https://github.com/carlos-jenkins/python-github-webhooks
с некоторыми изменениями в том числе добавлена поддержка gogs

Установка
=======

::

  Скопировать в /usr/local/webhook/python-github-webhooks (в соответвии м путем в webhook.service)
  * файл webhook.service - в /etc/systemd/system
  * chown www-data:www-data -R ./hooks (пользователь может быть и другой - но нужно поменять в файле webhook.service)



Установка зависимостей
============

::

   sudo pip install -r requirements.txt
   или если не лень - то поставить из пакетов (для 2-го питона!)

Настройка
=====
``config.json`` - пример простой конфигурации

::

    {
        "github_ips_only": true,
        "enforce_secret": "",
        "return_scripts_info": true,
        "hooks_path": "/.../hooks/"
    }

:github_ips_only: Только адреса гитхаба, которые можно получить динамически у самого гитхаба
 `GitHub Meta <https://developer.github.com/v3/meta/>`_
:enforce_secret: Проверять подпись ``X-Hub-Signature``.
 `GitHub WebHooks Documentation <https://developer.github.com/v3/repos/hooks/>`_.
:hooks_path: Путь к файлам хуков

Хуки
============

По сути это просто код на питоне, и имя файла определяется по событию имени репозитория и бранче
(при этом никто не мешает проверять все поля например в коде хука дополнительно)
::

    hooks/{event}-{name}-{branch}
    hooks/{event}-{name}
    hooks/{event}
    hooks/all

The application will pass to the hooks the path to a JSON file holding the
payload for the request as first argument. The event type will be passed
as second argument. For example:

::
   В репозитории включен хук all и пример дженкис кода на groovy 
   который по сути ничего не делает кроме как  показывает содержимое
   в этом файле можно при желании написать обработчик для вызова отдельных
   джоб для разных условий, что бы не тянуть логику обработки в код на питоне

    hooks/push-myrepo-master /tmp/sXFHji push

Hooks can be written in any scripting language as long as the file is
executable and has a shebang. A simple example in Python could be:

::

    #!/usr/bin/env python
    # Python Example for Python GitHub Webhooks
    # File: push-myrepo-master

    import sys
    import json

    with open(sys.argv[1], 'r') as jsf:
      payload = json.loads(jsf.read())

    ### Do something with the payload
    name = payload['repository']['name']
    outfile = '/tmp/hook-{}.log'.format(name)

    with open(outfile, 'w') as f:
        f.write(json.dumps(payload))

Not all events have an associated branch, so a branch-specific hook cannot
fire for such events. For events that contain a pull_request object, the
base branch (target for the pull request) is used, not the head branch.

The payload structure depends on the event type. Please review:

    https://developer.github.com/v3/activity/events/types/


Deploy
======

Nginx
------

::

server {
    listen 25001 default_server;
    root /var/www/html;
    server_name _;
    access_log /var/log/nginx/github-to-jenkins-proxy-access.log postdata;
    error_log /var/log/nginx/github-to-jenkins-proxy-error.log;

    location / {
        client_body_buffer_size      64k;
        client_body_in_single_buffer on;
        proxy_pass                   http://127.0.0.1:25002;
        proxy_set_header             Host $host:$server_port;
        proxy_set_header             X-Real-IP $remote_addr;
        proxy_set_header             X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header             X-Forwarded-Proto $scheme;
        proxy_http_version           1.1;
        proxy_request_buffering      off;
    }
}


You can now register the hook in your Github repository settings:

    https://github.com/youruser/myrepo/settings/hooks

To register the webhook select 
* Content type: ``application/json``
* URL  http://my.site.com:2501

Docker
------

::  
 по желанию

License
=======

::
  Я конечно немного доработал код но оставляю оригинадльную лицензию

   Copyright (C) 2014-2015 Carlos Jenkins <carlos@jenkins.co.cr>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing,
   software distributed under the License is distributed on an
   "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
   KIND, either express or implied.  See the License for the
   specific language governing permissions and limitations
   under the License.


Credits
=======

This project is just the reinterpretation and merge of two approaches:

- `github-webhook-wrapper <https://github.com/datafolklabs/github-webhook-wrapper>`_.
- `flask-github-webhook <https://github.com/razius/flask-github-webhook>`_.

Thanks.
