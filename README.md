# bluetooth-smartbulb

An application to control the leds of the [Xindao P330.83 smart led bulb](https://www.xindao.com/en-gb/smart-bulb-with-wireless-speaker-white-p330.083) using a bluetooth enabled computer. The bulb contains a speaker as well, which can be controlled over A2DP.

It should work on any bluetooth smartbulb for which the MAC address starts with C9:7, C9:8 or C9:A. Please note that this application is developed and tested for one only on emodel of smartbulb, capabilities may differ between models and it is not clear how they can be properly detected.

## Network protocol

The network protocol is a variation on 'Chsmartbulb', see the github projects [Chsmartbulb-led-bulb-speaker](https://github.com/pfalcon/Chsmartbulb-led-bulb-speaker) and [Bluetooth-Chsmartbulb-Python-API](https://github.com/samsam2310/Bluetooth-Chsmartbulb-Python-API).

Once the bluetooth connection is set up using the SPP service the string 01234567 must be sent to initialize the communication. No reply is expected on this message.

### General message format

Apart from the initialization all messages to and from the bulb have the same structure:
```
protocol identifier  01fe0000
read/write mode      for writing datat to the bulb use 0x51, the bulb will respond with 0x41
bulb function        1 byte indicating which action is requested from the bulb (see below)
length               1 byte, total length of message including the protocol identifier, write flag, etc
payload              length-7 bytes, parameters for the requested action
```

### Functions

For some actions or requests it is not clear how to interpret the result.

| Function | Description |
| -------- | ----------- |
| `0x00` | This function takes a 9 bytes parameter `0x000000008000000080` and returns some information, which are most likely the capabilities of the bulb. |
| `0x02` | Heartbeat. The official app sends this message about once per second, but it turns out to be unnecessary. Input is `0x000000008000000080`, output depends on the model. |
| `0x80` | Request lamp information. Parameter is `0x000000000000000000`, the return message contains the name of the bulb among other information. |
| `0x81` | Control the lamp. The parameter of this functions starts with `0x000000000000000000`, followed by a message indicating which parameter to control. See below for details. |

### Subfunctions of function 0x81

```
identifier   0x0d
length       1 byte, total length of the subfunction message including `0x0d`
color mode   0x01 enables the white leds (white mode), 0x02 the red, green and/or blue leds (color mode)
unknown      0x03
subfunction  1 byte indicating the parameter to modify (see below)
payload      length-6 bytes with extra parameters if necessary
terminator   0x0e
```

| Subfunction | Description |
| -------- | ----------- |
| `0x00` | Read current color mode, color and brightness |
| `0x01` | Set color mode and power. The payload indicates the power state. `0x01` turns the power on, `0x02` turns the power off |
| `0x02` | Set the brightness, works only when the bulb is white mode. The payload indicates the brightness, valid values range from `0x01` to `0x10` |
| `0x03` | Set the color when the bulb is in color mode. The payload contains 3 bytes for red, green and blue, followed by `0x00` |
| `0x04` | Set party mode. The payload contains 1 byte indicating which mode to select. `0x00` is party mode off, `0x01`, `0x02` or `0x03` will set light on the rythm of the sound, `0x04` is rainbow, `0x05` is pulse and `0x06` is candle. For the last mode you can set the color first. |

## Colors

The bulb contains white, red, green and blue leds. When the bulb is set to white mode then only the white leds will light up. The specific model described here does not support setting a color temperature, but it can be simulated in color mode. See the method set_white_temperature.

When in color mode the white leds are always turned off and in theory there are 16,7 million colors to choose from (24 bit). However, some colors cannot be mixed well by the bulb. For example #888888 will result in some kind of dimmed white and #FFFFFF will be some kind of blueish white, because the blue leds have slightly more power.
The bulb class allows you to set any RGB color you like by using the set\_color\_rgb method, but because of the baove limitation it is preferred to set the color using the method set\_color\_hsv. The hue can be given in degrees, 0 will result in red, 120 in green, 240 in blue, and values in between will mix at most two colors. Saturation will automatically be set to 100% in this method to avoid a third color mixed in, since this will almost always result in some shade of white light.

## Disclaimer

All information in this document is obtained by trial and error, without logging the communication of the included app. It may or may not work for you, use at your own risk.

