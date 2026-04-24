terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "YOUR_PROJECT_ID-tf-state"
    prefix = "realtime-pipeline"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Pub/Sub ---
resource "google_pubsub_topic" "events" {
  name = "events-topic"

  message_retention_duration = "86600s"

  labels = {
    env       = var.env
    component = "ingestion"
  }
}

resource "google_pubsub_subscription" "events_sub" {
  name  = "events-sub"
  topic = google_pubsub_topic.events.name

  ack_deadline_seconds       = 60
  message_retention_duration = "600s"
  retain_acked_messages      = false

  expiration_policy {
    ttl = ""
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_topic" "dead_letter" {
  name = "events-dead-letter"
}

# --- BigQuery ---
resource "google_bigquery_dataset" "events" {
  dataset_id  = var.bq_dataset
  location    = var.region
  description = "Real-time events ingested via Dataflow"

  labels = {
    env       = var.env
    component = "storage"
  }
}

resource "google_bigquery_table" "events_raw" {
  dataset_id          = google_bigquery_dataset.events.dataset_id
  table_id            = "events_raw"
  deletion_protection = true

  time_partitioning {
    type  = "DAY"
    field = "ingest_date"
  }

  clustering = ["event_type", "user_id"]

  schema = file("${path.module}/../../config/bq_schema.json")

  labels = {
    env = var.env
  }
}

# --- GCS buckets ---
resource "google_storage_bucket" "dataflow_temp" {
  name                        = "${var.project_id}-df-temp"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 7 }
  }
}

resource "google_storage_bucket" "templates" {
  name                        = "${var.project_id}-templates"
  location                    = var.region
  uniform_bucket_level_access = true
}

# --- Service account for Dataflow ---
resource "google_service_account" "dataflow_runner" {
  account_id   = "dataflow-runner"
  display_name = "Dataflow Pipeline Runner"
}

resource "google_project_iam_member" "dataflow_worker" {
  project = var.project_id
  role    = "roles/dataflow.worker"
  member  = "serviceAccount:${google_service_account.dataflow_runner.email}"
}

resource "google_project_iam_member" "bq_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dataflow_runner.email}"
}

resource "google_project_iam_member" "pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.dataflow_runner.email}"
}
