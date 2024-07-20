import os
import sys
import re
import shutil
import json

from configparser import ConfigParser
from scp import SCPClient, SCPException
import paramiko

DEBUG = False
# ================================= #
# scp_copy.py 
#
# Author: JozeDash
#
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
#
# A script that uses scp to backup, copy, 
# and revert files on an ssh target device
# ================================= #

# ================================= #
# 'Global' variables
# ================================= #

DEFAULT_CONF = "./copier.cfg"

# Argv indeces
ARG_INDEX_MODE = 1
ARG_INDEX_CFG = 2

# Modes
MODE_BACKUP = "b"
MODE_COPY = "c"
MODE_REVERT = "r"

# Configuration keys
SECTION_LOCAL = "local"
SECTION_TARGET = "target"

CFG_LOCAL_PATH = "path"
CFG_BACKUPS_PATH = "backups"

CFG_IP = "ip"
CFG_PORT = "port"
CFG_USERNAME = "username"
CFG_PWD = "password"
CFG_TARGET_PATH = "path"
CFG_TARGET_PRE = "pre"
CFG_TARGET_POST = "post"

# ================================= #
# Utility and helper functions
# ================================= #

# readCfgFile
# Parse the config file on the provided path
# param configFilePath: the path to the config file
# return a config dictionary
def readCfgFile(configFilePath):

    if not os.path.exists(configFilePath):
        print("Config file at: " + configFilePath + " does not exist!")
        sys.exit(1)
    
    configFile = ConfigParser() 
    configFile.read(configFilePath)
    config = dict()

    config[SECTION_LOCAL] = dict()
    config[SECTION_TARGET] = dict()

    # Support multiple input directories split over multiple lines
    config[SECTION_LOCAL][CFG_LOCAL_PATH] = configFile.get(SECTION_LOCAL, CFG_LOCAL_PATH).splitlines()
    
    config[SECTION_LOCAL][CFG_BACKUPS_PATH] = configFile.get(SECTION_LOCAL, CFG_BACKUPS_PATH)

    config[SECTION_TARGET][CFG_IP] = configFile.get(SECTION_TARGET, CFG_IP)
    config[SECTION_TARGET][CFG_PORT] = configFile.get(SECTION_TARGET, CFG_PORT)
    config[SECTION_TARGET][CFG_USERNAME] = configFile.get(SECTION_TARGET, CFG_USERNAME)
    config[SECTION_TARGET][CFG_PWD] = configFile.get(SECTION_TARGET, CFG_PWD)
    config[SECTION_TARGET][CFG_TARGET_PATH] = configFile.get(SECTION_TARGET, CFG_TARGET_PATH)

    # Support multiple commands over several lines, here
    config[SECTION_TARGET][CFG_TARGET_PRE] = configFile.get(SECTION_TARGET, CFG_TARGET_PRE).splitlines()
    config[SECTION_TARGET][CFG_TARGET_POST] = configFile.get(SECTION_TARGET, CFG_TARGET_POST).splitlines()

    if DEBUG:
        prettyPrint = json.dumps(config, indent=4)
        print(prettyPrint)

    return config

# handleStdOut
# Decode and print stdout from target
# param stdout: the stdout from the target command
def handleStdout(stdout):
    prettyString = stdout.read().decode('utf-8')
    if len(prettyString) > 0:
        print("output:")
        print(prettyString)

# handStderr
# Decode and print stderr (if any) from target
# param stderr: the stderr stream from target
# return: false if err output, else true
def handleStderr(stderr):
    prettyString = stderr.read().decode('utf-8')
    if len(prettyString) > 0:
        print("\t error: ", prettyString)
        return False
    else:
        return True 

# runTargetCommand
# Run the provided command on the ssh client
# param ssh: the ssh instance
# param command: the command to execute
def runTargetCommand(ssh, command):
    print("Run target command: ", command)
    (stdin, stdout, stderr) = ssh.exec_command(command)
    handleStdout(stdout)
    if not handleStderr(stderr):
        print("Exiting!")
        sys.exit(1)

# scpLocal2Target
# Copy all files in the provided directory to the target directory
# param scp: the scp instance
# param sourcePath: the source directory
# param targetPath: the target directory
def scpLocal2Target(scp, sourcePath, targetPath):
    for source in os.listdir(sourcePath):
        # scp does not support Windows paths, flip the slashes here
        genericPath = re.sub(r'\\', '/', source) 
        sourceFile = os.path.join(sourcePath, genericPath)
        print("Copy file from source " + sourceFile + " to target directory " + targetPath)
        
        try:
            scp.put(sourceFile, recursive=True, remote_path=targetPath)
            print("\tSuccess!")
        except SCPException:
            print("\tCopy failed, bailing!")
            sys.exit(1)

# printHelp
# print the help
def printHelp():
    print("Usage:")
    print("python3 ./copier.py [mode] [config]")
    print("[mode]\t\tone of: b, c, r (Backup, Copy, Revert)")
    print("[config]\toptional path to a config file (allows for multiple targets/operations)")


# ================================= #
# Main logic
# ================================= #

# Check inputs ==================== #
if len(sys.argv) > ARG_INDEX_MODE:
    mode = sys.argv[ARG_INDEX_MODE]
    if not (mode == MODE_BACKUP \
            or mode == MODE_COPY \
            or mode == MODE_REVERT):
        printHelp()
        print("Exiting!")
        sys.exit(1)
else:
    printHelp()
    sys.exit(1)

configFilePath = DEFAULT_CONF

if len(sys.argv) > ARG_INDEX_CFG:
    # config
    configFilePath = sys.argv[ARG_INDEX_CFG]

config = readCfgFile(configFilePath)

# Setup SSH ======================= #
ssh = paramiko.SSHClient()
ssh.set_missing_host_CFG_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect(config[SECTION_TARGET][CFG_IP], \
                port=config[SECTION_TARGET][CFG_PORT], \
                username=config[SECTION_TARGET][CFG_USERNAME], \
                password=config[SECTION_TARGET][CFG_PWD], \
                timeout=3)
except:
    print("Failed to connect to host '" \
        + config[SECTION_TARGET][CFG_USERNAME] \
        + "@" \
        + config[SECTION_TARGET][CFG_IP] \
        + "' with password: '" \
        + config[SECTION_TARGET][CFG_PWD] \
        + "'")
    print("Please check your connection and config is ok")
    sys.exit(1)

# Create scp
scp = SCPClient(ssh.get_transport())

# Backup ========================== #
if mode == MODE_BACKUP:
    # Search target for each file in the source directory(ies) and try to back it up
    if os.path.exists(config[SECTION_LOCAL][CFG_BACKUPS_PATH]):
        shutil.rmtree(config[SECTION_LOCAL][CFG_BACKUPS_PATH])

    os.makedirs(config[SECTION_LOCAL][CFG_BACKUPS_PATH], \
                exist_ok=True)

    successCount = 0
    skipCount = 0
    for directory in config[SECTION_LOCAL][CFG_LOCAL_PATH]:
        for root, dirs, files in os.walk(directory):
            for file in files:
                relativePath = os.path.relpath(os.path.join(root, file), start=directory)
                genericPath = re.sub(r'\\', '/', relativePath) # scp library does not support Windows paths

                targetFile = os.path.join(config[SECTION_TARGET][CFG_TARGET_PATH], \
                                            genericPath)
                backupPath = os.path.join(config[SECTION_LOCAL][CFG_BACKUPS_PATH], \
                                          os.path.split(genericPath)[0])
                print("Back up target file " + targetFile + " to local path " + backupPath)
                
                os.makedirs(backupPath, exist_ok=True)
                
                try:
                    scp.get(targetFile, backupPath)
                    print("\tSuccess!")
                    successCount += 1
                except SCPException:
                    print("\tFile not already on target, ignoring")
                    skipCount += 1

    print("Backed up " \
          + str(successCount) \
          + " file(s), skipped " \
          + str(skipCount) 
          + " file(s).")

# Copy or revert=================== #
elif mode == MODE_COPY or mode == MODE_REVERT:
    
    # Run target pre scp commands ======== #
    for command in config[SECTION_TARGET][CFG_TARGET_PRE]:
        runTargetCommand(ssh, command)

    # Copy ============================ #
    if mode == MODE_COPY:
        print("Copying local files to target")
        for localPath in config[SECTION_LOCAL][CFG_LOCAL_PATH]:
            scpLocal2Target(scp, localPath, config[SECTION_TARGET][CFG_TARGET_PATH])

    # Revert ========================== #
    elif mode == MODE_REVERT:
        print("Copying backed up files to target")
        scpLocal2Target(scp, config[SECTION_LOCAL][CFG_BACKUPS_PATH], config[SECTION_TARGET][CFG_TARGET_PATH])
    
    # Run target post scp commands ==== #
    for command in config[SECTION_TARGET][CFG_TARGET_POST]:
        runTargetCommand(ssh, command)

# close scp
scp.close   
