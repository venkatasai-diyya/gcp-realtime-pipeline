variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "env" {
  description = "Environment tag (dev / staging / prod)"
  type        = string
  default     = "dev"
}

variable "bq_dataset" {
  description = "BigQuery dataset name"
  type        = string
  default     = "events_streaming"
}
