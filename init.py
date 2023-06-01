import subprocess
import os
import sys
import platform

def restart_service(service_name):
    if platform.system() == "Windows":
        subprocess.run(["net", "stop", service_name], check=True)
        subprocess.run(["net", "start", service_name], check=True)
    elif platform.system() == "Linux":
        subprocess.run(["systemctl", "restart", service_name], check=True)

def agregador(discos_ignorados=[]):
    if platform.system() == "Windows":
        discos = subprocess.check_output("wmic diskdrive get name | findstr /r '^PHYSICALDRIVE[0-9]'", shell=True).decode().strip()
        discos = discos.replace("PHYSICALDRIVE", "")
    elif platform.system() == "Linux":
        discos = subprocess.check_output("ls /dev/sd* | awk -F'/' '{print $3}' | grep sd | sed 's/[0-9]*//g' | uniq", shell=True).decode().strip()

    discos = [d for d in discos.split() if d not in discos_ignorados]

    qtd_discos = len(discos)

    if qtd_discos <= 0:
        print("-> Não há discos a serem verificados")
        sys.exit()

    if qtd_discos > 1:
        print("Temos esses discos:")
        print(discos)
        resposta = input("Digite o disco que deseja verificar: ")
        if platform.system() == "Windows":
            resposta = "PhysicalDrive" + resposta
        valida_resposta = subprocess.check_output(f"echo '{discos}' | grep -w '{resposta}'", shell=True).decode().strip()
        if not valida_resposta:
            print("-> Não foi listado esse disco")
            sys.exit()
    else:
        resposta = discos[0]

    if platform.system() == "Windows":
        serial = subprocess.check_output(f"wmic diskdrive where \"Index={resposta}\" get SerialNumber /format:list | findstr SerialNumber", shell=True).decode().strip()
        serial = serial.split("=")[1]
        modelo = subprocess.check_output(f"wmic diskdrive where \"Index={resposta}\" get Model /format:list | findstr Model", shell=True).decode().strip()
        modelo = modelo.split("=")[1]
    elif platform.system() == "Linux":
        serial = subprocess.check_output(f"smartctl -i /dev/{resposta} | grep 'Serial' | awk -F':' '{{print $2}}' | tr -d '[:space:]'", shell=True).decode().strip()
        modelo = subprocess.check_output(f"smartctl -i /dev/{resposta} | grep 'Device Model' | awk -F':' '{{print $2}}' | tr -d '[:space:]'", shell=True).decode().strip()

    data = subprocess.check_output("date +%Y-%m-%d", shell=True).decode().strip()

    log_file = f"{os.getcwd()}/{data}-good"
    if os.path.exists(log_file) or os.path.exists(f"{os.getcwd()}/{data}-bad"):
        verificador_log = subprocess.check_output(f"cat {log_file}* | grep -w '{serial}' 2>/dev/null", shell=True).decode().strip()
        if verificador_log:
            print("-> Ignorando verificação, já possui esse serial no LOG!")
            sys.exit()

agregador()
print(f"Verificando o {resposta}")

if len(sys.argv) > 1 and sys.argv[1] == "f":
    print("Removedor raid é partição ATIVO!")
    x = 1
    a = 1
    while True:
        if platform.system() == "Windows":
            teste_mount = subprocess.check_output(f"wmic partition get name | findstr {resposta}", shell=True).decode().strip()
            teste = subprocess.check_output(f"wmic diskdrive where \"Model LIKE '{resposta}%'\" get Index /format:list | findstr Index", shell=True).decode().strip()
            teste = teste.split("=")[1]
        elif platform.system() == "Linux":
            teste_mount = subprocess.check_output(f"df | awk -F' ' '{{print $1}}' | grep '{resposta}'", shell=True).decode().strip()
            teste = subprocess.check_output(f"find /dev/ -maxdepth 1 -iname 'md*' | grep -wv '/dev/md' | sed -n '{x}p' 2>/dev/null", shell=True).decode().strip()

        if teste:
            if platform.system() == "Windows":
                subprocess.run(["diskpart", "/s", "clean.txt"], check=True)  # Assumes clean.txt contains the commands to clean the disk
            elif platform.system() == "Linux":
                subprocess.run(["sudo", "mdadm", "--stop", teste], check=True)
                subprocess.run(["sudo", "mdadm", "--remove", teste], check=True)
            x += 1
        else:
            if platform.system() == "Windows":
                teste2 = subprocess.check_output(f"wmic partition where \"Model LIKE '{resposta}%'\" get DeviceID /format:list | findstr DeviceID", shell=True).decode().strip()
                teste2 = teste2.split("=")[1]
            elif platform.system() == "Linux":
                teste2 = subprocess.check_output(f"find /dev/ -maxdepth 1 -iname '{resposta}' | grep -wv '/dev/{resposta}' | sed -n '{a}p' 2>/dev/null", shell=True).decode().strip()

            if teste2 or teste_mount:
                if platform.system() == "Windows":
                    subprocess.run(["diskpart", "/s", "clean.txt"], check=True)  # Assumes clean.txt contains the commands to clean the disk
                elif platform.system() == "Linux":
                    subprocess.run(["sudo", "umount", f"/dev/{resposta}*", "2>/dev/null"], check=True)
                    subprocess.run(["sudo", "/sbin/parted", f"/dev/{resposta}", "rm", "1", "--script", "2>/dev/null"], check=True)
                a += 1
            else:
                break

agregador()

def verificador():
    if platform.system() == "Windows":
        saida_comando = subprocess.run("echo %ERRORLEVEL%", shell=True).returncode
    elif platform.system() == "Linux":
        saida_comando = subprocess.call("echo $?", shell=True)
    if saida_comando == 0:
        print("Sucesso")
    else:
        print("Falha")
        sys.exit()
        subprocess.run(["umount", particao])
        subprocess.run(["/sbin/parted", f"/dev/{resposta}", "rm", "1", "--script"])
        subprocess.run(["rm", "-r", "/mnt/blade"])

print("-> Etapa 1 - Testando criar rótulo de disco: ", end="")
if platform.system() == "Windows":
    subprocess.run(["diskpart", "/s", "create_label.txt"], check=True)  # Assumes create_label.txt contains the commands to create the disk label
elif platform.system() == "Linux":
    subprocess.run(["/sbin/parted", f"/dev/{resposta}", "mklabel", "gpt", "--script"], check=True)
verificador()

print("-> Etapa 2 - Testando criar partição: ", end="")
if platform.system() == "Windows":
    subprocess.run(["diskpart", "/s", "create_partition.txt"], check=True)  # Assumes create_partition.txt contains the commands to create the partition
elif platform.system() == "Linux":
    subprocess.run(["/sbin/parted", f"/dev/{resposta}", "mkpart", "primary", "0%", "100%", "--script"], check=True)
verificador()

print("-> Etapa 3 - Testando formatação da partição: ", end="")
particao = f"/dev/{resposta}1"
if platform.system() == "Windows":
    subprocess.run(["format", particao, "/FS:NTFS", "/Q", "/Y"], check=True)
elif platform.system() == "Linux":
    subprocess.run(["mkfs.ext4", "-q", "-F", particao, "1>/dev/null"], check=True)
verificador()

subprocess.run(["mkdir", "/mnt/blade"])
print("-> Etapa 4 - Testando montagem da partição: ", end="")
if platform.system() == "Windows":
    subprocess.run(["mountvol", "/s", particao, "/d"], check=True)
    subprocess.run(["mountvol", "/s", particao, "/m", "/mnt/blade"], check=True)
elif platform.system() == "Linux":
    subprocess.run(["mount", particao, "/mnt/blade"], check=True)
verificador()

print("-> Etapa 5 - Verificando status da partição montada: ", end="")
mountpoint = subprocess.check_output("df -h | grep -w '{particao}'", shell=True).decode().strip()
if not mountpoint:
    print("Falha")
    sys.exit()
else:
    print("Sucesso")

subprocess.run(["sleep", "4"])
if platform.system() == "Windows":
    subprocess.run(["mountvol", "/s", particao, "/d"], check=True)
elif platform.system() == "Linux":
    subprocess.run(["umount", particao])
subprocess.run(["/sbin/parted", f"/dev/{resposta}", "rm", "1", "--script"])
subprocess.run(["rm", "-r", "/mnt/blade"])
subprocess.run(["sleep", "2"])

print("-> Etapa 6 - Verificando smartctl status: ", end="")
if platform.system() == "Windows":
    test = subprocess.check_output(f"smartctl.exe -A /dev/{resposta} | findstr -E \"Reallocated_Sector_Ct Offline_Uncorrectable Reported_Uncorrect End-to-End_Error\" | awk {{print $NF}} | awk {{sum+=$1}} END {{print sum}}", shell=True).decode().strip()
elif platform.system() == "Linux":
    test = subprocess.check_output(f"smartctl -A /dev/{resposta} | grep -P 'Reallocated_Sector_Ct|Offline_Uncorrectable|Reported_Uncorrect|End-to-End_Error' | awk '{{print $NF}}' | awk '{{sum+=$1}} END {{print sum}}'", shell=True).decode().strip()
if int(test) != 0:
    print("Falha")
else:
    print("Sucesso")

print("-> Etapa 7 - Verificando hddtemp status: ", end="")
if platform.system() == "Windows":
    hddtemp = subprocess.check_output(f"hddtemp.exe /dev/{resposta}", shell=True).decode().strip()
elif platform.system() == "Linux":
    hddtemp = subprocess.check_output(f"hddtemp /dev/{resposta}", shell=True).decode().strip()
if not hddtemp or hddtemp == "/dev/sg0: open failed: No such file or directory":
    print("Falha")
else:
    print("Sucesso")

print("-> Etapa 8 - Gravando informações no log: ", end="")
if platform.system() == "Windows":
    subprocess.run([f"echo {serial} - {modelo} >> {log_file}-good.txt"], shell=True)
elif platform.system() == "Linux":
    subprocess.run([f"echo {serial} - {modelo} >> {log_file}-good.txt"], shell=True)
print("Sucesso")
