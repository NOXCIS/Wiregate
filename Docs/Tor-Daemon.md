## Tor

WireGate includes the complied binaries for the following Tor Transort Plugins:
  
- **Lyrebird** (meek_lite,obfs2,obfs3,obfs4,scramblesuit)
- **SnowFlake**
- **WebTunnel**
- 
Plugin choice can be seleted during installation or updated with docker compose. Also at a random intervals between **100** & **1642** seconds, **WireGate will Obtain a new Tor Circuit** if Tor is Enabled.

## Help
All Wiregate supporting configurations can be found in the Global Configs Folder.
If you need assistance, simply run:

```bash
sudo ./install.sh help
```
This will display the usage instructions and available options.
