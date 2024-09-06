import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
loglevel = 'info'
accesslog = '-'
errorlog = '-'
timeout = 120
