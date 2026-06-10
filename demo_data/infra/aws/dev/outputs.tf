output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "web_server_ip" {
  description = "Web server public IP"
  value       = aws_instance.web_server.public_ip
}
