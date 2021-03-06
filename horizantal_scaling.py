#!/usr/bin/env python3
import boto3
import time
import requests
import mechanicalsoup
import re
from botocore.exceptions import ClientError

class HScale:
    def __init__(self):
        self.load_gen_ami = "ami-2575315a"
        self.web_server_ami = "ami-886226f7"
        self.security_group = "project2-security-group"
        self.instance_type = "m3.medium"
        # ec2 resource
        self.ec2_client = boto3.resource('ec2', 'us-east-1')
        self.instances = []
        self.dns = []
        self.create_security_group()
        self.log_id = None
        self.current_rps = 0

    def create_security_group(self):
        ec2 = boto3.client('ec2')
        response = ec2.describe_vpcs()
        vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

        try:
            response = ec2.create_security_group(GroupName=self.security_group,
                                         Description='None', VpcId=vpc_id)
            self.security_group_id = response['GroupId']
            print('Security Group Created %s in vpc %s.' % (self.security_group_id, vpc_id))

            data = ec2.authorize_security_group_ingress(
            GroupId=self.security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                 'FromPort': 80,
                 'ToPort': 80,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp',
                 'FromPort': 22,
                 'ToPort': 22,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])
            print('Ingress Successfully Set %s' % data)
        except ClientError as e:
            print(e)

    def remove_security_group(self):
        ec2 = boto3.client('ec2')
        try:
            response = ec2.delete_security_group(GroupId=self.security_group_id)
            print('Security Group Deleted')
        except ClientError as e:
            print(e)


    def launch_load_gen_instance(self):
        """
            launch a load generator.
        """
        response = self.ec2_client.create_instances(ImageId=self.load_gen_ami, MinCount=1, MaxCount=1, 
                    InstanceType=self.instance_type, SecurityGroups=[self.security_group])
        self.instances.append(response[0])
        return response[0]

    def launch_web_server_instance(self):
        """
            launch web server instance.
        """
        response = self.ec2_client.create_instances(ImageId=self.web_server_ami, MinCount=1, MaxCount=1, 
                    InstanceType=self.instance_type, SecurityGroups=[self.security_group])
        self.instances.append(response[0])
        return response[0]

    def check_instance_ready(self):
        """
            check if given instances are running and ready.
        """
        # check for pending
        while True:
            all_done = True
            for inst in self.instances:
                if inst.state["Name"] == "pending":
                    print(inst.state)
                    all_done = False
            if all_done is True:
                break
            time.sleep(10)
            print("pending...")
            for inst in self.instances:
                inst.load()
        
        time.sleep(5)                
        
        # set the tag if everything is good or rise exception    
        for inst in self.instances:
            if inst.state["Name"] == "running":
                inst.create_tags(Tags=[{'Key': 'Project', 'Value': '2'}])
            else:
                raise NameError('Some Instance is not running!!!')
       
       
        # still initilalizing?
        all_ids = [inst.instance_id for inst in self.instances]
        response = self.ec2_client.meta.client.describe_instance_status(InstanceIds=all_ids)
        while True:
            all_done = True
            for i in range(len(all_ids)):
                status = response["InstanceStatuses"][i]["InstanceStatus"]["Status"]
                if status == "initializing" :
                    all_done = False
            if all_done is True:
                break
            time.sleep(10)
            response = self.ec2_client.meta.client.describe_instance_status(InstanceIds=all_ids)
            print("initilalizing...")
        
        time.sleep(5)
        
        # is ready?    
        for i in range(len(all_ids)):
            status = response["InstanceStatuses"][i]["InstanceStatus"]["Status"]
            if status != "ok":
                raise NameError('Some Instance status is not ok!')

        print("all ready!!!")

    def terminate_all_webservers(self):
        # ids of all web servers
        all_ids = [inst.instance_id for inst in self.instances[1:]]
        self.ec2_client.instances.filter(InstanceIds=all_ids).terminate()

    def login(self, public_dns_name, user, password):
        """
            login to load generator.
        """
        br = mechanicalsoup.StatefulBrowser()
        br.open('http://' + public_dns_name + "/password")
        contents = br.get_current_page()
        text = str(contents)
        text = text.replace("\n", " ")
        R = re.compile(".*You have entered your submission password.*")
        x = R.match(text)
        print(text)
        if  x != None:
            self.logined = True
            return True
        try:
            br.select_form(nr=0)
            br['passwd'] = password #'81Rd2rcbE0vIxMkdotO5K2'
            br['username'] = user #'amir.harati@gmail.com'
            req = br.submit_selected()
            print(req.text)
            self.logined = True
        except:
            raise NameError("Cant login!")

    def submit_web_dns(self, load_gen_dns, dns):
        """
            submit the dns of web server to load generator.
        """
        br = mechanicalsoup.StatefulBrowser()
        br.open('http://' + load_gen_dns + "/test/horizontal")
        contents = br.get_current_page()
        text = str(contents)
        text = text.replace("\n", " ")
        R = re.compile(".*\/log\?name=test\.(.*)\.log.*")
        x = R.match(text)
        print(text)
        if  x != None:
            self.log_id = x.group(1)
            return True
        try:
            while True:
                r = requests.get("http://" + dns + "/lookup/random")
                print(r)
                if str(r) == "<Response [200]>":
                    break
            br.select_form(nr=0)
            br['dns'] = dns
            req = br.submit_selected()
            print(req.text)
            text = req.text
            text = text.replace("\n", " ")
            x = R.match(text)
            if x != None:
                self.log_id = x.group(1)
            else:
                raise NameError("Something goes wrong with getting log_id")

            #self.logined = True
        except:
            raise NameError("Cant submit!")

    def add_web_dns(self, load_gen_dns, dns):
        """
            add new web server to load generator.
        """
        br = mechanicalsoup.StatefulBrowser()
        br.open('http://' + load_gen_dns + "/test/horizontal/add")
        contents = br.get_current_page()
        text = str(contents)
        text = text.replace("\n", " ")
        R = re.compile(".*\/log\?name=test\.(.*)\.log.*")
        x = R.match(text)
        print(text)
        if  x != None:
            self.log_id = x.group(1)
            return True
        try:
            while True:
                r = requests.get("http://" + dns + "/lookup/random")
                print(r)
                if str(r) == "<Response [200]>":
                    break

            br.select_form(nr=0)
            br['dns'] = dns
            req = br.submit_selected()
            print(req.text)
            #text = req.text
            #text = text.replace("\n", " ")
            #x = R.match(text)
            #if x != None:
            #    self.log_id = x.group(1)
            #else:
            #    raise NameError("Something goes wrong with getting log_id")

            #self.logined = True
        except:
            raise NameError("Cant submit!")


    def check_logs(self, load_gen_dns):
        """
            check the logs of load generator and return the  requests per second (RPS).
        """
        r = requests.get('http://' + load_gen_dns + "/log?name=test." + self.log_id + ".log")
        R = re.compile(".*\[Current\s+rps=(.*)\].*")
        text = str(r.content)
        text = text.replace("\n", " ")
        x = R.match(text)
        if x != None:
            self.current_rps = float(x.group(1))
        else:
            print("cant find rps!!!")

        print(r.content)

def read_userpass(userpass_file):
    lines = [line.strip() for line in open(userpass_file)]
    user, passwd = lines[0].split()
    return user, passwd

def main():
    user, passwd = read_userpass("userpass.txt")
    hs = HScale()
    load_gen_inst = hs.launch_load_gen_instance()
    web_inst = hs.launch_web_server_instance()
    hs.check_instance_ready()
    # 
    hs.login(load_gen_inst.public_dns_name, user, passwd)
    load_dns = load_gen_inst.public_dns_name
    web_dns = web_inst.public_dns_name
    #load_dns = "ec2-18-204-210-67.compute-1.amazonaws.com"
    #web_dns = "ec2-184-73-76-63.compute-1.amazonaws.com"
    hs.submit_web_dns(load_dns, web_dns)
    #hs.log_id =  "1529787302394"
    #hs.log_id = "1529791834222"
    hs.check_logs(load_dns)
    while hs.current_rps < 60:
        web_inst = hs.launch_web_server_instance()
        hs.check_instance_ready()
        web_dns = web_inst.public_dns_name
        #web_dns = "ec2-18-207-219-135.compute-1.amazonaws.com"
        hs.add_web_dns(load_dns, web_dns)
        if hs.current_rps >= 50:
            time.sleep(100)
        hs.check_logs(load_dns)

    # clean up
    hs.terminate_all_webservers()
    hs.remove_security_group()

if __name__ == "__main__":
    main()

