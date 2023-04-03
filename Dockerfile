FROM python:3
# as of writing, GitHub Actions runs in an environment with a version of sqlite3 too old
# we need at least 3.26 to do upserts (INSERT ... ON CONFLICT UPDATE)
# python:3 ships with sqlite3.sqlite_version = '3.27.2'

ADD requirements.txt .
RUN pip install --requirement requirements.txt ruff
