# MPRIS Control

A simplified MPRIS server-client system for local and remote control of media players.

## Server

command-line arguments:

- `-tcp` - Runs as a TCP server for the client to connect to
- `-info` - Shows MPRIS Player song information
- `-control` - Control media playback from the server itself
- `-reselect` - Reselects the preferred MPRIS Player

## Client
_Work in progress..._

Connecting to the Server
- `mpris-client.py ip:port`

## Dependencies
- dbus-python

