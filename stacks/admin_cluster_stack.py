from aws_cdk import (
    Stack,
    aws_eks as eks,
    aws_ec2 as ec2,
)
from aws_cdk.lambda_layer_kubectl import KubectlLayer
from constructs import Construct

class AdminClusterStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        admin_cluster = eks.Cluster(self, "admin-cluster",
            version=eks.KubernetesVersion.V1_24,
            kubectl_layer=KubectlLayer(self, "kubectl"),

            # One T3.small instance can contain up to 11 pods with AWS VPC CNI
            default_capacity_instance=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.SMALL),
            default_capacity=2,

            alb_controller=eks.AlbControllerOptions(
                version=eks.AlbControllerVersion.V2_4_1,
            ),
        )


