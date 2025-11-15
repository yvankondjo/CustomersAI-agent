#!/usr/bin/env python3
import os
import sys
from rq import Worker, Queue, Connection
from app.workers.queue import redis_conn, document_queue, website_queue

if __name__ == "__main__":
    with Connection(redis_conn):
        worker = Worker([document_queue, website_queue])
        worker.work()

