# Download kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
mv kubectl /usr/local/bin/
mkdir /root/.kube
cd /mnt
cp readonly-kubeconfig /root/.kube/config
chmod 600 /root/.kube/config
pip3 install -r requirements.txt