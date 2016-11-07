export C_FORCE_ROOT=True
celery -A async_server worker -l info
