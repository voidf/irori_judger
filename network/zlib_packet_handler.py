from loguru import logger
import zlib
from network.misc import *
import asyncio
import traceback

class RequestHandlerMeta(type):
    def __call__(cls, *args, **kwargs):
        handler = super().__call__(*args, **kwargs)
        handler.on_connect()
        try:
            handler.handle()
        except BaseException:
            logger.exception('Error in base packet handling')
            raise
        finally:
            handler.on_disconnect()

class ZlibPacketHandler():
    proxies = []

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.timeout = 15
        self.client_address = writer.get_extra_info('peername')
        print(self.client_address)
        self._initial_tag = None
        self._got_packet = False

    async def recv(self, n: int) -> bytes:
        """最多读n个byte"""
        if n > MAX_ALLOWED_PACKET_SIZE:
            logger.warning(
                f'Disconnecting client due to too-large message size ({n} bytes): {self.client_address}')
            raise Disconnect()
        return await asyncio.wait_for(self.reader.read(n), self.timeout)

    async def recvn(self, n: int) -> bytes:
        """保证读n个byte"""
        if n > MAX_ALLOWED_PACKET_SIZE:
            logger.warning(
                f'Disconnecting client due to too-large message size ({n} bytes): {self.client_address}')
            raise Disconnect()
        return await asyncio.wait_for(self.reader.readexactly(n), self.timeout)

    async def read_sized_packet(self, size, initial=None):
        if size > MAX_ALLOWED_PACKET_SIZE:
            logger.warning(
                f'Disconnecting client due to too-large message size ({size} bytes): {self.client_address}')
            raise Disconnect()

        buffer = []
        remainder = size

        if initial:
            buffer.append(initial)
            remainder -= len(initial)
            assert remainder >= 0
        buffer.append(await self.recvn(remainder))
        await self._on_packet(b''.join(buffer))

    def parse_proxy_protocol(self, line):
        words = line.split()

        if len(words) < 2:
            raise Disconnect()

        if words[1] == b'TCP4':
            if len(words) != 6:
                raise Disconnect()
            self.client_address = (utf8text(words[2]), utf8text(words[4]))
        elif words[1] == b'TCP6':
            self.client_address = (
                utf8text(words[2]), utf8text(words[4]), 0, 0)
        elif words[1] != b'UNKNOWN':
            raise Disconnect()

    async def read_size(self, buffer=b'') -> int:
        return size_pack.unpack(await self.recvn(size_pack.size))[0]

    async def read_proxy_header(self, buffer=b'') -> bytes:
        # Max line length for PROXY protocol is 107, and we received 4 already.
        while b'\r\n' not in buffer:
            if len(buffer) > 107:
                raise Disconnect()
            data = await self.recv(107)
            if not data:
                raise Disconnect()
            buffer += data
        return buffer

    async def _on_packet(self, data):
        decompressed = zlib.decompress(data).decode('utf-8')
        self._got_packet = True
        logger.debug(decompressed)
        await self.on_packet(decompressed)

    async def on_packet(self, data):
        raise NotImplementedError()

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_timeout(self):
        pass

    async def handle(self):
        try:
            tag = await self.read_size()
            self._initial_tag = size_pack.pack(tag)
            if self.client_address[0] in self.proxies and self._initial_tag == b'PROX':
                proxy, _, remainder = await self.read_proxy_header(self._initial_tag).partition(b'\r\n')
                self.parse_proxy_protocol(proxy)

                while remainder:
                    while len(remainder) < size_pack.size:
                        await self.read_sized_packet(await self.read_size(remainder))
                        break

                    size = size_pack.unpack(remainder[:size_pack.size])[0]
                    remainder = remainder[size_pack.size:]
                    if len(remainder) <= size:
                        await self.read_sized_packet(size, remainder)
                        break

                    self._on_packet(remainder[:size])
                    remainder = remainder[size:]
            else:
                await self.read_sized_packet(tag)

            while True:
                await self.read_sized_packet(await self.read_size())
        except Disconnect:
            return
        except zlib.error:
            if self._got_packet:
                logger.warning(
                    f'Encountered zlib error during packet handling, disconnecting client: {self.client_address}\n{traceback.format_exc()}')
            else:
                logger.info(
                    f'Potentially wrong protocol (zlib error): {self.client_address}: {self._initial_tag}\n{traceback.format_exc()}')
        except asyncio.TimeoutError:
            if self._got_packet:
                logger.info(f'Socket timed out: {self.client_address}')
                self.on_timeout()
            else:
                logger.info(
                    f'Potentially wrong protocol: {self.client_address}: {self._initial_tag}')
        except Exception as e:
            logger.error(e)
            # When a gevent socket is shutdown, gevent cancels all waits, causing recv to raise cancel_wait_ex.
            # if e.__class__.__name__ == 'cancel_wait_ex':
                # return
            raise

    async def send(self, data):
        compressed = zlib.compress(data.encode('utf-8'))
        self.writer.write(size_pack.pack(len(compressed)) + compressed)
        await self.writer.drain()

    def close(self):
        self.writer.close()
