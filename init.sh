g++ sandbox.cpp -o sb.elf -lpthread -static
docker build -t sandbox:sb .
docker run -dit --name sbsb sandbox:sb