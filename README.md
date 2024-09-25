# Pwnagotchi plugins made for my builds

### [displaydriverupdate.sh](https://github.com/RasTacsko/Pwnagotchi-plugins/blob/main/displaydriverupdate.sh "displaydriverupdate.sh")

A  bash script that downloads my pwny repo with the updated display drivers, and copies it to the necessary folders.
Be aware that is made with chat gpt, and it is need internet connection of course, so use at your own risk...
Just copy/create the file in /home/pi for example, 
```bash
sudo chmod +x displaydriverupdate.sh
sudo ./displaydriverupdate.sh
```
It will ask you what fw you have (32/64bit), and after updateing it cleans up the downloaded files.
Future plan: update the config.txt if needed for the spi LCD screens (`dtoverlay=spi0-0cs` to `dtoverlay=spi0-1cs`)

### [**gpiocontrol.py**](https://github.com/RasTacsko/Pwnagotchi-plugins/blob/main/gpiocontrol.py "gpiocontrol.py")

An updated version of the default gpio_buttons plugin, based on gpiozero package instead of RPi.gpio
It supports buttons (short and long press) and encoders (2 encoder pins, plus one button).
**Config**:
```toml
# Config for buttons should include the gpio number of the button and the commands to run.
#It needs separate lines for short/long press commands
main.plugins.gpiocontrol.gpios.17.short_press = "echo 'Short Press on GPIO 17'"
main.plugins.gpiocontrol.gpios.17.long_press = "echo 'Long Press on GPIO 17'"

# Config for encoders should include the gpio number of the encoder pins, the gpio number of the button pin, and the commands to run.
#It needs separate lines for up/down and short/long press commands.
main.plugins.gpiocontrol.encoder.a = 5
main.plugins.gpiocontrol.encoder.b = 6
main.plugins.gpiocontrol.encoder.button = 13
main.plugins.gpiocontrol.encoder.up_command = "echo 'Encoder Rotated Up'"
main.plugins.gpiocontrol.encoder.down_command = "echo 'Encoder Rotated Down'"
main.plugins.gpiocontrol.encoder.short_press = "echo 'Encoder Button Short Pressed'"
main.plugins.gpiocontrol.encoder.long_press = "echo 'Encoder Button Long Pressed'"
```


