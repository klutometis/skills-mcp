---
description: Control LIFX lights via the LIFX HTTP API using $LIFX_TOKEN. Turn on/off, set brightness, color, or color temperature. Always uses fast=true.
---

# LIFX Light Control

Controls all LIFX lights on the account via the LIFX cloud HTTP API.
Requires `$LIFX_TOKEN` in the environment.

## Always use `fast=true`

This bulb's cloud→device round-trip is **intermittently slow**. A normal
(`fast=false`) PUT frequently blocks ~6s and returns `status: timed_out`
**without actuating**. `fast=true` returns `202 Accepted` immediately and
the command lands reliably. Do not parse the body for success — fast mode
returns none; `http 202` means accepted. Verify with a state read if you
need confirmation.

## On — dim warm (good default)
```bash
curl -s -w "http=%{http_code}\n" -X PUT "https://api.lifx.com/v1/lights/all/state" \
  -H "Authorization: Bearer $LIFX_TOKEN" \
  -d "power=on&color=kelvin:1500&brightness=0.25&fast=true"
```

## Off
```bash
curl -s -w "http=%{http_code}\n" -X PUT "https://api.lifx.com/v1/lights/all/state" \
  -H "Authorization: Bearer $LIFX_TOKEN" -d "power=off&fast=true"
```

## Set color / brightness
`color` accepts a name (`blue`), `hue:0-360 saturation:0-1`, or
`kelvin:1500-9000` (1500 = warmest, 9000 = coolest). `brightness` is
`0.0`–`1.0`.
```bash
curl -s -w "http=%{http_code}\n" -X PUT "https://api.lifx.com/v1/lights/all/state" \
  -H "Authorization: Bearer $LIFX_TOKEN" \
  -d "power=on&color=hue:280 saturation:0.8&brightness=0.3&fast=true"
```

## Read current state (title, power, color, brightness)
```bash
curl -s -H "Authorization: Bearer $LIFX_TOKEN" https://api.lifx.com/v1/lights/all
```
