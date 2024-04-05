# Ecrit par Xavier B. et Dwayne H.
#Ce programme python récupère la liste des cannaux utilisés sur le reseau et
#propose un canal qui est le moins utilisé.

#Ensuite le script adhoc.sh est éxécuté.



import os
import netifaces
import subprocess
import sys


def get_available_channel(dico, network):
    for line in os.popen("sudo iwlist "+ network +" channel | grep -o '[0-9]*'"):
        #convert the line in integer
        channel = int(line)
        if channel not in dico.keys():
            dico[channel] = 0


def is_wireless(network):
    return len(subprocess.run(["sudo iwconfig " + network ],shell = True,capture_output=True).stdout)!=0


def get_nb_channel(dico_channel,network):


    grep = "Channel:"
    grep2 = "[0-9]*"
  
    get_available_channel(dico_channel, network)



    output = os.popen("sudo iwlist " +network+ " scanning | grep "+ grep + " | grep -o "+ grep2 )
    
    for ligne in output.readlines():
        dico_channel[int(ligne)]+=1

    output.close()

def get_network_itf():

    return netifaces.interfaces()


def tri(dico):
    return sorted(dico.items(),key=lambda t :t[1]+t[0])[:3]
    
def main():
    dico ={}
    network_list = get_network_itf()
    for itf in network_list :
            if is_wireless(itf):
                get_nb_channel(dico,itf)
    res=tri(dico)[1][0]
    
    print("Canal le moins utilisé : "+ str(res))
    
    p = subprocess.Popen(["./adhoc.sh"], shell=True ,stdout=subprocess.PIPE)
    p.wait()
        
main()
