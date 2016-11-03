from __future__ import absolute_import, unicode_literals
from celery import Celery

app = Celery('async_server',
             broker='amqp://',
             backend='amqp://',
             include=['async_server.tasks'])

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=None,        # Celery will keep values forever
    task_track_started=True,    # Tasks will show started status
)

if __name__ == '__main__':
    app.start()
