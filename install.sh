#!/bin/bash
function green {
    echo "\e[032m$1\e[0m";
}

chmod +x wizarddes.py
echo -e "Copy" $(green "wizzardes") "executable to" $(green "/usr/bin/")  
sudo cp wizarddes.py /usr/bin/wizarddes
DIR="/etc/wizarddes"
if [ -d "$DIR" ]; then
    echo -e "Cleaning" $(green $DIR) "directory"
    rm -rfv $DIR/*
else
    echo -e "Creating" $(green $DIR) "directory"
    sudo mkdir $DIR
fi
echo -e "Copy" $(green "'rules'") "to" $(green $DIR)  
sudo cp rules /etc/wizarddes/rules
echo -e "Copy" $(green "'app_runners'") "to" $(green $DIR)  
sudo cp app_runners /etc/wizarddes/app_runners