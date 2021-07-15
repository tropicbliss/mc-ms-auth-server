#!/bin/bash

cd app
gunicorn main:app -w 3 -b 0.0.0.0:1338 -k uvicorn.workers.UvicornWorker