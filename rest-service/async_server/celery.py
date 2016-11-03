from __future__ import absolute_import, unicode_literals
from celery import Celery

app = Celery('async_server',
             broker='amqp://',
             backend='amqp://',
             include=['async_server.tasks'])

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=3600,  # TODO: May be this time is too low
)

if __name__ == '__main__':
    app.start()
