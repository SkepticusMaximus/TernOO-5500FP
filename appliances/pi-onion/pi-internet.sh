#!/bin/sh
ip route replace default via 10.55.0.24 dev usb0
resolvectl dns usb0 8.8.8.8 1.1.1.1
resolvectl domain usb0 '~.'
