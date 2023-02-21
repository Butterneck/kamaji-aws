#!/usr/bin/env bash

KUBERNETES_VERSION=$1; shift

# Install `containerd` as container runtime.
cat << EOF | tee containerd.conf
overlay
br_netfilter
EOF

cat << EOF | tee 99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

sudo apt update && sudo apt install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sed -e "s#SystemdCgroup = false#SystemdCgroup = true#g" | sudo tee -a /etc/containerd/config.toml
sudo systemctl restart containerd && sudo systemctl enable containerd
sudo chown -R root:root containerd.conf && sudo mv containerd.conf /etc/modules-load.d/containerd.conf
sudo modprobe overlay && sudo modprobe br_netfilter
sudo chown -R root:root 99-kubernetes-cri.conf && sudo mv 99-kubernetes-cri.conf /etc/sysctl.d/99-kubernetes-cri.conf
sudo sysctl --system

# Install `kubectl`, `kubelet`, and `kubeadm` in the desired version.

INSTALL_KUBERNETES="sudo apt install -y kubelet=${KUBERNETES_VERSION}-00 kubeadm=${KUBERNETES_VERSION}-00 kubectl=${KUBERNETES_VERSION}-00 --allow-downgrades --allow-change-held-packages"

sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl
sudo curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg
echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt update
${INSTALL_KUBERNETES}
sudo apt-mark hold kubelet kubeadm kubectl