from __future__ import absolute_import, unicode_literals
from celery import Celery
import os

# port = os.environ['REDIS_PORT_6379_TCP_PORT']
# host = os.environ['REDIS_PORT_6379_TCP_ADDR']
# redis_uri = "redis://{0}:{1}/0".format(host, port)
redis_uri = "redis://redis:6379"
rabbit_mq = 'amqp://'

app = Celery('async_server',
             broker=redis_uri,
             backend=redis_uri,
             include=['async_server.tasks'])

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=None,        # Celery will keep values forever TODO
    task_track_started=True,    # Tasks will show started status
)

if __name__ == '__main__':
    app.start()
