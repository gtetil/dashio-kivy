#echo 1 > /sys/class/backlight/rpi_backlight/bl_power

cd /
cd home/pi/dashio-kivy
sudo python3 main.py > dashio.log 2> dashio.err &
cd /
