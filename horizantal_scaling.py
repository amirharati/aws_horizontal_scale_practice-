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
        self.security_group = "project2-sec-group"
        self.instance_type = "m3.medium"
        # ec2 resource
        self.ec2_client = boto3.resource('ec2', 'us-east-1')
        self.instances = []
        self.dns = []
        self.create_security_group()

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

    def submit_web_dns(self, dns):
        """
            submit the dns of web server to load generator.
        """
        pass

    def add_web_dns(self, dns):
        """
            add new web server to load generator.
        """
        pass

    def check_logs(self):
        """
            check the logs of load generator and return the  requests per second (RPS).
        """
        pass


def main():
    #hs = HScale()
    #load_gen_inst = hs.launch_load_gen_instance()
    #web_inst = hs.launch_web_server_instance()
    #hs.check_instance_ready()
    # 
    hs.login(load_gen_inst.public_dns_name, 'amir.harati@gmail.com', '81Rd2rcbE0vIxMkdotO5K2')

if __name__ == "__main__":
    main()

