#!/bin/sh
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

venv_python="./venv/bin/python3"
venv_gunicorn="./venv/bin/gunicorn"
pythonExecutable="python3"
TOP_PID=$$


_check_and_set_venv(){
    VIRTUAL_ENV="./venv"
    
    # Check if the virtual environment exists, if not, create it
    if [ ! -d $VIRTUAL_ENV ]; then
        printf "[WGDashboard][Docker] Creating Python Virtual Environment under ./venv\n"
        { $pythonExecutable -m venv $VIRTUAL_ENV; } >> ./log/install.txt
        if [ $? -ne 0 ]; then
            printf "[WGDashboard][Docker] Failed to create Python Virtual Environment. Halting now.\n"
            kill $TOP_PID
            exit 1
        fi
    fi
    
    # Check if the virtual environment is activated correctly
    if ! $venv_python --version > /dev/null 2>&1; then
        printf "[WGDashboard][Docker] %s Python Virtual Environment under ./venv failed to create. Halting now.\n" "$heavy_crossmark"
        kill $TOP_PID
        exit 1
    fi
    
    source ${VIRTUAL_ENV}/bin/activate
    if [ $? -ne 0 ]; then
        printf "[WGDashboard][Docker] Failed to activate virtual environment. Halting now.\n"
        kill $TOP_PID
        exit 1
    fi
}

build_core () {
    # Check if the log directory exists, if not, create it
    if [ ! -d "log" ]; then
        printf "[WGDashboard][Docker] Creating ./log folder\n"
        mkdir "log"
        if [ $? -ne 0 ]; then
            printf "[WGDashboard][Docker] Failed to create ./log folder. Halting now.\n"
            exit 1
        fi
    fi

    # Install required packages
    apk add --no-cache python3 net-tools python3-dev py3-virtualenv
    if [ $? -ne 0 ]; then
        printf "[WGDashboard][Docker] Failed to install dependencies. Halting now.\n"
        exit 1
    fi

    _check_and_set_venv

    # Upgrade pip
    printf "[WGDashboard][Docker] Upgrading Python Package Manager (PIP)\n"
    { date; python3 -m pip install --upgrade pip; printf "\n\n"; } >> ./log/install.txt
    if [ $? -ne 0 ]; then
        printf "[WGDashboard][Docker] Failed to upgrade pip. Halting now.\n"
        exit 1
    fi

    # Install dependencies from builder_requirements.txt
    printf "[WGDashboard][Docker] Building Bcrypt & Psutil\n"
    { date; python3 -m pip install -r builder_requirements.txt; printf "\n\n"; } >> ./log/install.txt
    if [ $? -ne 0 ]; then
        printf "[WGDashboard][Docker] Failed to install dependencies. Halting now.\n"
        exit 1
    fi

    printf "[WGDashboard][Docker] Build Successful!\n"

    # Clean up pip
    printf "[WGDashboard][Docker] Clean Up Pip!\n"
    { date; rm -rf /opt/wireguarddashboard/src/venv/lib/python3.12/site-packages/pip*; printf "\n\n"; } >> ./log/install.txt
    if [ $? -ne 0 ]; then
        printf "[WGDashboard][Docker] Failed to clean up pip. Halting now.\n"
        exit 1
    fi
}


build_core
exit 0
