FROM alpine:latest
RUN adduser sandbox -u 1111 -h /sandbox -D
COPY sb.elf /usr/sbin/
WORKDIR /usr/sbin/