#!/bin/bash

echo "Launch gunicorn"
gunicorn -b 0.0.0.0:8000 routes:app --reload -t 120
