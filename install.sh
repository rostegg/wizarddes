#!/bin/bash
function green {
    echo "\e[032m$1\e[0m";
}

chmod +x wizarddes.py
echo -e "Copy" $(green "wizzardes") "executable to" $(green "/usr/bin/")  
sudo cp wizarddes.py /usr/bin/wizarddes
DIR="${HOME}/.wizarddes"
if [ -d "$DIR" ]; then
    echo -e "Cleaning" $(green $DIR) "directory"
    rm -rfv $DIR/*
else
    echo -e "Creating" $(green $DIR) "directory"
    mkdir $DIR
fi
RULES_DIR="${DIR}/rules"
if [ -d "$RULES_DIR" ]; then
    echo -e "Cleaning" $(green $RULES_DIR) "directory"
    rm -rf $RULES_DIR
fi
echo -e "Copy" $(green "'rules'") "to" $(green $DIR)  
cp -R rules "${RULES_DIR}/" 

echo -e "Copy" $(green "'app_runners'") "to" $(green $DIR)  
cp app_runners "${DIR}/app_runners"