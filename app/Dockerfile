# setup
FROM        python:3.11-rc-alpine3.15

WORKDIR     /usr/app

RUN         apk --no-cache add curl


# copy files
# COPY        ./ ./
COPY        ./src/templates ./src/templates
COPY        ./src ./src
COPY        requirements.txt ./

# install dependencies
RUN         pip install -r requirements.txt

# set env vars
ENV         FLASK_APP=app.py
ENV         FLASK_RUN_HOST=0.0.0.0
# ENV         FLASK_RUN_HOST=127.0.0.2
# ENV         FLASK_RUN_HOST=192.168.0.1

# ENV         FLASK_DEBUG=1


EXPOSE 8080


WORKDIR     /usr/app/src
# run the app

# CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
CMD         ["flask", "run"]
# CMD         ["flask", "run"]
# CMD         ["flask", "run", "-h", "localhost", "-p", "8080"]
# CMD         ["flask", "run", "-h", "127.0.0.1", "-p", "8080"]
# CMD         ["flask", "run", "-h", "127.0.0.1", "-p", "5000"]
# CMD         ["flask", "run", "-h", "172.27.0.1", "-p", "5000"]


# docker build -t app --rm .
# docker run -it --rm app