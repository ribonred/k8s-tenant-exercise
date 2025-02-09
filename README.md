# Tenant Operator

This is an example of a tenant operator that can be used to manage tenant resources in a kubernetes cluster.

## Prerequisites

- Python 3.11
- Minikube  (v1.23.2)
- Docker (v20.10.8)
- Helm (v3.7.0)
- Kubectl (v1.22.2)
- [uv python package (v1.4.0)](https://docs.astral.sh/uv/guides/install-python/)

### start minikube

delete existing minikube if exist
```bash
minikube start --addons=metrics-server,ingress,ingress-dns
```

### build docker image inside minikube
```bash
eval $(minikube docker-env)
```
if you use windows, you can use this command

```bash
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
```

more info is in here [minikube docker-env](https://minikube.sigs.k8s.io/docs/handbook/pushing/)

then can proceed to build the example app

### Build example app 
```bash
docker build -f ./examples/Dockerfile -t edu-app:latest ./examples
```

### install cluster requirements for operator and custom resource.

install flux operator and custom resource
```bash
kubectl apply -f ./crds/01-flux-install.yaml
```
install chart requirements for operator and custom resource tenant
```bash
kubectl apply -f ./crds/02-tenant-requirements.yaml
```
install CRD for Tenant
```bash
kubectl apply -f ./crds/03-tenant-crd.yaml
```

### start tenant operator

open new terminal and run this command

```bash
uv run kopf run ./tenant-operator.py
```

### start django control plane app

open new terminal and run this command

```bash
uv run python manage.py runserver
```

### start tunneling to minikube for ingress

open new terminal and run this command

```bash
minikube tunnel
```

navigate to http://127.0.0.1:8000/admin/ to see the tenant list

---

# Helm Chart management

tenant-chart are in the `tenant-stack` directory. the chart must be hosted in public or private helm repository.

in this example, im using github pages as helm repository.

the release chart can be found in `chart-release` directory.

### how to build the helm chart

```bash
 helm package tenant-stack -d chart-release
```

this command will create a tar.gz file in the `chart-release` directory.

### indexing the helm chart

```bash
helm repo index .
```

this command will create an index.yaml file in the current directory. 
later, the index.yaml file and the tar.gz file must be hosted in the public or private helm repository.
when i push to github repository there is a github action that will automatically update github pages with the new chart.

