FROM python:3.6
MAINTAINER masatora <atarashi.masatora@gmail.com>
RUN pip3 install flask
RUN pip3 install requests
COPY blockchain.py ./
CMD ["python3", "blockchain.py", "5000"]
