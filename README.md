### INTRO
A 'single-file' SCP-based file copying script written using python. Aimed at users who need to copy files to their target via scp, but have some commands to run oin the target before copying can commence. As such, this script supports

1. pre-copy commands (config file)
2. Backup, copy, or revert files (paths configured in config file, mode chosen via cmd options)
3. post-copy command (config file)

### SETUP:
Python3 and pip installed:

#### MS: 
https://www.microsoft.com/store/productId/9PJPW5LDXLZ5?ocid=pdpshare

#### Linux
    sudo apt-get -y install python3 python3-pip
    
#### Libraries
    pip install paramiko cryptography
    
### USAGE:

1. Configure scp_copy.cfg
2. Connect to target (your normal method)
3. Run scp_copy.py (see below)

### CONFIG FILE:

Local parameters (supports multiple source paths)

    [local]
    path=   /some/path/usr/
            /optional/other/path/usr/
    backups=./backups/

Target (remote) parameters. (only one target path)

    [target]
    ip=192.168.1.1
    port=22
    username=usrnm
    password=pwd
    path=/usr/
    pre=ls -l
        mkdir someDir
    post=chmod 777 /usr/*

**NOTE:** The script copies *inside* the source paths *into* the target directory. For example:

1. Source path '/path/usr' conatains dir 'bin'
2. Target path '/target/path'
3. Result: 'target/path/bin'
    
### EXECUTION:
Execute with mode as parameter:

    python3 .\scp_copy.py [mode] [config]

b, c and r are the modes (Backup, Copy, Revert).

[config] is an optional path to the config file (defaults to ./scp_copy.cfg)

**NOTE:** Backup mode overwrites any previous backups, please be careful!
