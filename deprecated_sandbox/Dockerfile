FROM alpine:latest
RUN adduser sandbox -u 1111 -h /sandbox -D && sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories && apk update && apk add python2 && apk add python3
COPY sb.elf /usr/sbin/
WORKDIR /usr/sbin/