FROM busybox:latest
RUN adduser sandbox -u 1111 -h /sandbox -D
COPY sb.elf /root/
