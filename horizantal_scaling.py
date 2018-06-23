#!/usr/bin/env python3
import boto3
import time
import requests
import mechanicalsoup

class HScale:
    def __init__(self):
        self.load_gen_ami = "ami-2575315a"
        self.web_server_ami = "ami-886226f7"
        self.security_group = "launch-wizard-1"
        self.instance_type = "m3.medium"
        # ec2 resource
        self.ec2_client = boto3.resource('ec2', 'us-east-1')
        self.instances = []
        self.dns = []

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

    def login(self, user, password):
        """
            login to load generator.
        """
        pass

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
    hs = HScale()
    load_gen_inst = hs.launch_load_gen_instance()
    web_inst = hs.launch_web_server_instance()
    hs.check_instance_ready()

if __name__ == "__main__":
    main()

