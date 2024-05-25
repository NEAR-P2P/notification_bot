#!/usr/bin/python
# coding=utf-8

from subprocess import Popen
import sys
import time

filename = sys.argv[1]
while True:
    print("\nEn ejecución archivo " + filename)
    p = Popen("python3 " + filename, shell=True)
    p.wait()
    time.sleep(30)