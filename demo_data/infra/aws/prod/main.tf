resource "aws_vpc" "main" {
  cidr_block = "10.10.0.0/16"
  tags = { Name = "prod-main-vpc", Environment = "prod" }
}

resource "aws_db_instance" "primary" {
  identifier        = "prod-db-primary"
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = "db.t3.medium"
  allocated_storage = 100
  db_name           = "appdb"
  username          = "dbadmin"
  password          = var.db_password
  tags = { Environment = "prod" }
}

resource "aws_iam_role" "app_role" {
  name = "prod-app-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
  tags = { Environment = "prod" }
}
