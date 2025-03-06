# AWS CLI Guide for Setting Up EKS Cluster and Deploying Applications

This guide provides concise steps for a DevOps engineer to set up an EKS (Elastic Kubernetes Service) cluster, manage VPC and subnets, create a node group, and deploy applications using Kubernetes via AWS CLI.

### 1. **Check for Existing VPC or Create a New VPC**

#### Check for Existing VPC:
```bash
aws ec2 describe-vpcs --query "Vpcs[*].VpcId"
```

#### Create a New VPC:
```bash
aws ec2 create-vpc --cidr-block <CIDR_BLOCK> --query "Vpc.VpcId" --output text
```
- Replace `<CIDR_BLOCK>` with your desired CIDR block (e.g., `10.0.0.0/16`).

### 2. **Check for Existing Subnet or Create a New Subnet**

#### Check for Existing Subnets:
```bash
aws ec2 describe-subnets --query "Subnets[*].SubnetId"
```

#### Create a New Subnet:
```bash
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block <CIDR_BLOCK> --availability-zone <AZ> --query "Subnet.SubnetId" --output text
```
- Replace `<VPC_ID>`, `<CIDR_BLOCK>`, and `<AZ>` with your VPC ID, CIDR block (e.g., `10.0.1.0/24`), and Availability Zone (e.g., `us-west-2a`).

### 3. **Create EKS Cluster**

#### Create an EKS Cluster:
```bash
aws eks create-cluster --name <CLUSTER_NAME> --role-arn <EKS_ROLE_ARN> --resources-vpc-config subnetIds=<SUBNET_IDS>,securityGroupIds=<SG_IDS>
```
- Replace `<CLUSTER_NAME>`, `<EKS_ROLE_ARN>`, `<SUBNET_IDS>`, and `<SG_IDS>` with your desired cluster name, IAM role ARN, subnet IDs, and security group IDs.

### 4. **Check the Status of the EKS Cluster**

#### Check Cluster Status:
```bash
aws eks describe-cluster --name <CLUSTER_NAME> --query "cluster.status"
```

### 5. **Create Node Group for EKS Cluster**

#### Create Node Group:
```bash
aws eks create-nodegroup --cluster-name <CLUSTER_NAME> --nodegroup-name <NODE_GROUP_NAME> --subnet-ids <SUBNET_IDS> --instance-types <INSTANCE_TYPE> --scaling-config minSize=<MIN_SIZE>,maxSize=<MAX_SIZE>,desiredSize=<DESIRED_SIZE>
```
- Replace `<CLUSTER_NAME>`, `<NODE_GROUP_NAME>`, `<SUBNET_IDS>`, `<INSTANCE_TYPE>`, `<MIN_SIZE>`, `<MAX_SIZE>`, and `<DESIRED_SIZE>` with appropriate values.

### 6. **Set the Kube Context to the EKS Cluster**

#### Update Kubeconfig:
```bash
aws eks update-kubeconfig --name <CLUSTER_NAME> --region <REGION>
```
- Replace `<CLUSTER_NAME>` and `<REGION>` with your cluster name and AWS region.

### 7. **Deploy Applications Using Kubernetes on EKS**

#### Apply Kubernetes Manifests (e.g., for deploying a pod):
```bash
kubectl apply -f <PATH_TO_K8S_MANIFEST>.yaml
```
- Replace `<PATH_TO_K8S_MANIFEST>` with the path to your Kubernetes YAML file.

#### Example to Deploy a Simple Nginx Pod:
```bash
kubectl run nginx --image=nginx --port=80
```

### 8. **Check the Status of Deployments, Services, Pods, and ReplicaSets**

#### Check Pod Status:
```bash
kubectl get pods
```

#### Check Deployment Status:
```bash
kubectl get deployments
```

#### Check Service Status:
```bash
kubectl get svc
```

#### Check ReplicaSet Status:
```bash
kubectl get replicasets
```

#### Get Detailed Information for a Specific Resource:
```bash
kubectl describe <RESOURCE_TYPE> <RESOURCE_NAME>
```
- Replace `<RESOURCE_TYPE>` with `pods`, `deployments`, `svc`, etc., and `<RESOURCE_NAME>` with the name of the resource.

---

### Conclusion

This guide provides a streamlined approach to managing AWS resources using AWS CLI for setting up an EKS cluster, configuring Kubernetes, and deploying applications. Each step is designed to simplify the process for a DevOps engineer while ensuring scalability and flexibility.