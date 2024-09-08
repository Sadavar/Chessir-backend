import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
loglevel = 'info'
accesslog = '-'
errorlog = '-'
timeout = 120
bind = '0.0.0.0:8000'
