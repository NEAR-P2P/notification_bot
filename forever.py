#!/usr/bin/python
# coding=utf-8

from subprocess import Popen
import sys
import time

filenames = sys.argv[1:]  # Accept multiple filenames as arguments
processes = []

while True:
    for filename in filenames:
        print("\nEn ejecución archivo " + filename)
        p = Popen("python3 " + filename, shell=True)
        processes.append(p)

    # Wait for all processes to finish
    for p in processes:
        p.wait()

    # Restart after a delay
    time.sleep(30)