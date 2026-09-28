# Dependencies and protocol references

This repository contains the standalone exporter code and synthetic tests, not the
preservation server, game models, game client, assets, or captured account fixtures.
Dependencies are installed separately using the locked versions in `uv.lock`.

Direct dependencies: mitmproxy (MIT), msgpack-python (Apache-2.0), python-lz4 (BSD),
and python-qrcode (BSD). Their own distributions contain their licenses; this
repository's MIT license does not replace dependency license terms.

Protocol interoperability work was informed by the public TeamOpenSirius/OpenSiriusServer
and UnknownSekai/server-of-dreams projects, and by inspection of the account owner's
captured responses. No server implementation or generated game model files are bundled.
The envelope decoder implements MessagePack-CSharp LZ4 extension formats 98/99.

References:
- https://github.com/TeamOpenSirius/OpenSiriusServer
- https://github.com/UnknownSekai/server-of-dreams
- https://github.com/MessagePack-CSharp/MessagePack-CSharp
- https://docs.mitmproxy.org/stable/concepts/modes/#wireguard
