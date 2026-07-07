#docker build -t mam10eks/ntcir-tot:eval-0.0.1 .
FROM ubuntu:24.04

ADD trec_eval /usr/bin/trec_eval

RUN apt-get update && apt-get install -y python3

