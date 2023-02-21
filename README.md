
# Kamaji AWS

Deploy [kamaji](https://github.com/clastix/kamaji) on AWS EKS

# How to 

## deploy

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

Export AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY env variables.

```
$ export AWS_ACCESS_KEY_ID="..."
$ export AWS_SECRET_ACCESS_KEY="..."
```

At this point you can deploy the EKS cluster.

```
$ npx cdk deploy AdminClusterStack
```

Now install [Flux](https://fluxcd.io/flux/installation/) to install Kamaji and it's dependencies.

Finally deploy all the tenants.

```
$ npx cdk deploy --all
```

## Add new tenants

In order to add new tenants add a new `.yaml` file on `tenants` folder with tenant's configuration; then run 

```
$ npx cdk deploy --all
```