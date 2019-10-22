
# Setting up a dev environment

See instructions bellow to set up a [local development environment](#develop-locally) or [a development environment on AWS](#develop-on-aws).


## Develop locally

### Fork and clone repo
- Fork this repo on GitHub
- Create a local clone of your fork. On your terminal:
```
git clone git@github.com:YOUR-USERNAME/shell-history.git
```

### (optional) Keep your fork up to date with original repo. 
If you wish to keep your fork up to date with the original repo's changes, you have to:
1. Add upstream:
```
cd into/cloned/fork-repo
git remote add upstream git://github.com/ebastos/shell-history.git
git fetch upstream
```
2. Update your local fork with updates from original repo
```
git pull upstream master
```
3. Push latest changes to your fork in GitHub:
```
git push
```

### Run the backend
For development purposes, it's possible to use a sample database (SQLite) by following these steps:

1. Change the default database in Django's settings to use SQLite instead of MySQL:
Open `backend/shell/shell/settings.py` on your text editor.
Remove comment markings from the following lines:
```
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': os.path.join(BASE_DIR, 'db.sqlite3')
```
Comment out the following lines:
```
    'ENGINE': 'django.db.backends.mysql',
    'NAME': os.environ.get('SH_MYSQL_DB'),
    'HOST': os.environ.get('SH_MYSQL_HOST'),
    'USER': os.environ.get('SH_MYSQL_USER'),
    'PASSWORD': os.environ.get('SH_MYSQL_PASS'),
```

2. Create and run a Docker image for the project
From your project's directory:
```
docker build . --tag shell-history
docker run -p 8000:80 -p 50051:50051 shell-history

```
3. Visit [localhost:8000](http://localhost:8000/) on the browser


----------------------------------------------------------------------------------------------------------------------------------

## Develop on AWS

The steps below can be used to set up a develop environment using an AWS EC2 instance running Amazon Linux 2.

*Assuming running as root* 

### Install Go and Python 3:

```
amazon-linux-extras install golang1.9
amazon-linux-extras install python3
```

### Install git
```
yum install -y git
```

### Download the proto compiler
```
wget https://github.com/google/protobuf/releases/download/v3.5.1/protoc-3.5.1-linux-x86_64.zip
unzip protoc-3.5.1-linux-x86_64.zip
cp bin/protoc /usr/bin/
```

### Download Go dependencies
```
go get -u github.com/gobuffalo/packr/...
go get github.com/square/certstrap
go get google.golang.org/grpc
go get -u github.com/golang/protobuf/protoc-gen-go
```

### Add Go bin dir to path
```
PATH=$PATH:/root/go/bin/
```

### Clone repo
```
cd /root/go/src/github.com
mkdir ebastos
cd ebastos
git clone 
https://github.com/ebastos/shell-history.git
cd shell-history
```

### Install Python requirements
```
pip3 install -r requirements.txt
```

### Generate certificates
```
certstrap --depot-path certs init --common-name localhost
```