# coding=utf-8
import queue
import threading
import time

q = queue.Queue()


def main_thread(a, b):
    print(a)
    print('main thread')


arg = (1, 2)
main_thread(*arg)
