terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "dev-main-vpc", Environment = "dev" }
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "ap-southeast-1a"
  tags = { Name = "dev-public-subnet", Environment = "dev" }
}

resource "aws_security_group" "web" {
  name        = "dev-web-sg"
  description = "Web tier security group"
  vpc_id      = aws_vpc.main.id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Environment = "dev" }
}

resource "aws_instance" "web_server" {
  ami             = "ami-0abcdef1234567890"
  instance_type   = "t3.micro"
  subnet_id       = aws_subnet.public.id
  security_groups = [aws_security_group.web.id]
  tags = { Name = "dev-web-server", Environment = "dev" }
}

resource "aws_s3_bucket" "app_data" {
  bucket = "myapp-dev-data-bucket"
  tags   = { Environment = "dev", ManagedBy = "terraform" }
}
