variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "enterprise-rag"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "node_instance_type" {
  description = "EKS node instance type"
  type        = string
  default     = "t3.large"
}

variable "node_min_count" {
  description = "Minimum number of EKS nodes"
  type        = number
  default     = 2
}

variable "node_max_count" {
  description = "Maximum number of EKS nodes"
  type        = number
  default     = 5
}

variable "node_desired_count" {
  description = "Desired number of EKS nodes"
  type        = number
  default     = 3
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "enterprise-rag"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}
