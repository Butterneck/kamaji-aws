from aws_cdk import (
    CfnJson,
    CustomResource,
    Stack,
    Token,
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    custom_resources as cr,
    aws_ssm as ssm,
)
from aws_cdk.lambda_layer_kubectl_v24 import KubectlV24Layer
from constructs import Construct

class AdminClusterStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        admin_cluster = eks.Cluster(self, "admin-cluster",
            version=eks.KubernetesVersion.V1_24,
            kubectl_layer=KubectlV24Layer(self, "kubectlV24"),

            # One T3.small instance can contain up to 11 pods with AWS VPC CNI
            default_capacity_instance=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.SMALL),
            default_capacity=3,
        )

        ssm.StringParameter(self, "admin-cluster-name-param",
            parameter_name="/eks/admin-cluster/name",
            string_value=admin_cluster.cluster_name,
        )

        ssm.StringParameter(self, "admin-cluster-kubectl-role-arn",
            parameter_name="/eks/admin-cluster/kubectl/role/arn",
            string_value=admin_cluster.kubectl_role.role_arn,
        )

        ssm.StringParameter(self, "admin-cluster-vpc-id",
            parameter_name="/eks/admin-cluster/vpc/id",
            string_value=admin_cluster.vpc.vpc_id,
        )

        on_event = lambda_.Function(
            self,
            "oidc-provider-id-fn",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.on_event",
            code=lambda_.Code.from_asset("get_oidc_provider_id"),
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        my_provider = cr.Provider(self, "oidc-provider-id-provider",
            on_event_handler=on_event,
            log_retention=logs.RetentionDays.ONE_DAY,
        )

        oidc_provider_id_cr = CustomResource(
            self, 
            "oidc-provider-id-cr",
            service_token=my_provider.service_token,
            properties={
                "oidcProviderArn": admin_cluster.open_id_connect_provider.open_id_connect_provider_arn,
            },
        )

        oidc_provider_id = Token.as_string(oidc_provider_id_cr.get_att('Id'))

        oidc_tr_conditions = CfnJson(self, "oidc-condition-json",
            value={
                f"{Token.as_string(oidc_provider_id)}:aud": "sts.amazonaws.com",
                f"{Token.as_string(oidc_provider_id)}:sub": "system:serviceaccount:kube-system:ebs-csi-controller-sa",
            },
        )

        ebs_csi_role = iam.Role(
            self,
            "ebs-csi-role",
            assumed_by=iam.FederatedPrincipal(
                federated=admin_cluster.open_id_connect_provider.open_id_connect_provider_arn,
                assume_role_action="sts:AssumeRoleWithWebIdentity",
                conditions={
                    "StringEquals": oidc_tr_conditions,
                },
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEBSCSIDriverPolicy"),
            ],
        )

        ebs_csi_addon = eks.CfnAddon(self, "ebs-csi-addon",
            addon_name="aws-ebs-csi-driver",
            cluster_name=admin_cluster.cluster_name,

            # the properties below are optional
            preserve_on_delete=False,
            service_account_role_arn=ebs_csi_role.role_arn,
        )

