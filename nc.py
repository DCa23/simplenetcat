#!/home/uadm/PycharmProjects/NetCatTalegero/venv/bin/python
# -*- coding:utf8 -*-

import socket
import subprocess
import argparse
import time
import threading
import os
import datetime

def logger(msg,mode="info"):
    strdate = datetime.date.today().strftime("%H:%M,%S %d/%m/%Y")
    msg = "[" + mode + "][" + strdate + "]" + msg
    print(msg)

def server_loop(connection_info):
    sk = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sk.bind(connection_info)
    sk.listen(6)

    while True:
        client,addr = sk.accept()
        msg = "[+] Accepted connection from %s:%s" % (addr[0], addr[1])
        logger(msg)

        client_handler = threading.Thread(target=handle_client,args=(client,))
        client_handler.start()


def serve_shell(sk):
    sk.send(b"ACKC")
    while True:
        remote_input = sk.recv(1024)
        remote_input = remote_input.decode("utf8")
        if remote_input == "exit":
            break
        else:
            output_cmd = execCmd(remote_input)
            sk.send(output_cmd.encode("utf8"))




def handle_client(sk):
    mode = sk.recv(1024)
    if mode == b"command":
        serve_shell(sk)
    elif mode == b"execute":
        execute_remotecmd(sk)
    elif mode == b"upload":
        recive_file(sk)
    sk.close()
    return

def connect_shell(conn):
    conn.send(b"command")
    server_msg = conn.recv(1024)
    if server_msg == b"ACKC":
        while True:
            user_input = input("shell>").strip("\n")
            if user_input == "exit":
                conn.send(user_input.encode("utf8"))
                break
            else:
                conn.send(user_input.encode("utf8"))
                server_msg = conn.recv(2048)
                print(server_msg.decode("utf8"))
    else:
        print("Error en la conexion con el servidor")

#Execute command
def execute_remotecmd(conn):
    try:
        conn.send(b"ACKE")
        command = conn.recv(1024).decode("utf8")
        cmd_result = execCmd(command)
        conn.send(cmd_result.encode("utf8"))
    except Exception as e:
        logger("Error handling connection: " + str(e))
    pass

#Send command
def execute_command(conn,command):
    conn.send(b"execute")
    server_msg = conn.recv(1024)
    if server_msg == b"ACKE":
        conn.send(command.encode("utf8"))
        server_msg = conn.recv(4084)
        print(server_msg.decode("utf8"))


def upload_file(conn,uploadfile):
    conn.send(b"upload")
    server_msg = conn.recv(1024)
    if server_msg == b"ACKU":
        conn.send(uploadfile.encode("utf8"))
        fh = open(uploadfile,"rb")
        txt = fh.read()
        conn.send(txt)
        #MD5 CHECK
        server_msg = conn.recv(1024)
        if server_msg == b"ACKU":
            print("Fileuploaded Correctly")
        else:
            print("Error uploading file")



def recive_file(conn):
    try:
        conn.send(b"ACKU")
        filename = conn.recv(1024).decode("utf8")
        num = 0
        newfilepath = filename.split("/")[-1]
        while os.path.exists(newfilepath):
            elements = newfilepath.split(".")
            newfilepath = elements[0] + str(num) + "." + elements[1]
            num += 1
        uploaded_file = conn.recv(8192)
        fh = open(newfilepath,"wb")
        fh.write(uploaded_file)
        logger("Uploaded file " + newfilepath )
        conn.send(b"ACKU")
    except:
        conn.send(b"ACKERR")

def execCmd(cmdtxt):
    result = subprocess.Popen([cmdtxt],stdout = subprocess.PIPE, shell = True,stderr = subprocess.STDOUT,universal_newlines=True)
    (output,err) = result.communicate()
    if not output:
        output = "\n"
    return output


def readArguments():
    parser = argparse.ArgumentParser(description="NetCat Talegero",usage='%(prog)s -t target_host -p port [options]')
    parser.add_argument("-t", "--target",required=True, help="Host")
    parser.add_argument("-p", "--port", required=True,help="Puerto",type=int)
    parser.add_argument("-l","--listen", action="store_true",help="Listen on -t [host] -p [port] for incoming connections")
    parser.add_argument("-e","--execute", help="Execute the given file file upon recieving a connection")
    parser.add_argument("-c","--command", action="store_true", help="Initialize a command shield")
    parser.add_argument("-u","--upload", help="Upon recieving connection a file and write to [destination]")
    args = vars(parser.parse_args())
    if args["command"] and (args["execute"] or args["upload"]):
        parser.print_help()
        exit(0)
    elif args["execute"] and (args["command"] or args["upload"]):
        parser.print_help()
        exit(0)
    elif args["upload"] and (args["command"] or args["execute"] ):
        parser.print_help()
        exit(0)
    return args


def main():
    args = readArguments()
    if args["listen"]:
        server_loop((args["target"],args["port"]))
    else:
        try:
            conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            conn.connect((args["target"],args["port"]))
        except Exception as e:
            print("Unable no connect to the target:")
            print(str(e))
        if args["command"]:
            connect_shell(conn)
        elif args["execute"]:
            execute_command(conn,args["execute"])
        elif args["upload"]:
            upload_file(conn,args["upload"])
        conn.close()

if __name__ == "__main__":
    main()