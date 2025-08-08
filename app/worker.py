from rq import Connection, Worker, Queue
from redis import Redis
import os

listen = ['transfers']

def run_worker():
    redis = Redis.from_url(os.getenv("REDIS_URL"))
    with Connection(redis):
        worker = Worker(map(Queue, listen))
        worker.work()

if __name__ == "__main__":
    run_worker()
