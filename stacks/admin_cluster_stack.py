from aws_cdk import (
    Stack,
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_iam as iam,
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

        ebs_csi_role = iam.Role(
            self,
            "ebs-csi-role",
            assumed_by=iam.FederatedPrincipal(
                federated=admin_cluster.open_id_connect_provider.open_id_connect_provider_arn,
                assume_role_action="sts:AssumeRoleWithWebIdentity",
                conditions={
                    "StringEquals": {
                        "$oidc_provider:aud": "sts.amazonaws.com",
                        "$oidc_provider:sub": "system:serviceaccount:kube-system:ebs-csi-controller-sa",
                    },
                },
            ),
            inline_policies={
                "default": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ec2:CreateSnapshot",
                                "ec2:AttachVolume",
                                "ec2:DetachVolume",
                                "ec2:ModifyVolume",
                                "ec2:DescribeAvailabilityZones",
                                "ec2:DescribeInstances",
                                "ec2:DescribeSnapshots",
                                "ec2:DescribeTags",
                                "ec2:DescribeVolumes",
                                "ec2:DescribeVolumesModifications",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ec2:CreateTags",
                            ],
                            resources=[
                                "arn:aws:ec2:*:*:volume/*",
                                "arn:aws:ec2:*:*:snapshot/*",
                            ],
                            conditions={
                                "StringEquals": {
                                    "ec2:CreationAction": [
                                        "CreateVolume",
                                        "CreateSnapshot",
                                    ],
                                },
                            },
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ec2:DeleteTags",
                            ],
                            resources=[
                                "arn:aws:ec2:*:*:volume/*",
                                "arn:aws:ec2:*:*:snapshot/*",
                            ],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ec2:CreateVolume",
                            ],
                            resources=["*"],
                            conditions={
                                "StringLike": {
                                    "aws:RequestTag/ebs.csi.aws.com/cluster": "true",
                                },
                            },
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ec2:CreateVolume",
                            ],
                            resources=["*"],
                            conditions={
                                "StringLike": {
                                    "aws:RequestTag/CSIVolumeName": "*",
                                },
                            },
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ec2:DeleteVolume",
                            ],
                            resources=["*"],
                            conditions={
                                "StringLike": {
                                    "ec2:ResourceTag/ebs.csi.aws.com/cluster": "true",
                                },
                            },
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ec2:DeleteVolume",
                            ],
                            resources=["*"],
                            conditions={
                                "StringLike": {
                                    "ec2:ResourceTag/CSIVolumeName": "*",
                                },
                            },
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ec2:DeleteVolume",
                            ],
                            resources=["*"],
                            conditions={
                                "StringLike": {
                                    "ec2:ResourceTag/kubernetes.io/created-for/pvc/name": "*",
                                },
                            },
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ec2:DeleteSnapshot",
                            ],
                            resources=["*"],
                            conditions={
                                "StringLike": {
                                    "ec2:ResourceTag/CSIVolumeSnapshotName": "*",
                                },
                            },
                        ),
                    ],
                ),
            },
        )

        ebs_csi_addon = eks.CfnAddon(self, "ebs-csi-addon",
            addon_name="aws-ebs-csi-driver",
            cluster_name=admin_cluster.cluster_name,

            # the properties below are optional
            preserve_on_delete=False,
            service_account_role_arn=ebs_csi_role.role_arn,
        )

